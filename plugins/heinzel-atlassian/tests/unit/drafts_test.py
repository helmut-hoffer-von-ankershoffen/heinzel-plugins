"""Drafts change nothing; the write operations act only on a ready draft, once, and never on a changed work item."""

import json
from datetime import datetime
from pathlib import Path

import pytest
from heinzel import HeinzelError

from heinzel_atlassian import AtlassianSettings
from heinzel_atlassian._drafts import JiraDrafts, digest_of
from tests.conftest import live

pytestmark = pytest.mark.unit

SITE = "https://acme.atlassian.net"
GONE = "✗ Error: Issue does not exist or you do not have permission to see it."


def drafts(fake) -> JiraDrafts:
    return JiraDrafts(AtlassianSettings(site_url=SITE), fake)


class Jira:
    """A tiny Jira behind the fake acli: work items by key, and a record of every write."""

    def __init__(self, fake, *, existing: dict[str, dict] | None = None, labelled: list[str] | None = None):
        self.items = {"KAN-8": live("view_task.json"), "KAN-4": live("view_epic.json")} | (existing or {})
        self.labelled = labelled or []
        self.writes: list[list[str]] = []
        self.definitions: list[dict] = []
        self.fail: dict[str, tuple[int, str]] = {}
        fake.handler = self.handle

    def handle(self, args: list[str]):
        verb = " ".join(args[:3])
        if verb == "jira workitem view":
            return (0, json.dumps(self.items[args[3]]), "") if args[3] in self.items else (1, "", GONE)
        if verb == "jira workitem search":
            found = [{"key": k} for k in self.labelled]
            return 0, json.dumps(found), ""
        self.writes.append(args)
        if verb in self.fail:
            code, text = self.fail[verb]
            return code, "", text
        if verb == "jira workitem create":
            self.definitions.append(json.loads(Path(args[args.index("--from-json") + 1]).read_text(encoding="utf-8")))
            return 0, json.dumps({"key": "KAN-30"}), ""
        return 0, json.dumps({"results": [{"status": "SUCCESS"}]}), ""

    def written(self, verb: str) -> list[list[str]]:
        return [w for w in self.writes if " ".join(w[:3]) == verb]


CREATE = {
    "project": "kan",
    "kind": "Task",
    "summary": "Check the Dunmore offset",
    "parent": "KAN-4",
    "labels": ["harbor"],
}


def test_a_draft_of_a_new_item_shows_what_it_would_do_and_creates_nothing(fake_acli):
    jira = Jira(fake_acli)
    draft = drafts(fake_acli).draft_create(**CREATE, assign_to_me=True, due="2026-11-20")
    assert draft.ready
    assert draft.action == "create-issue"
    assert draft.arguments["project"] == "KAN"
    assert draft.preview[0] == "Create a Task in KAN: Check the Dunmore offset"
    assert any(line.startswith("Parent: KAN-4 (Epic)") for line in draft.preview)
    assert jira.writes == []


@pytest.mark.parametrize(
    ("changes", "problem"),
    [
        ({"summary": ""}, "A summary is needed."),
        ({"summary": "two\nlines"}, "must be one line"),
        ({"summary": "x" * 256}, "at most 255"),
        ({"kind": ""}, "type is needed"),
        ({"project": "no good"}, "not a Jira project key"),
        ({"kind": "Subtask", "parent": None}, "needs a parent"),
        ({"kind": "Epic"}, "An Epic has no parent"),
        ({"parent": "nope"}, "not a Jira work item key"),
        ({"due": "next week"}, "not a date"),
        ({"labels": ["has space"]}, "no spaces"),
        ({"description": "x\x00y"}, "NUL"),
    ],
)
def test_missing_or_wrong_fields_are_named_before_acli_is_asked_to_write(fake_acli, changes, problem):
    jira = Jira(fake_acli)
    draft = drafts(fake_acli).draft_create(**(CREATE | changes))
    assert not draft.ready
    assert any(problem in p for p in draft.problems), draft.problems
    with pytest.raises(HeinzelError, match="draft is not ready"):
        drafts(fake_acli).create_issue(**(CREATE | changes))
    assert jira.writes == []


def test_a_parent_that_does_not_exist_is_an_error_not_a_guess(fake_acli):
    Jira(fake_acli)
    with pytest.raises(HeinzelError, match="no KAN-99"):
        drafts(fake_acli).draft_create(**(CREATE | {"parent": "KAN-99"}))


