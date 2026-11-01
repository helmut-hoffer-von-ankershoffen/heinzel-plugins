"""Locks, candidate core metadata and the isolated environment are authenticated before any plugin command runs."""

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest
from packaging.requirements import Requirement

from heinzel_plugin_tools import cli

pytestmark = pytest.mark.unit

CORE_REQUIRES = ["pydantic>=2.11", "typer>=0.15"]


def core_wheel(path, *, name="heinzel", version="0.9.4", requires=CORE_REQUIRES):
    text = f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
    text += "".join(f"Requires-Dist: {value}\n" for value in requires)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{name}-{version}.dist-info/METADATA", text)
    return path


@pytest.fixture
def project(tmp_path):
    directory = tmp_path / "plugins/heinzel-harbor"
    directory.mkdir(parents=True)
    metadata = {
        "project": {
            "name": "heinzel-harbor",
            "version": "0.2.0",
            "dependencies": ["heinzel>=0.9.1,<0.10", "tidal-tables>=1"],
            "entry-points": {"heinzel.modules": {"harbor": "heinzel_harbor.module:Harbor"}},
        },
        "dependency-groups": {
            "test": ["pytest>=9", {"include-group": "extra"}],
            "extra": ["freezegun>=1"],
            "dev": [],
        },
        "build-system": {"requires": ["hatchling>=1.29"]},
    }
    return cli.Project(directory, "heinzel-harbor", "0.2.0", metadata)


@pytest.fixture
def commands(monkeypatch):
    recorded = []
    monkeypatch.setattr(cli, "run", lambda command, **options: recorded.append((command, options)))
    return recorded


def write_lock(project, core, **changes):
    record = {"format": 1, "sdk": 1, "inputs": cli.dependency_inputs(project), "core": cli.core_metadata(str(core))}
    (project.directory / "plugin-lock.json").write_text(json.dumps(record | changes))
    (project.directory / "requirements.lock").write_text("tidal-tables==1.0 --hash=sha256:00\n")
    return record


def test_dependency_groups_follow_includes_and_tolerate_missing_groups(project):
    assert cli.requirements(project, "test") == ["pytest>=9", "freezegun>=1"]
    assert cli.requirements(project, "absent") == []


def test_every_declared_input_is_part_of_the_lock_inputs(project):
    assert cli.dependency_inputs(project) == sorted(
        ["heinzel>=0.9.1,<0.10", "tidal-tables>=1", "pytest>=9", "freezegun>=1", "hatchling>=1.29"]
    )


@pytest.mark.parametrize(
    ("version", "allowed"), [("0.9.1", True), ("0.9.9", True), ("0.10.0", False), ("0.8.0", False)]
)
def test_a_plugin_supports_exactly_the_core_range_it_declares(project, version, allowed):
    assert cli.supports_core(project, version) is allowed


def test_a_plugin_that_declares_no_core_supports_none(project):
    bare = cli.Project(project.directory, project.name, project.version, {"project": {"dependencies": ["x>=1"]}})
    assert cli.supports_core(bare, "0.9.4") is False


def test_core_metadata_is_read_from_a_wheel_without_installing_it(tmp_path):
    wheel = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    assert cli.core_metadata(str(wheel)) == {
        "version": "0.9.4",
        "dependencies": sorted(str(Requirement(v)) for v in CORE_REQUIRES),
    }


def test_a_wheel_of_another_distribution_is_not_accepted_as_core(tmp_path):
    other = core_wheel(tmp_path / "other-1.0-py3-none-any.whl", name="not-core", version="1.0")
    with pytest.raises(ValueError, match="built Heinzel core wheel"):
        cli.core_metadata(str(other))


def test_a_remote_candidate_is_fetched_over_https_with_a_size_bound(tmp_path, monkeypatch):
    wheel = core_wheel(tmp_path / "core.whl")
    requested = []

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def opened(url, timeout):
        requested.append((url, timeout))
        return Response(wheel.read_bytes())

    monkeypatch.setattr(cli.urllib.request, "urlopen", opened)
    assert cli.core_metadata("https://example.org/core.whl")["version"] == "0.9.4"
    assert requested == [("https://example.org/core.whl", 60)]


