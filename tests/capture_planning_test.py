"""The screenshot definition is a hand-edited JSON file; capture reads it and never plans."""

import json

import pytest

from heinzel_plugin_tools import capture, planning, privacy

pytestmark = pytest.mark.unit


@pytest.fixture
def owner(tmp_path):
    (tmp_path / "src/heinzel_harbor").mkdir(parents=True)
    (tmp_path / "src/heinzel_harbor/__init__.py").write_text('raise RuntimeError("do not import while planning")\n')
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="heinzel-harbor"\nversion="0.1.0"\n'
        '[project.entry-points."heinzel.modules"]\nharbor="heinzel_harbor"\n'
    )
    return tmp_path


def test_init_writes_a_canonical_editable_definition_once(owner):
    capture.write_default_plan(owner)
    path = owner / planning.DEFINITION
    text = path.read_text()
    plan = json.loads(text)
    assert text == planning.definition_text(plan)
    assert plan["format"] == 1 and len(plan["scenes"]) == 3
    plan["scenes"][0]["caption"] = "My own caption for the fictional harbor"
    planning.write_definition(owner, plan)
    capture.write_default_plan(owner)
    assert capture.read_plan(owner)["scenes"][0]["caption"] == "My own caption for the fictional harbor"


def test_an_edited_definition_is_validated_before_anything_runs(owner):
    capture.write_default_plan(owner)
    path = owner / planning.DEFINITION
    plan = json.loads(path.read_text())
    plan["scenes"][0]["route"] = "https://example.com/"
    path.write_text(json.dumps(plan))
    with pytest.raises(privacy.CaptureError, match="route must stay inside the local app"):
        capture.read_plan(owner)


@pytest.mark.parametrize("text", ["{not json", "[]", "x" * (70 * 1024)])
def test_a_broken_definition_is_a_clear_error(owner, text):
    (owner / "docs").mkdir()
    (owner / planning.DEFINITION).write_text(text)
    with pytest.raises(privacy.CaptureError):
        capture.read_plan(owner)


def test_a_missing_definition_reads_as_the_deterministic_default(owner):
    assert capture.read_plan(owner) == capture.validate_plan(owner, capture.default_plan(owner))
    assert not (owner / planning.DEFINITION).exists()
