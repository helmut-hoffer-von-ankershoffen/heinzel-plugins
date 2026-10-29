"""The planner and boundary guard must work for a new plugin without registry edits."""

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from heinzel_plugin_tools import cli as plugins

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("name", ["harbor", None])
def test_actual_collection_make_fast_loop_dispatches_only_the_selected_scope(tmp_path, monkeypatch, name):
    monkeypatch.setenv("MAKELEVEL", "5")  # CI invokes pytest under make; its nested-driver flags must not leak.
    make = shutil.which("make")
    assert make
    driver = tmp_path / "driver.py"
    driver.write_text('import json, os, sys\nprint(json.dumps([sys.argv[1:], os.environ.get("PLUGIN_NAME")]))\n')
    command = shlex.join([sys.executable, str(driver)])
    # An unselected collection calls its shared tooling target through a recursive make.
    (tmp_path / "Makefile").write_text(f"tooling-check:\n\t@{command} tooling-check\n")
    arguments = [make, "-f", str(Path(__file__).parents[1] / "Makefile"), "check-fast", f"PLUGIN={command}"]
    if name:
        arguments.append(f"NAME={name}")
    result = subprocess.run(  # noqa: S603 - actual repository Makefile, disposable driver and fixed arguments
        arguments,
        cwd=tmp_path,
        env={
            key: value
            for key, value in os.environ.items()
            if key not in {"NAME", "PLUGIN_NAME"} and not key.startswith("MAKE")
        },
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    assert json.loads(result.stdout) == [["check-fast"] if name else ["tooling-check"], name or ""]


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


@pytest.mark.parametrize(
    "changed", [[], ["plugins/heinzel-unforeseen/src/plugin.py", "plugins/heinzel-unforeseen/README.md"]]
)
def test_hook_dispatch_checks_owners_and_contract_consumers_without_core(tmp_path, monkeypatch, changed):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="heinzel"\nversion="0.9.1"\n[project.entry-points.pytest11]\nheinzel="heinzel.testing"\n'
    )
    project(tmp_path, "heinzel-unforeseen", provides=["metrics:read@1"])
    project(tmp_path, "heinzel-reader", requires=["metrics:read@1"])
    project(tmp_path, "heinzel-independent")
    inventory = plugins.projects(tmp_path)
    assert all(item.name != "heinzel" for item in inventory)
    monkeypatch.setattr(plugins, "ROOT", tmp_path)
    monkeypatch.setattr(plugins, "projects", lambda: inventory)
    monkeypatch.setattr(sys, "argv", ["hz-plugin", "check-changed", *(["--changed", *changed] if changed else [])])
    calls = []
    monkeypatch.setattr(plugins, "check", lambda item, core, *, fast: calls.append((item.name, fast)))
    assert plugins.main() == 0
    assert set(calls) == ({("heinzel-unforeseen", True), ("heinzel-reader", True)} if changed else set())


def test_plugin_only_hooks_do_not_run_collection_checks():
    import re

    import yaml

    config = yaml.safe_load((Path(__file__).parents[1] / ".pre-commit-config.yaml").read_text())
    hooks = {hook["id"]: hook for repo in config["repos"] for hook in repo["hooks"]}
    core = hooks["check-fast"]
    assert not core.get("always_run")
    assert re.search(core["exclude"], "plugins/heinzel-harbor/src/plugin.py")
    owner = hooks["owning-plugin-checks"]
    assert "check-changed" in owner["entry"]
    assert owner["require_serial"] is True
    assert owner["entry"].endswith("--git-hook")
    assert owner["pass_filenames"] is False and owner["always_run"] is True


