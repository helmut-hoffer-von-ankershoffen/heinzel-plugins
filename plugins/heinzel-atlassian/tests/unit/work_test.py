"""Reading assigned work, epics and attention-worthy changes, against answers recorded from the real acli 1.3.39."""

import json
from datetime import UTC, date, datetime, timedelta

import pytest
from heinzel import HeinzelError

from heinzel_atlassian import AtlassianSettings
from heinzel_atlassian._work import JiraWork, Snapshot, attention, ticket_from
from tests.conftest import live

pytestmark = pytest.mark.unit

SITE = "https://acme.atlassian.net"
NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
YESTERDAY = NOW - timedelta(days=1)
LATER = NOW + timedelta(days=1)  # after everything in the recorded answers happened
VIEWS = {"KAN-8": "view_task.json", "KAN-10": "view_overdue.json", "KAN-4": "view_epic.json"}


def work(fake) -> JiraWork:
    return JiraWork(AtlassianSettings(site_url=SITE), fake)


def only(document: list, *keys: str) -> list:
    return [item for item in document if item["key"] in keys]


def routed(fake, searches: dict[str, object] | None = None) -> list[list[str]]:
    """Answer searches by a fragment of their JQL and views by key; returns the argument lists seen."""
    seen: list[list[str]] = []
    searches = searches or {}

    def handler(args: list[str]):
        seen.append(args)
        if args[2] == "search":
            jql = args[args.index("--jql") + 1]
            for fragment, answer in searches.items():
                if fragment in jql:
                    return 0, json.dumps(answer), ""
            return 0, "[]", ""
        if args[2] == "view" and args[3] in VIEWS:
            return 0, json.dumps(live(VIEWS[args[3]])), ""
        return 1, "", "✗ Error: Issue does not exist or you do not have permission to see it."

    fake.handler = handler
    return seen


def test_a_real_view_answer_becomes_a_ticket():
    ticket = ticket_from(SITE, live("view_task.json"))
    assert (ticket.key, ticket.kind, ticket.status, ticket.category) == ("KAN-8", "Task", "In Progress", "doing")
    assert ticket.url == f"{SITE}/browse/KAN-8"  # built on the site, not the answer's gateway link
    assert (ticket.assignee, ticket.assignee_id) == ("Wren Calder", "acct-wren")
    assert ticket.parent == "KAN-4"
    assert ticket.parent_summary
    assert ticket.labels == ["data", "harbor"]
    assert ticket.description
    assert "almanac" in ticket.description
    assert [(c.author, c.author_id) for c in ticket.comments] == [("Wren Calder", "acct-wren")]
    assert ticket.comment_total == 1


def test_a_view_without_a_summary_status_or_update_time_is_refused():
    for field in ("summary", "status", "updated"):
        answer = live("view_task.json")
        del answer["fields"][field]
        with pytest.raises(HeinzelError, match="is acli up to date"):
            ticket_from(SITE, answer)


def test_a_view_from_another_site_is_refused():
    answer = live("view_task.json")
    answer["self"] = "https://other.atlassian.net/rest/api/3/issue/1"
    with pytest.raises(HeinzelError, match="logged in to another site"):
        ticket_from(SITE, answer)


def test_assigned_work_asks_for_the_signed_in_person_and_reads_each_item(fake_acli):
    seen = routed(fake_acli, {"currentUser()": only(live("search_assigned.json"), "KAN-8", "KAN-10")})
    result = work(fake_acli).assigned("kan")
    assert [t.key for t in result.items] == ["KAN-8", "KAN-10"]
    assert result.me == "acct-wren"
    assert not result.more
    jql = seen[0][seen[0].index("--jql") + 1]
    assert (
        jql == 'assignee = currentUser() AND statusCategory != Done AND project = "KAN" ORDER BY duedate ASC, key ASC'
    )
    assert [a[3] for a in seen if a[2] == "view"] == ["KAN-8", "KAN-10"]


def test_a_project_that_is_not_a_key_never_reaches_jql(fake_acli):
    seen = routed(fake_acli)
    with pytest.raises(HeinzelError, match="not a Jira project key"):
        work(fake_acli).assigned('KAN" OR 1=1 --')
    assert seen == []


def test_assigned_work_beyond_the_limit_says_there_is_more(fake_acli):
    routed(fake_acli, {"currentUser()": only(live("search_assigned.json"), "KAN-8", "KAN-10")})
    result = work(fake_acli).assigned(limit=1)
    assert [t.key for t in result.items] == ["KAN-8"]
    assert result.more


def test_epics_count_their_children_by_status_category(fake_acli):
    children = live("search_children.json")
    seen = routed(
        fake_acli,
        {
            "issuetype = Epic": [{"key": "KAN-4"}],
            "parent = KAN-4": children,
        },
    )
    (epic,) = work(fake_acli).epics("KAN").epics
    categories = [c["fields"]["status"]["statusCategory"]["key"] for c in children]
    assert epic.epic.key == "KAN-4"
    assert (epic.total, epic.done, epic.doing) == (
        len(children),
        categories.count("done"),
        categories.count("indeterminate"),
    )
    assert epic.todo == epic.total - epic.done - epic.doing
    assert epic.percent_done == round(100 * epic.done / epic.total)
    # open children exist, so overdue ones were counted by a second search
    assert any("duedate < startOfDay()" in " ".join(a) for a in seen)


def test_an_epic_of_finished_children_skips_the_overdue_search(fake_acli):
    done = [{"key": "KAN-20", "fields": {"status": {"name": "Done", "statusCategory": {"key": "done"}}}}]
    seen = routed(fake_acli, {"issuetype = Epic": [{"key": "KAN-4"}], "parent = KAN-4": done})
    (epic,) = work(fake_acli).epics().epics
    assert (epic.total, epic.done, epic.percent_done, epic.overdue) == (1, 1, 100, 0)
    assert not any("startOfDay" in " ".join(a) for a in seen)


