"""The small author loop and immutable release flow work without core sources or real providers."""

import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

from heinzel_plugin_tools import cli, publishing

pytestmark = pytest.mark.unit


@pytest.fixture
def project(tmp_path):
    directory = tmp_path / "plugins/heinzel-unforeseen"
    (directory / "src").mkdir(parents=True)
    metadata = {
        "project": {
            "name": "heinzel-unforeseen",
            "version": "1.0.0",
            "dependencies": ["heinzel>=0.9.1,<0.10"],
            "entry-points": {"heinzel.modules": {"unforeseen": "heinzel_unforeseen"}},
        },
        "build-system": {"requires": []},
    }
    return cli.Project(directory, "heinzel-unforeseen", "1.0.0", metadata)


def wheel(path, name="heinzel-unforeseen", version="1.0.0"):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            f"{name.replace('-', '_')}-{version}.dist-info/METADATA", f"Name: {name}\nVersion: {version}\n"
        )
    return path


def test_fast_loop_checks_only_own_lint_and_unit_behavior(project, monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "prepare_environment", lambda *_: project.directory / ".venv/bin/python")
    monkeypatch.setattr(cli, "run", lambda command, **_: calls.append(command))
    cli.check(project, "candidate.whl", fast=True)
    assert any("--no-fix" in command for command in calls)
    assert any("unit and not perf" in command for command in calls)
    assert not any("mypy" in Path(command[0]).name or "coverage" in command or "typos" in command for command in calls)
    assert all("heinzel_unrelated" not in " ".join(command) for command in calls)


@pytest.mark.parametrize("mutate", [False, True])
def test_acceptance_uses_the_supplied_wheel_and_refuses_changed_bytes(project, tmp_path, monkeypatch, mutate):
    artifact = wheel(tmp_path / "heinzel_unforeseen-1.0.0-py3-none-any.whl")
    (project.directory / "tests/acceptance").mkdir(parents=True)
    monkeypatch.setattr(cli, "validate_lock", lambda *_: {"core": {"version": "0.9.1"}})
    monkeypatch.setattr(cli, "build", lambda *_: pytest.fail("Prebuilt acceptance must not rebuild"))
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        if "pytest" in command and mutate:
            artifact.write_bytes(b"changed during acceptance")

    monkeypatch.setattr(cli, "run", run)
    if mutate:
        with pytest.raises(ValueError, match="changed during acceptance"):
            cli.acceptance(project, "candidate.whl", wheel=artifact)
    else:
        cli.acceptance(project, "candidate.whl", wheel=artifact)
        assert any(str(artifact) in command for command, _ in calls)
        tests = next(kwargs for command, kwargs in calls if "pytest" in command)
        assert tests["env"]["PLUGIN_TEST_WHEEL"] == str(artifact)


def test_mislabeled_wheel_is_refused_before_installation(project, tmp_path, monkeypatch):
    artifact = wheel(tmp_path / "heinzel_unforeseen-1.0.0-py3-none-any.whl", name="another-provider")
    monkeypatch.setattr(cli, "validate_lock", lambda *_: {"core": {"version": "0.9.1"}})
    calls = []
    monkeypatch.setattr(cli, "run", lambda command, **_: calls.append(command))
    with pytest.raises(ValueError, match="metadata differs"):
        cli.acceptance(project, "candidate.whl", wheel=artifact)
    assert not any("install" in command for command in calls)


def test_registry_default_selects_only_compatible_stable_non_yanked_core(project, monkeypatch):
    def files(version, *, yanked=False):
        return [
            {
                "filename": f"heinzel-{version}-py3-none-any.whl",
                "url": f"https://example.test/{version}.whl",
                "yanked": yanked,
            }
        ]

    payload = {
        "releases": {
            "0.9.0": files("0.9.0"),
            "0.9.1": files("0.9.1"),
            "0.9.2": files("0.9.2", yanked=True),
            "0.9.3rc1": files("0.9.3rc1"),
            "0.10.0": files("0.10.0"),
        }
    }
    monkeypatch.setattr(cli.urllib.request, "urlopen", lambda *_, **__: io.BytesIO(json.dumps(payload).encode()))
    assert cli.released_core(project) == "https://example.test/0.9.1.whl"