@pytest.fixture(params=[False, True])
def isolated_hook_environment(tmp_path, monkeypatch, request):
    """Neither a hook's alternate index nor its foreign repository may escape a disposable fixture."""
    if request.param:
        foreign = tmp_path / "foreign-index"
        foreign.write_bytes(b"must remain unchanged")
        monkeypatch.setenv("GIT_INDEX_FILE", str(foreign))
        monkeypatch.setenv("GIT_DIR", str(tmp_path / "foreign-repository"))
        monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "foreign-tree"))
    for key in list(os.environ):
        if key.startswith("GIT_") or key.startswith("PRE_COMMIT_"):
            monkeypatch.delenv(key)
    yield
    if request.param:
        assert foreign.read_bytes() == b"must remain unchanged"
        assert not (tmp_path / "foreign-repository").exists()
        assert not (tmp_path / "foreign-tree").exists()


@pytest.mark.parametrize("pushed", [False, True])
def test_hook_git_scope_retains_deleted_paths_and_ignores_core(
    tmp_path, monkeypatch, pushed, isolated_hook_environment
):
    git = shutil.which("git")
    assert git

    def run(*args):
        return subprocess.check_output([git, *args], cwd=tmp_path, text=True, timeout=30)  # noqa: S603 - resolved git, disposable repository

    run("init", "--quiet")
    run("config", "user.name", "Example Author")
    run("config", "user.email", "author@example.test")
    directory = project(tmp_path, "heinzel-unforeseen")
    obsolete = directory / "src/obsolete.py"
    obsolete.write_text("obsolete = True\n")
    run("add", ".")
    run("-c", "core.hooksPath=/dev/null", "commit", "--quiet", "-m", "feat: add example")
    before = run("rev-parse", "HEAD").strip()
    obsolete.unlink()
    (tmp_path / "core.py").write_text("core = True\n")
    run("add", "--all")
    monkeypatch.setattr(plugins, "ROOT", tmp_path)
    monkeypatch.delenv("PRE_COMMIT_FROM_REF", raising=False)
    monkeypatch.delenv("PRE_COMMIT_TO_REF", raising=False)
    if pushed:
        run("-c", "core.hooksPath=/dev/null", "commit", "--quiet", "-m", "refactor: remove obsolete")
        monkeypatch.setenv("PRE_COMMIT_FROM_REF", before)
        monkeypatch.setenv("PRE_COMMIT_TO_REF", run("rev-parse", "HEAD").strip())
    assert plugins.hook_changes() == ["plugins/heinzel-unforeseen/src/obsolete.py"]


@pytest.mark.parametrize("stage", ["pre-commit", "pre-push"])
@pytest.mark.parametrize("change", ["delete", "core-only"])
def test_actual_prek_dispatch_includes_deletions_and_noops_for_unrelated_changes(
    tmp_path, stage, change, isolated_hook_environment
):
    import yaml

    git, prek = shutil.which("git"), shutil.which("prek")
    assert git and prek

    def run(*args):
        return subprocess.check_output([git, *args], cwd=tmp_path, text=True, timeout=30)  # noqa: S603 - resolved git and disposable repository

    run("init", "--quiet")
    run("config", "user.name", "Example Author")
    run("config", "user.email", "author@example.test")
    directory = project(tmp_path, "heinzel-unforeseen", provides=["metrics:read@1"])
    project(tmp_path, "heinzel-reader", requires=["metrics:read@1"])
    project(tmp_path, "heinzel-unrelated")
    obsolete = directory / "src/obsolete.py"
    obsolete.write_text("obsolete = True\n")
    log = tmp_path / "checked.json"
    driver = tmp_path / "driver.py"
    driver.write_text(
        "import json,sys\n"
        f"sys.path.insert(0, {str(Path(plugins.__file__).parents[1])!r})\n"
        "from heinzel_plugin_tools import cli\n"
        "from pathlib import Path\n"
        "selected=[]\n"
        "cli.check=lambda project,core,fast: selected.append(project.name)\n"
        "sys.argv=['hz-plugin','check-changed','--git-hook']\n"
        "assert cli.main() == 0\n"
        f"Path({str(log)!r}).write_text(json.dumps(selected))\n"
    )
    config = yaml.safe_load((Path(__file__).parents[1] / ".pre-commit-config.yaml").read_text())
    hook = next(hook for repo in config["repos"] for hook in repo["hooks"] if hook["id"] == "owning-plugin-checks")
    hook["entry"] = shlex.join([sys.executable, str(driver)])
    (tmp_path / ".pre-commit-config.yaml").write_text(yaml.safe_dump({"repos": [{"repo": "local", "hooks": [hook]}]}))
    run("add", ".")
    run("-c", "core.hooksPath=/dev/null", "commit", "--quiet", "-m", "feat: add example")
    before = run("rev-parse", "HEAD").strip()
    if change == "delete":
        obsolete.unlink()
    else:
        (tmp_path / "core.py").write_text("core = True\n")
    run("add", "--all")
    command = [prek, "run", "owning-plugin-checks", "--hook-stage", stage]
    if stage == "pre-push":
        run("-c", "core.hooksPath=/dev/null", "commit", "--quiet", "-m", "refactor: update example")
        command += ["--from-ref", before, "--to-ref", run("rev-parse", "HEAD").strip()]
    result = subprocess.run(command, cwd=tmp_path, text=True, capture_output=True, timeout=30, check=False)  # noqa: S603 - actual hook runner and disposable repository
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(log.read_text()) == (["heinzel-reader", "heinzel-unforeseen"] if change == "delete" else [])


