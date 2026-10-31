"""Published plugins carry real UI and CLI captures for their public catalog galleries."""

import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("project", sorted((ROOT / "plugins").glob("*/pyproject.toml")), ids=lambda p: p.parent.name)
def test_every_plugin_publishes_ui_and_cli_screenshots(project):
    data = tomllib.loads(project.read_text())
    catalog = data["tool"]["heinzel"]["catalog"]
    shots = catalog["screenshots"]
    assert 2 <= len(shots) <= 8
    assert {shot["surface"] for shot in shots} == {"ui", "cli"}
    for shot in shots:
        assert shot["caption"].strip()
        path = project.parent / shot["path"]
        assert path.resolve().is_relative_to(project.parent.resolve())
        assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert 0 < path.stat().st_size <= 500 * 1024
    if catalog.get("themes"):
        assert any("dark" in shot["caption"].lower() for shot in shots if shot["surface"] == "ui")
