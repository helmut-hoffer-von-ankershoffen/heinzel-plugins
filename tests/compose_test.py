"""App composition must consume the already released and accepted plugin bytes."""

import hashlib
import json
import runpy
import zipfile
from pathlib import Path

import pytest

from heinzel_plugin_tools.cli import Project

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "changed",
    [None, "source", "copy", "profile", "restore", "plugin-acceptance", "core-before", "core-install", "core-after"],
)
def test_composition_never_rebuilds_an_independently_released_plugin(tmp_path, monkeypatch, changed):
    compose = runpy.run_path(str(Path(__file__).parents[1] / "scripts/compose.py"))["compose"]
    scope = compose.__globals__
    destination = tmp_path / "composition"
    destination.mkdir()
    core = destination / "heinzel-0.9.1-py3-none-any.whl"
    with zipfile.ZipFile(core, "w") as archive:
        archive.writestr("heinzel-0.9.1.dist-info/METADATA", "Name: heinzel\nVersion: 0.9.1\n")
    core_digest = hashlib.sha256(core.read_bytes()).hexdigest()
    if changed == "core-before":
        core.write_bytes(core.read_bytes() + b"replaced verified core")
    directory = tmp_path / "plugins/heinzel-unforeseen"
    (directory / "tests/acceptance").mkdir(parents=True)
    project = Project(
        directory, "heinzel-unforeseen", "1.0.0", {"tool": {"heinzel": {"plugin": {"profiles": ["standard"]}}}}
    )
    # A stale local dist must not influence the selected release wheel.
    (directory / "dist").mkdir()
    (directory / "dist/heinzel_unforeseen-1.0.0-py3-none-any.whl").write_bytes(b"stale local artifact")
    accepted = []
    released = []
    calls = []
    managed = []
    monkeypatch.setenv("PYTHONPATH", "/a/checkout/must/not/override/the/sdk")
    monkeypatch.setenv("PYTHONHOME", "/an/unrelated/python")

    def restore(repository, tag, name, target):
        assert any("--dry-run" in command for command in calls)
        assert (repository, tag, name) == ("example/plugins", "heinzel-unforeseen/v1.0.0", project.name)
        target.mkdir(parents=True)
        wheel = target / "heinzel_unforeseen-1.0.0-py3-none-any.whl"
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr(
                "heinzel_unforeseen-1.0.0.dist-info/METADATA",
                "Name: heinzel-unforeseen\nVersion: 1.0.0\nRequires-Dist: heinzel>=0.9.1,<0.10\n",
            )
        released.append(wheel.read_bytes())
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        if changed == "restore":
            wheel.write_bytes(wheel.read_bytes() + b"replaced verified plugin")
        return {"artifacts": [str(wheel)], "artifact_hashes": {str(wheel): digest}}

    def run(command, **kwargs):
        calls.append(command)
        assert "PYTHONPATH" not in kwargs["env"]
        assert "PYTHONHOME" not in kwargs["env"]
        if str(command[0]).endswith("/bin/python"):
            assert command[1] == "-I"
            assert command.count("-I") == 1
        if command[:2] == ["uv", "venv"]:
            Path(command[-1]).mkdir()
            if changed == "core-install":
                core.write_bytes(core.read_bytes() + b"replaced before install")
        if "--dry-run" in command:
            probe = json.loads(Path(command[-1]).read_text())
            assert (probe["format"], probe["sdk"]) == (2, 1)
            assert [item["name"] for item in probe["artifacts"]] == ["heinzel"]

    monkeypatch.setenv("GH_REPO", "example/plugins")
    monkeypatch.setitem(scope, "projects", lambda: [project])
    monkeypatch.setitem(scope, "validate_lock", lambda *_: {})
    monkeypatch.setitem(scope, "restore", restore)

    def accept_plugin(*_args, wheel):
        accepted.append(wheel.read_bytes())
        if changed == "plugin-acceptance":
            wheel.write_bytes(wheel.read_bytes() + b"replaced during acceptance")

    monkeypatch.setitem(scope, "acceptance", accept_plugin)
    monkeypatch.setitem(scope, "run", run)

    def verify_managed(_interpreter, candidate):
        value = json.loads(candidate.read_text())
        managed.append(value)
        artifact = value["artifacts"][1]
        if changed in {"source", "copy"}:
            path = Path(artifact["url"]) if changed == "source" else destination / artifact["filename"]
            path.write_bytes(path.read_bytes() + b"changed after acceptance")
        elif changed == "profile":
            candidate.write_text(json.dumps(value | {"sdk": 99}))
        elif changed == "core-after":
            core.write_bytes(core.read_bytes() + b"replaced core after acceptance")

    monkeypatch.setitem(scope, "verify_managed_profile", verify_managed)
    if changed:
        with pytest.raises(ValueError, match="changed|differs"):
            compose(core, destination, "https://example.test/releases/app-v0.9.1", core_sha256=core_digest)
        assert not (destination / "standard.json").exists()
        if changed in {"core-before", "core-install"}:
            assert not any(command[:3] == ["uv", "pip", "install"] for command in calls)
        if changed == "restore":
            assert accepted == []
        return
    compose(core, destination, "https://example.test/releases/app-v0.9.1", core_sha256=core_digest)
    plugin = next(
        item
        for item in json.loads((destination / "standard.json").read_text())["artifacts"]
        if item["name"] == project.name
    )
    assert accepted == released
    assert (destination / plugin["filename"]).read_bytes() == released[0]
    assert plugin["sha256"] == hashlib.sha256(released[0]).hexdigest()
    assert not (destination / ".verified").exists()
    assert not any("build" in command or "pytest" in command for command in calls)
    assert json.loads((destination / "standard.json").read_text())["format"] == 2
    assert len(managed) == 1
    assert managed[0]["artifacts"][1]["sha256"] == plugin["sha256"]


def test_legacy_sdk_is_refused_before_any_provider_restoration_or_acceptance(tmp_path, monkeypatch):
    compose = runpy.run_path(str(Path(__file__).parents[1] / "scripts/compose.py"))["compose"]
    scope = compose.__globals__
    destination = tmp_path / "composition"
    destination.mkdir()
    core = destination / "heinzel-0.9.1-py3-none-any.whl"
    with zipfile.ZipFile(core, "w") as archive:
        archive.writestr("heinzel-0.9.1.dist-info/METADATA", "Name: heinzel\nVersion: 0.9.1\n")
    project = Project(
        tmp_path / "plugin", "heinzel-harbor", "1.0.0", {"tool": {"heinzel": {"plugin": {"profiles": ["standard"]}}}}
    )

    def run(command, **_kwargs):
        if "--dry-run" in command:
            raise SystemExit(2)

    def provider(*_args, **_kwargs):
        pytest.fail("An incompatible SDK must be refused before any provider work")

    monkeypatch.setenv("GH_REPO", "example/plugins")
    monkeypatch.setitem(scope, "projects", lambda: [project])
    monkeypatch.setitem(scope, "run", run)
    for name in ("validate_lock", "restore", "acceptance"):
        monkeypatch.setitem(scope, name, provider)
    with pytest.raises(SystemExit) as failure:
        compose(core, destination, "https://example.test/release")
    assert failure.value.code == 2
    assert not (destination / "standard.json").exists()
