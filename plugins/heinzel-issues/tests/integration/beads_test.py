"""The Beads connector through CLI and API heads, with a stand-in `bd` that answers in Beads' JSON shapes."""

import json

import pytest
from heinzel import Config
from heinzel.heads.cli import build
from typer.testing import CliRunner

import heinzel_issues

pytestmark = pytest.mark.integration


@pytest.fixture
def folder(tmp_path):
    board = tmp_path / "board"
    (board / ".beads").mkdir(parents=True)
    return board


def test_submit_work_finish_and_release(issues_kernel, folder, fake_bd, journey, tmp_path):
    journey(issues_kernel(folder, fake_bd), folder, fake_bd, tmp_path)


def test_a_refusal_is_explained(issues_kernel, folder, fake_bd):
    result = CliRunner().invoke(build(issues_kernel(folder, fake_bd)), ["issues", "show", "demo-404"])
    assert result.exit_code != 0
    assert "The tracker refused: Error: no issue found" in result.output


def test_a_malformed_id_never_reaches_the_tracker(issues_kernel, folder, fake_bd):
    result = CliRunner().invoke(build(issues_kernel(folder, fake_bd)), ["issues", "show", "--", "--all"])
    assert "is not an item id" in result.output


def test_a_missing_program_is_explained(issues_kernel, folder, tmp_path):
    result = json.loads(
        CliRunner().invoke(build(issues_kernel(folder, str(tmp_path / "no-bd"))), ["issues", "list", "--json"]).stdout
    )
    assert "is not installed" in result["problem"]


def test_a_folder_without_beads_is_explained(make_kernel, tmp_path):
    settings = {"issues": {"tracker": "beads", "beads": {"path": str(tmp_path)}}}
    kernel = make_kernel(builtins=True, config=Config(files=(), data=settings), issues=heinzel_issues.module)
    result = json.loads(CliRunner().invoke(build(kernel), ["issues", "list", "--json"]).stdout)
    assert not result["ready"]
    assert "has no .beads database" in result["problem"]
    assert result["fix"] == "hz setup issues"


def test_off_by_default_everywhere(make_kernel):
    kernel = make_kernel(builtins=True, issues=heinzel_issues.module)
    result = CliRunner().invoke(build(kernel), ["issues", "list"])
    assert result.exit_code == 0
    assert "Issue tracking is not set up. Run hz setup issues." in result.stdout
    sent = CliRunner().invoke(build(kernel), ["issues", "submit", "hello"])
    assert sent.exit_code != 0
    assert "not set up" in sent.output
    doctor = json.loads(CliRunner().invoke(build(kernel), ["system", "doctor", "--json"]).stdout)
    assert {"name": "tracker", "status": "up", "detail": "off; turn it on with hz setup issues", "fix": ""} in doctor[
        "checks"
    ]["issues"]