def test_an_oversized_core_artifact_is_refused(tmp_path, monkeypatch):
    class Huge(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, size=-1):
            return b"0" * size

    monkeypatch.setattr(cli.urllib.request, "urlopen", lambda *a, **k: Huge())
    with pytest.raises(ValueError, match="size limit"):
        cli.core_metadata("https://example.org/core.whl")


def test_the_newest_compatible_stable_non_yanked_wheel_is_selected(project, monkeypatch):
    def release(version, *, yanked=False, kind="py3-none-any.whl"):
        return [{"filename": f"heinzel-{version}-{kind}", "url": f"https://files.example/{version}", "yanked": yanked}]

    payload = {
        "releases": {
            "0.10.0": release("0.10.0"),  # outside the declared range
            "0.9.6rc1": release("0.9.6rc1"),  # prerelease
            "0.9.5": release("0.9.5", yanked=True),
            "0.9.4": release("0.9.4", kind="cp312-linux.whl") + release("0.9.4"),
            "0.9.3": release("0.9.3"),
        }
    }

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    monkeypatch.setattr(cli.urllib.request, "urlopen", lambda *a, **k: Response(json.dumps(payload).encode()))
    assert cli.released_core(project) == "https://files.example/0.9.4"


def test_no_compatible_release_asks_for_an_explicit_candidate(project, monkeypatch):
    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    monkeypatch.setattr(
        cli.urllib.request, "urlopen", lambda *a, **k: Response(json.dumps({"releases": {"0.10.0": []}}).encode())
    )
    with pytest.raises(ValueError, match="CORE=<candidate-core-wheel>"):
        cli.released_core(project)


def test_locking_resolves_inputs_against_the_candidate_and_records_the_core(project, tmp_path, commands):
    wheel = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    cli.lock(project, str(wheel))
    ((command, _),) = commands
    assert command[:4] == ["uv", "pip", "compile", command[3]]
    assert "--universal" in command and "--generate-hashes" in command
    assert command[command.index("--output-file") + 1] == str(project.directory / "requirements.lock")
    record = json.loads((project.directory / "plugin-lock.json").read_text())
    assert record["inputs"] == cli.dependency_inputs(project)
    assert record["core"]["version"] == "0.9.4"


def test_locking_refuses_a_core_the_plugin_does_not_allow(project, tmp_path, commands):
    wheel = core_wheel(tmp_path / "heinzel-0.10.0-py3-none-any.whl", version="0.10.0")
    with pytest.raises(ValueError, match="does not allow core 0.10.0"):
        cli.lock(project, str(wheel))
    assert commands == [] and not (project.directory / "plugin-lock.json").exists()


def test_locking_without_a_candidate_uses_the_released_core(project, tmp_path, commands, monkeypatch):
    wheel = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    monkeypatch.setattr(cli, "released_core", lambda _: str(wheel))
    cli.lock(project)
    assert json.loads((project.directory / "plugin-lock.json").read_text())["core"]["version"] == "0.9.4"


def test_a_missing_lock_tells_the_author_how_to_create_it(project):
    with pytest.raises(ValueError, match="needs its own dependency lock.*make lock NAME=heinzel-harbor"):
        cli.validate_lock(project, None)


def test_a_lock_with_changed_inputs_must_be_refreshed(project, tmp_path):
    wheel = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    write_lock(project, wheel, inputs=["something-else"])
    with pytest.raises(ValueError, match="dependencies changed"):
        cli.validate_lock(project, None)


def test_a_valid_lock_returns_its_record_and_checks_a_selected_core_against_it(project, tmp_path):
    wheel = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    write_lock(project, wheel)
    assert cli.validate_lock(project, None)["core"]["version"] == "0.9.4"
    assert cli.validate_lock(project, str(wheel))["core"]["version"] == "0.9.4"
    changed = core_wheel(tmp_path / "changed.whl", requires=[*CORE_REQUIRES, "extra-dependency>=1"])
    with pytest.raises(ValueError, match="Core dependencies changed; relock only this consumer"):
        cli.validate_lock(project, str(changed))
    newer = core_wheel(tmp_path / "newer.whl", version="0.10.0")
    with pytest.raises(ValueError, match="does not allow core 0.10.0"):
        cli.validate_lock(project, str(newer))


