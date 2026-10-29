"""App composition must consume the already released and accepted plugin bytes."""

import hashlib
import json
import runpy
import zipfile
from pathlib import Path

import pytest

from heinzel_plugin_tools.cli import Project

pytestmark = pytest.mark.unit


def test_composition_never_rebuilds_an_independently_released_plugin(tmp_path, monkeypatch):
    compose = runpy.run_path(str(Path(__file__).parents[1] / "scripts/compose.py"))["compose"]
    scope = compose.__globals__
    destination = tmp_path / "composition"
    destination.mkdir()
    core = destination / "heinzel-0.9.1-py3-none-any.whl"
    with zipfile.ZipFile(core, "w") as archive:
        archive.writestr("heinzel-0.9.1.dist-info/METADATA", "Name: heinzel\nVersion: 0.9.1\n")
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

    def restore(repository, tag, name, target):
        assert (repository, tag, name) == ("example/plugins", "heinzel-unforeseen/v1.0.0", project.name)
        target.mkdir(parents=True)
        wheel = target / "heinzel_unforeseen-1.0.0-py3-none-any.whl"
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr(
                "heinzel_unforeseen-1.0.0.dist-info/METADATA",
                "Name: heinzel-unforeseen\nVersion: 1.0.0\nRequires-Dist: heinzel>=0.9.1,<0.10\n",
            )
        released.append(wheel.read_bytes())
        return {"artifacts": [str(wheel)]}

    def run(command, **_):
        calls.append(command)
        if command[:2] == ["uv", "venv"]:
            Path(command[-1]).mkdir()

    monkeypatch.setenv("GH_REPO", "example/plugins")
    monkeypatch.setitem(scope, "projects", lambda: [project])
    monkeypatch.setitem(scope, "validate_lock", lambda *_: {})
    monkeypatch.setitem(scope, "restore", restore)
    monkeypatch.setitem(scope, "acceptance", lambda *_, wheel: accepted.append(wheel.read_bytes()))
    monkeypatch.setitem(scope, "run", run)
    compose(core, destination, "https://example.test/releases/app-v0.9.1")
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