def test_creating_sends_one_definition_with_an_idempotency_label(fake_acli):
    jira = Jira(fake_acli)
    applied = drafts(fake_acli).create_issue(**CREATE, due="2026-11-20", description="One\n\nTwo", assign_to_me=True)
    (definition,) = jira.definitions
    marker = "hz-" + digest_of(
        "create-issue",
        drafts(fake_acli)
        .draft_create(**CREATE, due="2026-11-20", description="One\n\nTwo", assign_to_me=True)
        .arguments,
    )
    assert definition["projectKey"] == "KAN"
    assert definition["labels"] == ["harbor", marker]
    assert definition["additionalAttributes"] == {"parent": {"key": "KAN-4"}, "duedate": "2026-11-20"}
    assert [p["content"][0]["text"] for p in definition["description"]["content"]] == ["One", "Two"]
    assert applied.key == "KAN-30"
    assert applied.url == f"{SITE}/browse/KAN-30"
    assert applied.done == ["Created KAN-30.", "Assigned to you."]
    assert jira.written("jira workitem assign")[0][3:6] == ["--key", "KAN-30", "--assignee"]


def test_the_same_approved_create_run_again_finds_the_first_and_creates_nothing(fake_acli):
    jira = Jira(fake_acli, labelled=["KAN-30"])
    applied = drafts(fake_acli).create_issue(**CREATE)
    assert applied.already_done
    assert applied.key == "KAN-30"
    assert jira.writes == []


def test_a_summary_starting_with_dashes_is_text_not_an_option(fake_acli):
    jira = Jira(fake_acli)
    drafts(fake_acli).create_issue(**(CREATE | {"summary": "--yes --json"}))
    assert jira.definitions[0]["summary"] == "--yes --json"
    up = drafts(fake_acli).draft_update("KAN-8", summary="--assignee=@me")
    drafts(fake_acli).update_issue(**up.arguments)
    edit = jira.written("jira workitem edit")[0]
    assert "--summary=--assignee=@me" in edit
    assert "--assignee=@me" not in edit


def test_jira_refusing_a_work_item_type_says_which_it_allows(fake_acli):
    jira = Jira(fake_acli)
    jira.fail["jira workitem create"] = (1, live("errors.json")["bad_type"])
    with pytest.raises(HeinzelError) as caught:
        drafts(fake_acli).create_issue(**(CREATE | {"kind": "Bug"}))
    assert "does not accept that work item type" in str(caught.value)
    assert "Epic, Subtask, Task, Story" in str(caught.value)


def test_a_rate_limit_on_a_write_says_nothing_was_changed(fake_acli):
    jira = Jira(fake_acli)
    jira.fail["jira workitem create"] = (1, "✗ Error: 429 Too Many Requests")
    with pytest.raises(HeinzelError, match=r"rate limit.*nothing was changed"):
        drafts(fake_acli).create_issue(**CREATE)
    assert len(jira.written("jira workitem create")) == 1  # never retried


def test_a_signed_out_acli_on_a_write_names_the_login(fake_acli):
    jira = Jira(fake_acli)
    jira.fail["jira workitem create"] = (1, live("errors.json")["signed_out"])
    with pytest.raises(HeinzelError, match="Log in: acli jira auth login"):
        drafts(fake_acli).create_issue(**CREATE)


def test_a_write_acli_refuses_for_permission_names_the_permission(fake_acli):
    jira = Jira(fake_acli)
    jira.fail["jira workitem comment"] = (1, "✗ Error: 403 Forbidden")
    with pytest.raises(HeinzelError, match="needs the permission Add comments"):
        drafts(fake_acli).comment_issue(**drafts(fake_acli).draft_comment("KAN-8", "Hello").arguments)


def test_a_write_that_times_out_says_it_may_have_happened(fake_acli):
    from heinzel_atlassian._acli import AcliTimeoutError

    Jira(fake_acli)
    original = fake_acli.handler

    def slow(args):
        if args[2] == "create":
            raise AcliTimeoutError(fake_acli.location)
        return original(args)

    fake_acli.handler = slow
    with pytest.raises(HeinzelError, match=r"may or may not have happened"):
        drafts(fake_acli).create_issue(**CREATE)