def test_the_installed_core_must_match_the_locked_dependencies(project, tmp_path, monkeypatch):
    wheel = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    write_lock(project, wheel)
    monkeypatch.setattr(cli.distributions, "requires", lambda name: list(CORE_REQUIRES))
    cli.validate_installed_core(project)
    monkeypatch.setattr(cli.distributions, "requires", lambda name: ["pydantic>=2.11"])
    with pytest.raises(ValueError, match="Installed core dependencies changed"):
        cli.validate_installed_core(project)


def test_a_local_core_stays_an_absolute_operand_and_a_released_core_is_pinned(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli.core_install_spec(None, "0.9.4") == "heinzel==0.9.4"
    assert cli.core_install_spec("https://example.org/core.whl", "0.9.4") == "https://example.org/core.whl"
    assert cli.core_install_spec("-sneaky.whl", "0.9.4") == str(tmp_path.resolve() / "-sneaky.whl")


def test_the_environment_is_built_from_hashes_then_core_then_the_plugin_without_resolution(project, tmp_path, commands):
    wheel = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    write_lock(project, wheel)
    interpreter = cli.prepare_environment(project, str(wheel))
    assert interpreter == project.directory / ".venv/bin/python"
    steps = [command[:3] for command, _ in commands]
    assert steps == [
        ["uv", "venv", "--python"],
        ["uv", "pip", "sync"],
        ["uv", "pip", "install"],
        ["uv", "pip", "install"],
        ["uv", "pip", "check"],
    ]
    sync = commands[1][0]
    assert "--require-hashes" in sync and "--no-build" in sync
    assert all("--no-deps" in command for command, _ in commands[2:4])
    assert "--editable" in commands[3][0]
    assert str(wheel.resolve()) in commands[2][0]


def test_an_existing_environment_is_reused(project, tmp_path, commands):
    wheel = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    write_lock(project, wheel)
    (project.directory / ".venv/bin").mkdir(parents=True)
    (project.directory / ".venv/bin/python").write_text("")
    cli.prepare_environment(project, None)
    assert ["uv", "venv"] not in [command[:2] for command, _ in commands]
    assert any("heinzel==0.9.4" in command for command, _ in commands)


def test_commands_run_only_from_the_plugins_own_environment(project):
    assert cli.python_command(project, None, ["ruff", "check"]) == [
        str(project.directory / ".venv/bin/ruff"),
        "check",
    ]


def test_a_plugin_with_its_own_ruff_policy_gets_no_default_configuration(project):
    assert [argument for argument in cli.ruff_configuration(project) if argument.startswith("lint.")] == [
        'lint.isort.known-first-party=["heinzel_harbor"]'
    ]
    owned = cli.Project(project.directory, project.name, project.version, project.metadata | {"tool": {"ruff": {}}})
    assert cli.ruff_configuration(owned) == []


def test_fixing_formats_checks_and_formats_again_after_refreshing_a_stale_lock(project, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "lock", lambda p, core: calls.append(("lock", core)))
    monkeypatch.setattr(cli, "prepare_environment", lambda p, core: calls.append(("prepare", core)))
    monkeypatch.setattr(cli, "run", lambda command, **options: calls.append((Path(command[0]).name, command[1:3])))
    (project.directory / "plugin-lock.json").write_text(json.dumps({"inputs": ["stale"]}))
    cli.fix(project, "candidate.whl")
    assert calls == [
        ("lock", "candidate.whl"),
        ("prepare", "candidate.whl"),
        ("ruff", ["format", "src"]),
        ("ruff", ["check", "--fix"]),
        ("ruff", ["format", "src"]),
    ]


def test_fixing_keeps_a_fresh_lock(project, tmp_path, monkeypatch):
    wheel = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    write_lock(project, wheel)
    monkeypatch.setattr(cli, "lock", lambda *a: pytest.fail("A fresh lock must not be rewritten"))
    monkeypatch.setattr(cli, "prepare_environment", lambda *a: None)
    monkeypatch.setattr(cli, "run", lambda *a, **k: None)
    cli.fix(project, None)


def test_building_the_frontend_is_skipped_unless_it_declares_a_build_script(project, commands):
    cli.build_view_assets(project)
    (project.directory / "web").mkdir()
    (project.directory / "web/package.json").write_text(json.dumps({"scripts": {"test": "vitest"}}))
    cli.build_view_assets(project)
    assert commands == []
    (project.directory / "web/package.json").write_text(json.dumps({"scripts": {"build": "vite build"}}))
    cli.build_view_assets(project)
    assert commands[0][0][-2:] == ["run", "build"]


def test_a_full_check_runs_strict_types_coverage_typos_and_the_frontend_gates(project, monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "prepare_environment", lambda *a: None)
    monkeypatch.setattr(cli, "run", lambda command, **options: calls.append(command))
    (project.directory / "web").mkdir()
    (project.directory / "web/package.json").write_text(json.dumps({"scripts": {"lint": "x", "test": "y"}}))
    cli.check(project, None)
    names = [Path(command[0]).name for command in calls]
    assert names[:2] == ["python", "ruff"]
    assert {"mypy", "pyright", "coverage", "typos"} <= set(names)
    assert [c[-1] for c in calls if c[0] == "uv"] == ["lint", "test"]


def test_the_test_only_loop_skips_lint_and_types_and_reports_nothing_but_tests(project, monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "prepare_environment", lambda *a: None)
    monkeypatch.setattr(cli, "run", lambda command, **options: calls.append(command))
    cli.check(project, None, tests_only=True)
    names = {Path(command[0]).name for command in calls}
    assert "pytest" in names and not names & {"ruff", "mypy", "pyright", "coverage", "typos"}


def test_a_recorded_gallery_is_checked_before_the_environment_is_prepared(project, monkeypatch):
    order = []
    monkeypatch.setattr(cli, "check_screenshots", lambda p: order.append("screenshots"))
    monkeypatch.setattr(cli, "prepare_environment", lambda *a: order.append("environment"))
    monkeypatch.setattr(cli, "run", lambda *a, **k: None)
    (project.directory / "docs").mkdir()
    (project.directory / "docs/screenshots.toml").write_text("")
    cli.check(project, None, fast=True)
    assert order == ["screenshots", "environment"]


def test_building_uses_the_lock_as_the_only_build_constraint(project, tmp_path, commands):
    wheel = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    write_lock(project, wheel)
    cli.build(project)
    ((command, _),) = commands
    assert command[:2] == ["uv", "build"]
    assert command[command.index("--build-constraints") + 1] == str(project.directory / "requirements.lock")


def test_release_info_names_the_independent_tag_and_exact_artifacts(project, monkeypatch):
    monkeypatch.setattr(cli, "ROOT", project.directory.parents[1])
    dist = project.directory / "dist"
    dist.mkdir()
    (dist / "heinzel_harbor-0.2.0-py3-none-any.whl").write_bytes(b"w")
    (dist / "heinzel_harbor-0.2.0.tar.gz").write_bytes(b"s")
    (dist / "heinzel_harbor-0.1.0-py3-none-any.whl").write_bytes(b"old")
    info = cli.release_info(project)
    assert info["tag"] == "heinzel-harbor/v0.2.0"
    assert info["path"] == "plugins/heinzel-harbor"
    assert [Path(path).name for path in info["artifacts"]] == [
        "heinzel_harbor-0.2.0-py3-none-any.whl",
        "heinzel_harbor-0.2.0.tar.gz",
    ]


def test_release_info_refuses_a_non_canonical_version(project):
    odd = cli.Project(project.directory, project.name, "0.02.0", project.metadata)
    with pytest.raises(ValueError, match="canonical plugin version"):
        cli.release_info(odd)


def wheel_for(project, directory, *, requires="Requires-Dist: heinzel>=0.9.1,<0.10\n", version=None):
    version = version or project.version
    path = directory / f"{project.name.replace('-', '_')}-{version}-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            f"{project.name.replace('-', '_')}-{version}.dist-info/METADATA",
            f"Name: {project.name}\nVersion: {version}\n{requires}",
        )
    return path