def test_actual_first_push_and_new_branch_deletion_select_the_owning_contract_consumers(
    tmp_path, isolated_hook_environment
):
    import yaml

    git, prek = shutil.which("git"), shutil.which("prek")
    assert git and prek
    remote, root = tmp_path / "origin.git", tmp_path / "work"
    root.mkdir()

    def run(*args):
        return subprocess.check_output([git, *args], cwd=root, text=True, stderr=subprocess.STDOUT, timeout=30)  # noqa: S603 - resolved git, disposable repository

    run("init", "--quiet", "--bare", str(remote))
    run("init", "--quiet", "--initial-branch=main")
    run("config", "user.name", "Example Author")
    run("config", "user.email", "author@example.test")
    run("remote", "add", "origin", str(remote))
    owner = project(root, "heinzel-unforeseen", provides=["metrics:read@1"])
    project(root, "heinzel-reader", requires=["metrics:read@1"])
    project(root, "heinzel-unrelated")
    obsolete = owner / "src/obsolete.py"
    obsolete.write_text("obsolete = True\n")
    log = tmp_path / "selected.json"
    driver = tmp_path / "driver.py"
    driver.write_text(
        "import json,sys\n"
        f"sys.path.insert(0, {str(Path(plugins.__file__).parents[1])!r})\n"
        "from heinzel_plugin_tools import cli\nfrom pathlib import Path\nselected=[]\n"
        "cli.check=lambda project,core,fast: selected.append(project.name)\n"
        "sys.argv=['hz-plugin','check-changed','--git-hook']\nassert cli.main() == 0\n"
        f"Path({str(log)!r}).write_text(json.dumps(selected))\n"
    )
    config = yaml.safe_load((Path(__file__).parents[1] / ".pre-commit-config.yaml").read_text())
    hook = next(hook for repo in config["repos"] for hook in repo["hooks"] if hook["id"] == "owning-plugin-checks")
    hook["entry"] = shlex.join([sys.executable, str(driver)])
    (root / ".pre-commit-config.yaml").write_text(yaml.safe_dump({"repos": [{"repo": "local", "hooks": [hook]}]}))
    subprocess.run([prek, "install", "--hook-type", "pre-push"], cwd=root, check=True, capture_output=True)  # noqa: S603 - actual hook runner, disposable repository
    run("add", ".")
    run("commit", "--quiet", "-m", "feat: add example")
    run("push", "--quiet", "origin", "main")
    assert set(json.loads(log.read_text())) == {"heinzel-unforeseen", "heinzel-reader", "heinzel-unrelated"}
    log.unlink()
    run("switch", "--quiet", "--create", "refactor/remove-obsolete")
    obsolete.unlink()
    run("add", "--all")
    run("commit", "--quiet", "-m", "refactor: remove obsolete")
    run("push", "--quiet", "origin", "HEAD")
    assert json.loads(log.read_text()) == ["heinzel-reader", "heinzel-unforeseen"]


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


