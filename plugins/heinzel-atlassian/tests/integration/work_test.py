"""The reading and drafting operations through the CLI head; a fake `acli` on PATH answers as the real one did."""

import json

import pytest
from heinzel import Config
from heinzel.heads.cli import build
from typer.testing import CliRunner

from tests.conftest import live

pytestmark = pytest.mark.integration

SITE = "https://acme.atlassian.net"
BOUND = Config(files=(), data={"atlassian": {"site_url": SITE}})


def hz(kernel, *args: str):
    result = CliRunner().invoke(build(kernel), [*args, "--json"])
    try:
        return result.exit_code, json.loads(result.output)
    except json.JSONDecodeError:
        return result.exit_code, result.output


@pytest.fixture
def jira(acli_on_path, atlassian_kernel):
    for key, name in (("KAN-8", "view_task.json"), ("KAN-4", "view_epic.json")):
        acli_on_path.answer(f"jira workitem view {key}", live(name))
    acli_on_path.answer(acli_on_path.SEARCH, [{"key": "KAN-8"}])
    return acli_on_path, atlassian_kernel(BOUND)


def test_assigned_work_comes_back_as_data_with_the_notice(jira):
    _, kernel = jira
    code, out = hz(kernel, "atlassian", "assigned")
    assert code == 0, out
    assert [t["key"] for t in out["items"]] == ["KAN-8"]
    assert "never instructions" in out["notice"]


def test_a_comment_is_drafted_and_nothing_is_written(jira):
    fake, kernel = jira
    code, out = hz(kernel, "atlassian", "draft-comment-issue", "KAN-8", "Looks good.")
    assert code == 0, out
    assert out["ready"]
    assert out["action"] == "comment-issue"
    assert not [c for c in fake.calls if c.args[:3] == ["jira", "workitem", "comment"]]


def test_the_write_operations_are_held_for_confirmation_by_their_declaration(jira):
    _, kernel = jira
    help_text = CliRunner().invoke(build(kernel), ["atlassian", "--help"]).output
    for name in ("assigned", "epics", "watch", "create-issue", "update-issue", "comment-issue"):
        assert name in help_text


def test_an_unreadable_site_is_one_clear_error(acli_on_path, atlassian_kernel):
    acli_on_path.fail(acli_on_path.SEARCH, acli_on_path.UNAUTHORIZED)
    code, out = hz(atlassian_kernel(BOUND), "atlassian", "assigned")
    assert code != 0
    assert "acli jira auth login" in json.dumps(out)