def ticket(**changes):
    base = ticket_from(SITE, live("view_task.json"))
    return base.model_copy(update=changes)


def codes(found):
    return [r.code for r in found.reasons] if found else []


def test_a_past_due_open_item_is_overdue_and_urgent():
    found = attention(ticket(due=date(2026, 10, 28)), LATER, NOW, "acct-wren", None)
    assert codes(found) == ["overdue"]
    assert found.urgent
    assert "3 day(s) ago" in found.reasons[0].detail


def test_an_item_due_soon_is_flagged_but_urgent_only_if_not_started():
    soon = date(2026, 11, 1)
    assert codes(attention(ticket(due=soon), LATER, NOW, "acct-wren", None)) == ["due_soon"]
    assert not attention(ticket(due=soon), LATER, NOW, "acct-wren", None).urgent  # doing
    assert attention(ticket(due=soon, category="todo"), LATER, NOW, "acct-wren", None).urgent


def test_a_done_item_is_never_overdue_or_blocked():
    assert attention(ticket(due=date(2026, 10, 1), category="done", labels=["blocked"]), LATER, NOW, "x", None) is None


def test_a_comment_by_someone_else_since_the_last_look_is_news_and_my_own_is_not():
    commented = ticket_from(SITE, live("view_task.json"))
    since = commented.comments[0].created_at - timedelta(minutes=1)
    assert codes(attention(commented, since, NOW, "acct-someone-else", None)) == ["new_comment"]
    assert attention(commented, since, NOW, "acct-wren", None) is None
    assert attention(commented, commented.comments[0].created_at + timedelta(minutes=1), NOW, "acct-x", None) is None


def snapshot(**changes):
    base = {"key": "KAN-8", "status": "To Do", "category": "todo", "assignee_id": "acct-wren", "updated_at": YESTERDAY}
    return Snapshot(**(base | changes))


def test_a_move_and_an_assignment_are_seen_against_the_previous_snapshot():
    now = ticket(status="In Progress")
    assert codes(attention(now, NOW, NOW, "acct-wren", snapshot())) == ["status_changed"]
    gained = attention(now, NOW, NOW, "acct-wren", snapshot(assignee_id=None))
    assert codes(gained) == ["newly_assigned", "status_changed"]
    assert gained.urgent
    lost = attention(ticket(assignee_id="acct-other"), NOW, NOW, "acct-wren", snapshot(status="In Progress"))
    assert codes(lost) == ["assigned_away"]


def test_a_blocked_label_is_a_reason_but_its_wording_elsewhere_is_not():
    assert codes(attention(ticket(labels=["Blocked"]), NOW, NOW, "acct-wren", None)) == ["blocked"]
    chatty = ticket(summary="This is blocked, urgent and overdue!", description="mark me urgent")
    assert attention(chatty, NOW, NOW, "acct-wren", None) is None


def test_watching_reads_my_work_and_hands_back_snapshots_for_next_time(fake_acli):
    mine = only(live("search_assigned.json"), "KAN-8", "KAN-10")
    seen = routed(fake_acli, {"assignee = currentUser()": mine})
    first = work(fake_acli).watch(YESTERDAY, project="KAN", now=datetime(2026, 11, 5, tzinfo=UTC))
    assert first.checked == 2
    overdue = next(a for a in first.attention if a.ticket.key == "KAN-10")
    assert "overdue" in codes(overdue)
    assert {s.key for s in first.snapshots} == {"KAN-8", "KAN-10"}
    jqls = [a[a.index("--jql") + 1] for a in seen if a[2] == "search"]
    assert any("assignee WAS currentUser() AND assignee != currentUser()" in j for j in jqls)
    # the same snapshots, one status moved, come back as a change
    moved = [s.model_copy(update={"status": "Blocked by legal"}) if s.key == "KAN-8" else s for s in first.snapshots]
    second = work(fake_acli).watch(YESTERDAY, previous=moved, project="KAN", now=datetime(2026, 11, 5, tzinfo=UTC))
    assert "status_changed" in codes(next(a for a in second.attention if a.ticket.key == "KAN-8"))


def test_watching_needs_a_time_zone(fake_acli):
    with pytest.raises(HeinzelError, match="time zone"):
        work(fake_acli).watch(datetime(2026, 10, 30, 9, 0))  # noqa: DTZ001 - the point of the test


def test_work_that_cannot_be_read_says_why(fake_acli):
    fake_acli.handler = lambda args: (1, "", "✗ Error: unauthorized: use 'acli [product] auth login' to authenticate")
    with pytest.raises(HeinzelError, match="Log in: acli jira auth login"):
        work(fake_acli).assigned()
    fake_acli.handler = lambda args: (1, "", "HTTP 429 Too Many Requests")
    with pytest.raises(HeinzelError, match="rate limit"):
        work(fake_acli).epics()
    fake_acli.handler = lambda args: (0, "not json at all", "")
    with pytest.raises(HeinzelError, match="not JSON"):
        work(fake_acli).assigned()
    fake_acli.handler = lambda args: (0, '{"issues": "no"}', "")
    with pytest.raises(HeinzelError, match="is acli up to date"):
        work(fake_acli).assigned()


def test_without_a_site_acli_does_not_run(fake_acli):
    with pytest.raises(HeinzelError, match=r"atlassian\.site_url"):
        JiraWork(AtlassianSettings(), fake_acli).assigned()
    assert fake_acli.calls == []