def test_plugin_can_add_and_execute_its_own_runtime_dependency_without_sibling_environments(tmp_path):
    import hashlib
    import shutil
    import zipfile

    dependency = tmp_path / "sample_helper-1.0.0-py3-none-any.whl"
    prefix = "sample_helper-1.0.0.dist-info"
    with zipfile.ZipFile(dependency, "w") as archive:
        archive.writestr("sample_helper/__init__.py", "def label(value): return 'helper:' + value\n")
        archive.writestr(f"{prefix}/METADATA", "Metadata-Version: 2.1\nName: sample-helper\nVersion: 1.0.0\n")
        archive.writestr(f"{prefix}/WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
        archive.writestr(f"{prefix}/RECORD", "")
    owner = project(
        tmp_path,
        "heinzel-unforeseen",
        dependency="sample-helper>=1",
        source="from sample_helper import label\nresult = label('ready')\n",
    )
    sibling = project(tmp_path, "heinzel-unrelated")
    selected = next(item for item in plugins.projects(tmp_path) if item.directory == owner)
    plugins.boundaries(selected)
    lock = owner / "requirements.lock"
    lock.write_text(
        f"sample-helper @ {dependency.as_uri()} --hash=sha256:{hashlib.sha256(dependency.read_bytes()).hexdigest()}\n"
    )
    interpreter = owner / ".venv/bin/python"
    uv = shutil.which("uv")
    assert uv
    subprocess.run(  # noqa: S603 - resolved executable and local test directory
        [uv, "venv", "--python", "3.12", str(interpreter.parents[1])],
        check=True,
        capture_output=True,
        timeout=30,
    )
    subprocess.run(  # noqa: S603 - owning hashed local fixture dependency
        [uv, "pip", "sync", "--python", str(interpreter), "--require-hashes", str(lock)],
        check=True,
        capture_output=True,
        timeout=30,
    )
    command = f"import runpy; assert runpy.run_path({str(owner / 'src/plugin.py')!r})['result'] == 'helper:ready'"
    subprocess.run([str(interpreter), "-c", command], check=True, capture_output=True, timeout=30)  # noqa: S603 - synthetic owned plugin only
    assert not (sibling / ".venv").exists()
    assert not (tmp_path / "pyproject.toml").exists()


@pytest.mark.parametrize("name", ["heinzel-unsafe;command", "heinzel-unsafe\noutput", "Heinzel-Unsafe"])
def test_metadata_cannot_inject_matrix_outputs_or_commands(tmp_path, name):
    directory = project(tmp_path, "heinzel-unforeseen")
    metadata = (directory / "pyproject.toml").read_text().replace('name="heinzel-unforeseen"', f"name={name!r}")
    (directory / "pyproject.toml").write_text(metadata)
    with pytest.raises(ValueError):
        plugins.projects(tmp_path)


@pytest.mark.parametrize(
    "option", ["NAME", "CORE", "TAG", "REGISTRY", "TOOLING", "PRESET", "TEMPLATE", "REF", "BASE", "CONTRACT"]
)
def test_make_does_not_evaluate_forwarded_options_as_make_code(tmp_path, option):
    sentinel = tmp_path / "must-not-exist"
    make = shutil.which("make")
    assert make
    stub = tmp_path / "uv"
    stub.write_text("#!/bin/sh\nexit 0\n")
    stub.chmod(0o755)
    result = subprocess.run(  # noqa: S603, S607 - test passes inert make input directly, no shell
        [make, "check", f"{option}=$(shell touch {sentinel})"],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"]},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not sentinel.exists()
