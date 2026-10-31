"""Source-based definitions precede execution and remain editable without a hidden bypass."""

import json
from types import SimpleNamespace

import pytest

from heinzel_plugin_tools import capture, planning

pytestmark = pytest.mark.unit


@pytest.fixture
def owner(tmp_path):
    (tmp_path / "src/heinzel_harbor").mkdir(parents=True)
    (tmp_path / "src/heinzel_harbor/__init__.py").write_text('raise RuntimeError("do not import while planning")\n')
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="heinzel-harbor"\nversion="0.1.0"\n'
        '[project.entry-points."heinzel.modules"]\nharbor="heinzel_harbor"\n'
    )
    (tmp_path / "README.md").write_text("# Harbor\nA fictional useful harbor.\n")
    capture.write_default_plan(tmp_path)
    return tmp_path


def test_missing_agent_cannot_silently_publish_default_help_and_plugin_cards(owner, monkeypatch):
    monkeypatch.setattr(planning.shutil, "which", lambda _: None)
    with pytest.raises(ValueError, match="source analysis needs"):
        planning.ensure_definition(owner)
    assert not (owner / capture.OUTPUT).exists()


def test_source_analysis_gets_only_regular_owned_sources_and_preserves_editable_plan(owner, monkeypatch):
    (owner / ".preview").mkdir()
    (owner / ".preview/private.txt").write_text("private state")
    (owner / "secret.txt").write_text("not a source input")
    calls = []

    def run(command, **kwargs):
        folder = owner.__class__(command[command.index("--cd") + 1])
        assert (folder / "src/heinzel_harbor/__init__.py").is_file()
        assert not (folder / ".preview").exists()
        assert not (folder / "secret.txt").exists()
        assert "--sandbox" in command and "read-only" in command
        assert "--ephemeral" in command
        response = {
            "format": 1,
            "story": "# Synthetic story\nUseful greeting examples in two UI scenes and actual CLI output.",
            "plan_toml": (owner / capture.PLAN).read_text(),
        }
        owner.__class__(command[-1]).write_text(json.dumps(response))
        calls.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(planning.shutil, "which", lambda _: "/safe/codex")
    monkeypatch.setattr(planning.subprocess, "run", run)
    definition = planning.ensure_definition(owner)
    assert definition["reviewer"] == "Codex feature-story agent"
    assert len(calls) == 1
    assert planning.ensure_definition(owner) == definition
    assert len(calls) == 1
    assert planning.validate_definition(owner, capture.read_plan(owner)) == definition


@pytest.mark.parametrize("change", ["source", "plan", "story", "fixture"])
def test_definition_receipt_binds_source_plan_story_and_fixture(owner, change):
    fixture = owner / "docs/fixture.py"
    fixture.write_text("# Fictional fixture\n")
    path = owner / capture.PLAN
    path.write_text(path.read_text().replace("format = 1", 'format = 1\nbootstrap = "docs/fixture.py"'))
    plan = capture.read_plan(owner)
    planning.record_definition(
        owner,
        plan,
        "# Synthetic agent story\nActual CLI results and two UI views with fictional data.",
        reviewer="Synthetic test source agent",
    )
    if change == "source":
        (owner / "src/heinzel_harbor/__init__.py").write_text("# changed\n")
    elif change == "plan":
        plan["scenes"][0]["caption"] = "A different screenshot purpose"
    elif change == "story":
        (owner / planning.STORY).write_text("Changed after analysis")
    else:
        fixture.write_text("# changed demonstration data\n")
    with pytest.raises(ValueError, match="definition is stale"):
        planning.validate_definition(owner, plan)