def test_setup_never_creates_an_embedded_standalone_repository(project, tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    project.metadata["tool"] = {"heinzel": {"plugin": {"layout": "standalone"}}}
    monkeypatch.setattr(cli, "run", lambda *_: pytest.fail("Do not initialize an embedded repository"))
    with pytest.raises(ValueError, match="--layout collection"):
        cli.setup(project, "candidate.whl")
    assert not (project.directory / ".git").exists()


def test_local_release_has_no_alternate_upload_path(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["hz-plugin", "release", "unforeseen", "--publish"])
    monkeypatch.setattr(cli, "run", lambda *_: pytest.fail("Preview must not upload"))
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 2
    assert "protected release workflow" in capsys.readouterr().err


def test_scaffold_prints_the_portable_owning_directory_next_step(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "ROOT", tmp_path / "collection with spaces")
    destination = cli.ROOT / "plugins/heinzel-harbor"
    project = cli.Project(destination, "heinzel-harbor", "0.0.0", {})
    monkeypatch.setattr(cli, "run", lambda *_, **__: None)
    monkeypatch.setattr(cli, "projects", lambda *_: [project])
    monkeypatch.setattr(cli, "lock", lambda *_: None)
    monkeypatch.setattr(cli, "fix", lambda *_: None)
    cli.scaffold("harbor", "candidate.whl", "candidate-template", "HEAD", "minimal")
    output = capsys.readouterr().out
    assert f"cd '{destination}' && make check-fast\n" in output
    assert "NAME=" not in output


@pytest.mark.parametrize("private", [False, True])
def test_owning_publish_dispatches_the_generic_host_workflow_without_building_core(project, monkeypatch, private):
    revision = "a" * 40
    replies = iter(["main\n", "", revision, revision])
    monkeypatch.setattr(cli.subprocess, "check_output", lambda *_, **__: next(replies))
    monkeypatch.setattr(cli, "repository_private", lambda: private)
    commands = []
    monkeypatch.setattr(cli, "run", lambda command, **_: commands.append(command))
    cli.dispatch_publication(project, None)
    assert commands == [
        ["git", "fetch", "--quiet", "origin", "main"],
        [
            "gh",
            "workflow",
            "run",
            "release.yml",
            "--ref",
            "main",
            "--field",
            "plugin=heinzel-unforeseen",
            "--field",
            "publish=true",
            "--field",
            "registry=github" if private else "registry=pypi",
        ],
    ]


@pytest.fixture
def released_artifacts(tmp_path):
    whl = wheel(tmp_path / "heinzel_unforeseen-1.0.0-py3-none-any.whl")
    sdist = tmp_path / "heinzel_unforeseen-1.0.0.tar.gz"
    content = b"Name: heinzel-unforeseen\nVersion: 1.0.0\n"
    with tarfile.open(sdist, "w:gz") as archive:
        entry = tarfile.TarInfo("heinzel_unforeseen-1.0.0/PKG-INFO")
        entry.size = len(content)
        archive.addfile(entry, io.BytesIO(content))
    return {path.name: path.read_bytes() for path in (whl, sdist)}


@pytest.mark.parametrize("failure", [None, "digest", "provenance"])
def test_deferred_upload_verifies_original_commit_and_bytes_without_rebuilding(
    tmp_path, monkeypatch, released_artifacts, failure
):
    original = "a" * 40
    monkeypatch.setenv("GITHUB_SHA", "b" * 40)
    assets = [
        {"name": name, "size": len(data), "digest": "sha256:" + hashlib.sha256(data).hexdigest()}
        for name, data in released_artifacts.items()
    ]
    if failure == "digest":
        assets[0]["digest"] = "sha256:" + "0" * 64

    def api(path, **_):
        if "/git/ref/" in path:
            return {"object": {"type": "commit", "sha": original}}
        return {"draft": False, "assets": assets}

    calls = []

    def run(command, **_):
        calls.append(command)
        if command[:3] == ["gh", "release", "download"]:
            filename = command[command.index("--pattern") + 1]
            directory = Path(command[command.index("--dir") + 1])
            (directory / filename).write_bytes(released_artifacts[filename])
        elif failure == "provenance":
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(publishing, "api", api)
    monkeypatch.setattr(publishing.subprocess, "run", run)
    destination = tmp_path / "restored"
    if failure:
        with pytest.raises((ValueError, subprocess.CalledProcessError)):
            publishing.restore("example/plugins", "heinzel-unforeseen/v1.0.0", "unforeseen", destination)
    else:
        result = publishing.restore("example/plugins", "heinzel-unforeseen/v1.0.0", "unforeseen", destination)
        assert result["revision"] == original
        assert all(path.read_bytes() == released_artifacts[path.name] for path in destination.iterdir())
        verifications = [command for command in calls if command[:3] == ["gh", "attestation", "verify"]]
        assert len(verifications) == 2
        assert all(original in command and "--deny-self-hosted-runners" in command for command in verifications)
    assert all("uv" not in command for command in calls)


def test_named_make_fast_loop_reaches_the_owning_tool():
    root = Path(__file__).parents[1]
    make = shutil.which("make")
    assert make
    result = subprocess.run(  # noqa: S603 - resolved make executable, read-only dry-run arguments
        [make, "-n", "check-fast", "NAME=unforeseen"],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "hz-plugin check-fast" in result.stdout


@pytest.mark.parametrize(
    ("private", "requested", "expected"),
    [(True, None, "github"), (False, None, "pypi"), (False, "github", "github"), (True, "github", "github")],
)
def test_private_and_public_plugins_choose_their_intended_registry(private, requested, expected):
    assert cli.publication_registry(private, requested) == expected


def test_private_sources_cannot_be_sent_to_the_public_registry():
    with pytest.raises(ValueError, match="PyPI is public"):
        cli.publication_registry(True, "pypi")


def test_private_audit_never_sends_package_names_to_public_advisory_services(project, monkeypatch):
    monkeypatch.setenv("PLUGIN_PRIVATE", "true")
    monkeypatch.setattr(cli, "prepare_environment", lambda *_: project.directory / ".venv/bin/python")
    calls = []
    monkeypatch.setattr(cli, "run", lambda command, **_: calls.append(command))
    cli.audit(project, "candidate.whl")
    assert calls == []
    project.metadata["tool"] = {"heinzel": {"plugin": {"audit_command": ["internal-audit", "--offline"]}}}
    cli.audit(project, "candidate.whl")
    assert calls == [[str(project.directory / ".venv/bin/internal-audit"), "--offline"]]


def test_unknown_repository_visibility_stays_private(monkeypatch):
    monkeypatch.delenv("PLUGIN_PRIVATE", raising=False)

    def unavailable(*_, **__):
        raise FileNotFoundError("gh is unavailable")

    monkeypatch.setattr(cli.subprocess, "check_output", unavailable)
    assert cli.repository_private() is True
    monkeypatch.setenv("PLUGIN_PRIVATE", "false")
    assert cli.repository_private() is False
    monkeypatch.setenv("PLUGIN_PRIVATE", "unknown")
    with pytest.raises(ValueError, match="true or false"):
        cli.repository_private()


def test_preview_uses_only_own_isolated_state_and_stops_cleanly(project, monkeypatch, capsys):
    monkeypatch.setenv("VIRTUAL_ENV", "/unrelated/environment")
    monkeypatch.setenv("HZ_CONFIG_HOME", "/unrelated/configuration")
    monkeypatch.setattr(cli, "prepare_environment", lambda *_: project.directory / ".venv/bin/python")
    calls = []
    monkeypatch.setattr(cli, "run", lambda command, **kwargs: calls.append((command, kwargs)))
    cli.preview(project, "candidate.whl")
    [(_, options)] = calls
    assert "VIRTUAL_ENV" not in options["env"]
    assert options["env"]["HZ_CONFIG_HOME"] == str(project.directory / ".preview/config_home")
    assert options["env"]["HZ_PLUGINS_ENABLED"] == "true"

    def interrupted():
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "main", interrupted)
    assert cli.entrypoint() == 0
    assert capsys.readouterr().err == "Stopped.\n"


@pytest.mark.parametrize("modified", [False, True])
def test_release_stages_exact_accepted_bytes_and_refuses_modified_source(
    project, tmp_path, monkeypatch, released_artifacts, modified
):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    dist = project.directory / "dist"
    dist.mkdir()
    for name, content in released_artifacts.items():
        (dist / name).write_bytes(content)
    calls = []
    for name in ("check", "build", "audit"):
        monkeypatch.setattr(cli, name, lambda *_, name=name: calls.append(name))
    (project.directory / "tests/acceptance").mkdir(parents=True)
    accepted = []
    monkeypatch.setattr(cli, "acceptance", lambda *_, wheel: accepted.append((wheel, wheel.read_bytes())))

    def clean():
        if calls and modified:
            raise ValueError("Release verification requires clean committed sources")

    monkeypatch.setattr(cli, "require_clean_source", clean)
    monkeypatch.setattr(cli.subprocess, "check_output", lambda *_, **__: "a" * 40)
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    destination = tmp_path / "release-dist"
    if modified:
        with pytest.raises(ValueError, match="clean committed"):
            cli.verify_release(project, "candidate.whl", destination)
        assert not destination.exists()
    else:
        result = cli.verify_release(project, "candidate.whl", destination)
        assert result["revision"] == "a" * 40
        assert accepted == [
            (
                dist / "heinzel_unforeseen-1.0.0-py3-none-any.whl",
                released_artifacts["heinzel_unforeseen-1.0.0-py3-none-any.whl"],
            )
        ]
        assert {path.name: path.read_bytes() for path in destination.iterdir()} == released_artifacts


@pytest.mark.parametrize("problem", ["wheel-identity", "sdist-identity", "audit-mutation"])
def test_release_refuses_wrong_identity_or_changed_sdist_even_without_acceptance_tests(
    project, tmp_path, monkeypatch, released_artifacts, problem
):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    dist = project.directory / "dist"
    dist.mkdir()
    for name, content in released_artifacts.items():
        (dist / name).write_bytes(content)
    whl = dist / "heinzel_unforeseen-1.0.0-py3-none-any.whl"
    sdist = dist / "heinzel_unforeseen-1.0.0.tar.gz"
    if problem == "wheel-identity":
        wheel(whl, version="2.0.0")
    if problem == "sdist-identity":
        content = b"Name: another-provider\nVersion: 1.0.0\n"
        with tarfile.open(sdist, "w:gz") as archive:
            entry = tarfile.TarInfo("heinzel_unforeseen-1.0.0/PKG-INFO")
            entry.size = len(content)
            archive.addfile(entry, io.BytesIO(content))
    monkeypatch.setattr(cli, "require_clean_source", lambda: None)
    monkeypatch.setattr(cli, "check", lambda *_: None)
    monkeypatch.setattr(cli, "build", lambda *_: None)
    monkeypatch.setattr(cli, "audit", lambda *_: sdist.write_bytes(b"changed") if problem == "audit-mutation" else None)
    destination = tmp_path / "release-dist"
    with pytest.raises(ValueError, match="metadata differs|artifact changed"):
        cli.verify_release(project, "candidate.whl", destination)
    assert not destination.exists()
