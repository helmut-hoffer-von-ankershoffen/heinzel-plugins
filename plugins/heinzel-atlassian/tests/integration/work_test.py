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
    """Run `hz ... --json`: the exit code and the parsed result; for a failure, just its message."""
    result = CliRunner().invoke(build(kernel), [*args, "--json"])
    try:
        output = json.loads(result.output)
    except json.JSONDecodeError:
        output = result.output
    return result.exit_code, failure_message(output) if result.exit_code else output


def failure_message(output: object) -> object:
    """The message of a failed command, as Core prints it under `--json`: `Error: ...` text or an `error` object."""
    if isinstance(output, dict) and isinstance(output.get("error"), str):
        return output["error"]
    if isinstance(output, str):
        return output.strip().removeprefix("Error:").strip()
    return output


def test_a_failure_reads_the_same_as_text_or_as_a_json_error_object():
    assert failure_message("Error: gh is missing\n") == "gh is missing"
    assert failure_message({"error": "gh is missing", "code": "not_supported"}) == "gh is missing"
    assert failure_message({"checks": []}) == {"checks": []}  # a result that sets the exit code stays as it is


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


def test_everyday_work_operations_are_listed_in_cli_help(jira):
    _, kernel = jira
    help_text = CliRunner().invoke(build(kernel), ["atlassian", "--help"]).output
    for name in ("assigned", "epics", "watch", "create-issue", "update-issue", "comment-issue"):
        assert name in help_text


def test_an_unreadable_site_is_one_clear_error(acli_on_path, atlassian_kernel):
    acli_on_path.fail(acli_on_path.SEARCH, acli_on_path.UNAUTHORIZED)
    code, out = hz(atlassian_kernel(BOUND), "atlassian", "assigned")
    assert code != 0
    assert "acli jira auth login" in json.dumps(out)