def test_an_update_draft_shows_before_and_after_and_names_what_it_saw(fake_acli):
    Jira(fake_acli)
    draft = drafts(fake_acli).draft_update("kan-8", summary="Import tide tables", add_labels=["x"], status="Done")
    assert draft.ready
    assert any("-> 'Import tide tables'" in line for line in draft.preview)
    assert "Status: In Progress -> Done" in draft.preview
    assert draft.seen == datetime.fromisoformat(live("view_task.json")["fields"]["updated"])
    assert not drafts(fake_acli).draft_update("KAN-8").ready  # nothing to change


def test_an_update_applies_edit_then_transition_and_nothing_twice(fake_acli):
    jira = Jira(fake_acli)
    draft = drafts(fake_acli).draft_update(
        "KAN-8", summary="Import tides", add_labels=["x"], remove_labels=["y"], status="Done"
    )
    applied = drafts(fake_acli).update_issue(**draft.arguments)
    assert [" ".join(w[:3]) for w in jira.writes] == ["jira workitem edit", "jira workitem transition"]
    edit = jira.written("jira workitem edit")[0]
    assert {"--key=KAN-8", "--summary=Import tides", "--labels=x", "--remove-labels=y"} <= set(edit)
    assert "--status=Done" in jira.written("jira workitem transition")[0]
    assert applied.done == ["Edited summary, labels, remove-labels.", "Moved to Done."]


def test_an_update_of_an_item_that_changed_since_the_draft_changes_nothing(fake_acli):
    jira = Jira(fake_acli)
    draft = drafts(fake_acli).draft_update("KAN-8", summary="Import tides")
    jira.items["KAN-8"]["fields"]["updated"] = "2026-11-01T09:00:00.000+0100"
    with pytest.raises(HeinzelError, match=r"changed at .* after the draft saw it"):
        drafts(fake_acli).update_issue(**draft.arguments)
    assert jira.writes == []


def test_a_failed_transition_after_an_edit_reports_what_was_already_done(fake_acli):
    jira = Jira(fake_acli)
    jira.fail["jira workitem transition"] = (1, "✗ Error: no transition to 'Shipped'")
    draft = drafts(fake_acli).draft_update("KAN-8", summary="Import tides", status="Shipped")
    with pytest.raises(HeinzelError, match=r"Edited summary.*Moving KAN-8 to Shipped failed"):
        drafts(fake_acli).update_issue(**draft.arguments)


def test_a_comment_is_a_draft_until_posted_and_posted_once(fake_acli):
    jira = Jira(fake_acli)
    draft = drafts(fake_acli).draft_comment("KAN-8", "Dunmore fixed in the import.")
    assert draft.ready
    assert jira.writes == []
    applied = drafts(fake_acli).comment_issue(**draft.arguments)
    assert applied.done == ["Comment posted."]
    assert jira.written("jira workitem comment")[0][-3:] == [
        "--key=KAN-8",
        "--body=Dunmore fixed in the import.",
        "--json",
    ]


def test_a_comment_that_got_through_before_a_crash_is_not_posted_again(fake_acli):
    jira = Jira(fake_acli)
    text = "Northern coast CSVs imported; the Dunmore rows still have the wrong offset."
    draft = drafts(fake_acli).draft_comment("KAN-8", text)
    jira.items["KAN-8"]["fields"]["updated"] = "2026-11-01T09:00:00.000+0100"  # the first attempt bumped it
    applied = drafts(fake_acli).comment_issue(**draft.arguments)
    assert applied.already_done
    assert jira.writes == []


def test_a_comment_on_an_item_that_changed_is_refused(fake_acli):
    jira = Jira(fake_acli)
    draft = drafts(fake_acli).draft_comment("KAN-8", "New words")
    jira.items["KAN-8"]["fields"]["updated"] = "2026-11-01T09:00:00.000+0100"
    with pytest.raises(HeinzelError, match="Nothing was changed"):
        drafts(fake_acli).comment_issue(**draft.arguments)
    assert jira.writes == []


def test_an_empty_comment_is_not_ready(fake_acli):
    Jira(fake_acli)
    assert drafts(fake_acli).draft_comment("KAN-8", "  ").problems == ["A comment needs text."]


def test_a_work_item_that_does_not_exist_is_named(fake_acli):
    Jira(fake_acli)
    with pytest.raises(HeinzelError, match="no KAN-99"):
        drafts(fake_acli).draft_comment("KAN-99", "hi")
