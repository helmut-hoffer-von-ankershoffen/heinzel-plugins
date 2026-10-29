"""The planner and boundary guard must work for a new plugin without registry edits."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("plugin_tools", Path(__file__).parents[1] / "scripts/plugins.py")
assert spec and spec.loader
plugins = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = plugins
spec.loader.exec_module(plugins)


def project(root, name, *, requires=(), provides=(), dependency=None, source=""):
    directory = root / "plugins" / name
    (directory / "src").mkdir(parents=True)
    (directory / "src/plugin.py").write_text(source)
    dependencies = [dependency] if dependency else ["heinzel>=0.9,<0.10"]
    (directory / "pyproject.toml").write_text(
        f'[project]\nname="{name}"\nversion="1.0.0"\ndependencies={dependencies!r}\n'
        '[project.entry-points."heinzel.modules"]\nplugin="plugin:module"\n'
        f"[tool.heinzel.plugin]\nrequires={list(requires)!r}\nprovides={list(provides)!r}\n"
    )
    return directory


def test_unknown_plugin_selects_only_itself_and_contract_consumers(tmp_path):
    project(tmp_path, "heinzel-unforeseen", provides=["metrics:read@1"])
    project(tmp_path, "heinzel-reader", requires=["metrics:read@1"], provides=["summary:read@1"])
    project(tmp_path, "heinzel-display", requires=["summary:read@1"])
    project(tmp_path, "heinzel-independent")
    plan = plugins.plan(["plugins/heinzel-unforeseen/src/plugin.py"], plugins.projects(tmp_path), tmp_path)
    assert {entry["name"] for entry in plan["include"]} == {"heinzel-unforeseen", "heinzel-reader", "heinzel-display"}
    assert not any(plan[key] for key in ("core", "core_build", "core_tests"))


def test_shared_tooling_discovers_a_different_repository_without_parent_edits(tmp_path):
    project(tmp_path, "heinzel-unforeseen")
    result = subprocess.run(  # noqa: S603 - fixed interpreter, checked-in script and synthetic project
        [sys.executable, str(Path(plugins.__file__)), "plan", "--changed", "plugins/heinzel-unforeseen/src/plugin.py"],
        env={
            **{key: value for key, value in os.environ.items() if not key.startswith("PLUGIN_")},
            "PLUGIN_SOURCE_ROOT": str(tmp_path),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    work = json.loads(result.stdout)
    assert [entry["name"] for entry in work["include"]] == ["heinzel-unforeseen"]
    assert not any(work[key] for key in ("core", "core_build", "core_tests"))


def test_docs_only_change_selects_no_builds_and_shared_tooling_selects_all(tmp_path):
    project(tmp_path, "heinzel-unforeseen")
    inventory = plugins.projects(tmp_path)
    assert plugins.plan(["README.md"], inventory, tmp_path)["include"] == []
    assert len(plugins.plan(["scripts/plugins.py"], inventory, tmp_path)["include"]) == 1


@pytest.mark.parametrize(
    "source",
    [
        "import heinzel_other",
        "from heinzel.modules.system import sound",
        "from heinzel.kernel._lets import Let",
        "from heinzel.kernel import _lets",
    ],
)
def test_boundary_guard_catches_concrete_and_private_imports(tmp_path, source):
    project(tmp_path, "heinzel-unforeseen", source=source)
    with pytest.raises(ValueError, match="public contract"):
        plugins.boundaries(plugins.projects(tmp_path)[0])


def test_boundary_guard_catches_sibling_distribution_dependencies(tmp_path):
    project(tmp_path, "heinzel-unforeseen", dependency="heinzel-provider>=1")
    with pytest.raises(ValueError, match="public contract"):
        plugins.boundaries(plugins.projects(tmp_path)[0])


def test_public_contract_import_and_own_implementation_are_allowed(tmp_path):
    project(
        tmp_path,
        "heinzel-unforeseen",
        source="from heinzel import Module\nfrom hz_contracts import Reading\nimport heinzel_unforeseen.service",
    )
    plugins.boundaries(plugins.projects(tmp_path)[0])


def test_commands_use_only_the_owning_isolated_environment(tmp_path):
    directory = project(tmp_path, "heinzel-unforeseen")
    command = plugins.python_command(plugins.projects(tmp_path)[0], None, ["pytest", "tests"])
    assert command == [str(directory / ".venv/bin/pytest"), "tests"]


def test_core_contract_change_selects_declared_consumers_only(tmp_path):
    project(tmp_path, "heinzel-reader", requires=["core:plugin-api@1"])
    project(tmp_path, "heinzel-unrelated", requires=["some-other-contract@1"])
    plan = plugins.plan([], plugins.projects(tmp_path), tmp_path, contracts=["core:plugin-api@1"])
    assert [item["name"] for item in plan["include"]] == ["heinzel-reader"]
    assert not plan["core_tests"]


def test_nonstandard_provider_names_are_recognized_from_installed_metadata(tmp_path, monkeypatch):
    from types import SimpleNamespace

    provider = SimpleNamespace(
        metadata={"Name": "thirdparty-provider"},
        entry_points=[SimpleNamespace(group="heinzel.modules", value="some_provider:module")],
    )
    monkeypatch.setattr(plugins.distributions, "distributions", lambda: [provider])
    project(tmp_path, "heinzel-unforeseen", dependency="thirdparty-provider>=1")
    with pytest.raises(ValueError, match="public contract"):
        plugins.boundaries(plugins.projects(tmp_path)[0])


def test_implementation_free_contract_distributions_are_allowed(tmp_path, monkeypatch):
    from types import SimpleNamespace

    contract = SimpleNamespace(metadata={"Name": "heinzel-contracts"}, entry_points=[])
    monkeypatch.setattr(plugins.distributions, "distributions", lambda: [contract])
    monkeypatch.setattr(
        plugins.distributions, "packages_distributions", lambda: {"heinzel_contracts": ["heinzel-contracts"]}
    )
    project(
        tmp_path,
        "heinzel-unforeseen",
        dependency="heinzel-contracts>=1",
        source="from heinzel_contracts import Reading",
    )
    plugins.boundaries(plugins.projects(tmp_path)[0])


def test_root_plugin_is_selected_without_a_parent_registry(tmp_path):
    directory = project(tmp_path, "heinzel-unforeseen")
    (directory / "pyproject.toml").replace(tmp_path / "pyproject.toml")
    inventory = plugins.projects(tmp_path)
    assert inventory[0].directory == tmp_path
    assert plugins.plan(["src/plugin.py"], inventory, tmp_path)["include"] == [
        {"name": "heinzel-unforeseen", "path": "."}
    ]


def test_core_plan_excludes_consumers_outside_their_compatible_range(tmp_path, monkeypatch):
    project(tmp_path, "heinzel-current", requires=["core:plugin-api@1"])
    project(tmp_path, "heinzel-older", requires=["core:plugin-api@1"], dependency="heinzel>=0.8,<0.9")
    monkeypatch.setattr(plugins, "core_metadata", lambda _: {"version": "0.9.0"})
    plan = plugins.plan([], plugins.projects(tmp_path), tmp_path, contracts=["core:plugin-api@1"], core="candidate")
    assert [item["name"] for item in plan["include"]] == ["heinzel-current"]


def contract_wheel(directory):
    import zipfile

    wheel = directory / "heinzel_contracts-1.0.0-py3-none-any.whl"
    prefix = "heinzel_contracts-1.0.0.dist-info"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("heinzel_contracts/__init__.py", "class Reading: pass\n")
        archive.writestr(f"{prefix}/METADATA", "Metadata-Version: 2.1\nName: heinzel-contracts\nVersion: 1.0.0\n")
        archive.writestr(
            f"{prefix}/WHEEL", "Wheel-Version: 1.0\nGenerator: tests\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        )
        archive.writestr(f"{prefix}/RECORD", "")
    return wheel


def test_hash_verification_rejects_tampering_and_neutral_contract_works_in_fresh_environment(tmp_path):
    import hashlib
    import subprocess  # noqa: S404 - fixed test subprocesses

    wheel = contract_wheel(tmp_path)
    interpreter = tmp_path / "environment/bin/python"
    subprocess.run(["uv", "venv", "--python", "3.12", str(interpreter.parents[1])], check=True, capture_output=True)  # noqa: S603, S607 - isolated test interpreter
    lock = tmp_path / "requirements.lock"
    requirement = f"heinzel-contracts @ {wheel.as_uri()} --hash=sha256:"
    lock.write_text(requirement + "0" * 64 + "\n")
    command = ["uv", "pip", "sync", "--python", str(interpreter), "--require-hashes", str(lock)]
    failed = subprocess.run(command, capture_output=True, text=True, check=False)  # noqa: S603 - fixed uv arguments
    assert failed.returncode != 0
    assert "hash" in failed.stderr.lower()
    lock.write_text(requirement + hashlib.sha256(wheel.read_bytes()).hexdigest() + "\n")
    subprocess.run(command, check=True, capture_output=True)  # noqa: S603 - fixed uv arguments
    project(
        tmp_path,
        "heinzel-unforeseen",
        dependency="heinzel-contracts>=1",
        source="from heinzel_contracts import Reading",
    )
    script = (
        "import importlib.util,sys,pathlib; "
        f"spec=importlib.util.spec_from_file_location('plugins', {str(Path(plugins.__file__))!r}); "
        "module=importlib.util.module_from_spec(spec); sys.modules['plugins']=module; spec.loader.exec_module(module); "
        f"module.boundaries(module.projects(pathlib.Path({str(tmp_path)!r}))[0])"
    )
    # The tooling itself has one neutral dependency; it is independent of every provider and core.
    import packaging

    environment = {"PYTHONPATH": str(Path(packaging.__file__).parent.parent)}
    import os

    completed = subprocess.run(  # noqa: S603 - synthetic local package, no shell
        [str(interpreter), "-c", script],
        env=dict(os.environ) | environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("name", ["heinzel-unsafe;command", "heinzel-unsafe\noutput", "Heinzel-Unsafe"])
def test_metadata_cannot_inject_matrix_outputs_or_commands(tmp_path, name):
    directory = project(tmp_path, "heinzel-unforeseen")
    metadata = (directory / "pyproject.toml").read_text().replace('name="heinzel-unforeseen"', f"name={name!r}")
    (directory / "pyproject.toml").write_text(metadata)
    with pytest.raises(ValueError):
        plugins.projects(tmp_path)


def test_make_does_not_evaluate_untrusted_name_as_make_code(tmp_path):
    import shutil
    import subprocess

    sentinel = tmp_path / "must-not-exist"
    make = shutil.which("make")
    assert make
    result = subprocess.run(  # noqa: S603, S607 - test passes inert make input directly, no shell
        [make, "check", f"NAME=$(shell touch {sentinel})"],
        cwd=Path(plugins.__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert not sentinel.exists()