def standard(project):
    options = {"tool": {"heinzel": {"plugin": {"profiles": ["standard"]}}}}
    return cli.Project(project.directory, project.name, project.version, project.metadata | options)


def test_a_profile_pins_core_and_each_standard_plugin_wheel_by_digest(project, tmp_path):
    member = standard(project)
    (member.directory / "dist").mkdir()
    plugin = wheel_for(member, member.directory / "dist")
    core = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    destination = tmp_path / "out/standard.json"
    result = cli.profile([member, project], core, destination, "https://example.org/files/")
    assert json.loads(destination.read_text()) == result
    assert result["core_version"] == "0.9.4"
    by_name = {item["name"]: item for item in result["artifacts"]}
    assert set(by_name) == {"heinzel", "heinzel-harbor"}
    assert by_name["heinzel-harbor"]["sha256"] == hashlib.sha256(plugin.read_bytes()).hexdigest()
    assert by_name["heinzel-harbor"]["url"] == f"https://example.org/files/{plugin.name}"


def test_a_standard_plugin_must_be_built_before_a_profile_is_drafted(project, tmp_path):
    core = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    with pytest.raises(ValueError, match="Build heinzel-harbor 0.2.0 first"):
        cli.profile([standard(project)], core, tmp_path / "standard.json", None)


def test_a_plugin_outside_the_core_range_cannot_join_the_profile(project, tmp_path):
    member = standard(project)
    (member.directory / "dist").mkdir()
    wheel_for(member, member.directory / "dist", requires="Requires-Dist: heinzel>=0.8,<0.9\n")
    core = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    with pytest.raises(ValueError, match="does not support core 0.9.4"):
        cli.profile([member], core, tmp_path / "standard.json", None)


def test_selected_wheels_replace_the_dist_directory_lookup(project, tmp_path):
    member = standard(project)
    plugin = wheel_for(member, tmp_path)
    core = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    result = cli.profile([member], core, tmp_path / "p.json", None, selected_wheels={member.name: plugin})
    assert [item["name"] for item in result["artifacts"]] == ["heinzel", "heinzel-harbor"]
    with pytest.raises(ValueError, match="Build heinzel-harbor"):
        cli.profile([member], core, tmp_path / "p.json", None, selected_wheels={})


def test_the_accepted_profile_is_published_unchanged_with_only_urls_rewritten(project, tmp_path):
    core = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    candidate = tmp_path / "candidate.json"
    accepted = cli.profile([], core, candidate, None)
    result = cli.write_accepted_profile(accepted, candidate, tmp_path / "pub/standard.json", "https://example.org/dl")
    assert result["artifacts"][0]["url"] == "https://example.org/dl/" + core.name
    assert result["artifacts"][0]["sha256"] == accepted["artifacts"][0]["sha256"]
    assert json.loads((tmp_path / "pub/standard.json").read_text()) == result


def test_a_profile_changed_after_acceptance_is_refused(project, tmp_path):
    core = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    candidate = tmp_path / "candidate.json"
    accepted = cli.profile([], core, candidate, None)
    candidate.write_text(json.dumps(accepted | {"core_version": "9.9.9"}))
    with pytest.raises(ValueError, match="changed during installed acceptance"):
        cli.write_accepted_profile(accepted, candidate, tmp_path / "out.json", None)


def test_an_artifact_swapped_after_acceptance_is_refused(tmp_path):
    core = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    candidate = tmp_path / "candidate.json"
    accepted = cli.profile([], core, candidate, None)
    core.write_bytes(b"swapped")
    with pytest.raises(ValueError, match="accepted artifact changed"):
        cli.write_accepted_profile(accepted, candidate, tmp_path / "out.json", None)


def test_a_copied_artifact_that_differs_from_the_accepted_bytes_is_refused(tmp_path):
    core = core_wheel(tmp_path / "heinzel-0.9.4-py3-none-any.whl")
    candidate = tmp_path / "candidate.json"
    accepted = cli.profile([], core, candidate, None)
    copies = tmp_path / "copies"
    copies.mkdir()
    (copies / core.name).write_bytes(b"corrupted copy")
    with pytest.raises(ValueError, match="copied artifact differs"):
        cli.write_accepted_profile(accepted, candidate, tmp_path / "out.json", None, artifact_directory=copies)
    (copies / core.name).write_bytes(core.read_bytes())
    cli.write_accepted_profile(accepted, candidate, tmp_path / "out.json", None, artifact_directory=copies)


def test_a_composition_without_core_is_refused(tmp_path, project):
    member = standard(project)
    plugin = wheel_for(member, tmp_path)
    with pytest.raises(ValueError, match="Read the core artifact before plugins"):
        cli.profile([member], plugin, tmp_path / "p.json", None, selected_wheels={member.name: plugin})
