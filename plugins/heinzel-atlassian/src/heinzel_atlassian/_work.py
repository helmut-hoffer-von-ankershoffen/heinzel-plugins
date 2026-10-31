"""Reading the person's work: what is assigned to them, how their epics are going, and what deserves attention.

Every read is a real acli call (`search` to find keys, `view` for the fields `search` refuses). Ticket text is data
(`_untrusted`): the reasons something deserves attention come from structured fields only (dates, status category,
assignee id, comment times and authors), never from what a summary or comment says.
"""

import hashlib
import re
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from typing import Any, Literal, cast

from heinzel import HeinzelError
from pydantic import AwareDatetime, BaseModel, Field

from heinzel_atlassian._acli import Acli
from heinzel_atlassian._client import AcliClient, require_site, same_site
from heinzel_atlassian._models import AtlassianSettings
from heinzel_atlassian._untrusted import (
    LABEL_CHARS,
    NOTICE,
    adf_text,
    as_dict,
    as_list,
    is_list,
    is_object,
    one_line,
    word,
)

VIEW = "summary,status,assignee,priority,labels,issuetype,parent,duedate,created,updated,description,comment"
MAX_ITEMS = 50
"""Work items one read returns at most; each costs one `view` run."""
MAX_EPICS = 20
MAX_COMMENTS = 5
"""Newest comments of a work item kept."""
DUE_SOON_DAYS = 2
VIEWERS = 4
_PROJECT = re.compile(r"^[A-Z][A-Z0-9_]{1,254}$")
_KEY = re.compile(r"^[A-Z][A-Z0-9_]{1,254}-[0-9]{1,18}$")
_BLOCKED = frozenset({"blocked", "impediment", "on-hold", "on_hold"})
_STATUS_CATEGORIES = {"new": "todo", "indeterminate": "doing", "done": "done"}

type Category = Literal["todo", "doing", "done", "unknown"]
type ReasonCode = Literal[
    "overdue", "due_soon", "new_comment", "status_changed", "newly_assigned", "assigned_away", "blocked", "new_item"
]


class Comment(BaseModel):
    """One comment. `author` and `text` are untrusted data."""

    id: str
    author: str = Field(description="Display name as Jira shows it. Untrusted data.")
    author_id: str | None = Field(default=None, description="Jira's account id of the author.")
    created_at: AwareDatetime
    text: str = Field(description="Comment as plain text, cut at a bound. Untrusted data.")


class Ticket(BaseModel):
    """A Jira work item. Summary, description, comments, labels, status and names are untrusted data."""

    key: str
    url: str = Field(description="Built on the configured site, never taken from the answer.")
    kind: str = Field(description="Work item type in Jira's words, e.g. Epic, Task, Story. Untrusted data.")
    summary: str = Field(description="Title. Untrusted data.")
    status: str = Field(description="Status in the project's words. Untrusted data.")
    category: Category = Field(
        description="todo, doing or done: Jira's status category, which the project can't rename."
    )
    assignee: str | None = Field(default=None, description="Display name; none if unassigned. Untrusted data.")
    assignee_id: str | None = Field(default=None, description="Jira's account id of the assignee.")
    priority: str | None = None
    labels: list[str] = Field(default_factory=list[str], description="Untrusted data.")
    due: date | None = None
    created_at: AwareDatetime | None = None
    updated_at: AwareDatetime
    parent: str | None = Field(default=None, description="Key of the epic or parent work item.")
    parent_summary: str | None = Field(default=None, description="Its title. Untrusted data.")
    description: str | None = Field(default=None, description="As plain text, cut at a bound. Untrusted data.")
    comments: list[Comment] = Field(default_factory=list[Comment], description="The newest few, oldest first.")
    comment_total: int = 0


class Assigned(BaseModel):
    """Open work assigned to the person."""

    notice: str = Field(default=NOTICE)
    me: str | None = Field(default=None, description="Jira's account id of the person, learned from their work.")
    items: list[Ticket]
    more: bool = Field(default=False, description="True if more matched than were read; ask for a project.")


class EpicProgress(BaseModel):
    """An epic and how its children stand."""

    epic: Ticket
    total: int
    done: int
    doing: int
    todo: int
    overdue: int = Field(description="Open children whose due date has passed.")
    percent_done: int


class Epics(BaseModel):
    """Epics with progress."""

    notice: str = Field(default=NOTICE)
    epics: list[EpicProgress]


class Snapshot(BaseModel):
    """What was seen of a work item, to notice what changed since: hand it back on the next read."""

    key: str
    status: str
    category: Category
    assignee_id: str | None
    updated_at: AwareDatetime


class Reason(BaseModel):
    """Why something deserves attention, from structured fields only."""

    code: ReasonCode
    detail: str = Field(description="One sentence built from dates, ids and status words, never from free text.")


class Attention(BaseModel):
    """A work item that deserves a look, with the reasons, most pressing first."""

    ticket: Ticket
    reasons: list[Reason]
    urgent: bool
    notice_key: str = Field(
        description="Stable for this work item, these reasons and this update, so a channel sends the notice once."
    )
    title: str = Field(description="One line for a notice: the key and the reasons. No ticket text.")
    body: str = Field(description="The reasons' details in plain text, at most 500 characters. No ticket text.")


class Watch(BaseModel):
    """What changed in the person's work since a time."""

    notice: str = Field(default=NOTICE)
    since: AwareDatetime
    checked: int = Field(description="Work items looked at.")
    attention: list[Attention]
    snapshots: list[Snapshot] = Field(description="Pass these as `previous` next time to see status changes.")


def project_key(text: str) -> str:
    """A Jira project key, upper-cased and checked, so nothing unchecked reaches JQL.

    Raises:
        HeinzelError: If it is not a key.
    """
    key = text.strip().upper()
    if not _PROJECT.fullmatch(key):
        msg = f"{text!r} is not a Jira project key; write the key, e.g. KAN: a letter, then letters, digits or _."
        raise HeinzelError(msg)
    return key


def issue_key(text: str) -> str:
    """A work item key such as `KAN-12`, upper-cased and checked.

    Raises:
        HeinzelError: If it is not one.
    """
    key = text.strip().upper()
    if not _KEY.fullmatch(key):
        msg = f"{text!r} is not a Jira work item key such as KAN-12."
        raise HeinzelError(msg)
    return key


def _instant(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo is not None else None


def _day(value: object) -> date | None:
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _text_of(value: object, key: str) -> str | None:
    found = cast("dict[str, Any]", value).get(key) if isinstance(value, dict) else None
    return one_line(found) or None if isinstance(found, str) else None


def _category(status: object) -> Category:
    inner = cast("dict[str, Any]", status).get("statusCategory") if isinstance(status, dict) else None
    key = cast("dict[str, Any]", inner).get("key") if isinstance(inner, dict) else None
    return cast("Category", _STATUS_CATEGORIES.get(key, "unknown")) if isinstance(key, str) else "unknown"


def _comments(field: object) -> tuple[list[Comment], int]:
    if not is_object(field):
        return [], 0
    raw, total = as_list(as_dict(field).get("comments")), as_dict(field).get("total")
    found: list[Comment] = []
    for item in raw:
        entry = as_dict(item)
        created, ident = _instant(entry.get("created")), entry.get("id")
        if created is None or not isinstance(ident, str):
            continue
        author = as_dict(entry.get("author"))
        author_id = author.get("accountId")
        found.append(
            Comment(
                id=one_line(ident, 40),
                author=_text_of(author, "displayName") or "someone",
                author_id=author_id if isinstance(author_id, str) else None,
                created_at=created,
                text=adf_text(entry.get("body")),
            )
        )
    found.sort(key=lambda c: c.created_at)
    return found[-MAX_COMMENTS:], total if isinstance(total, int) else len(found)


def ticket_from(site: str, item: dict[str, Any]) -> Ticket:
    """One `acli jira workitem view --json` answer as a `Ticket`, checked field by field.

    Raises:
        HeinzelError: If the key, summary, status or update time is missing or malformed.
    """
    key, fields = item.get("key"), item.get("fields")
    if not (isinstance(key, str) and _KEY.fullmatch(key) and isinstance(fields, dict)):
        msg = "acli's view answer lacks the key or fields of a Jira work item; is acli up to date?"
        raise HeinzelError(msg)
    fields = cast("dict[str, Any]", fields)
    same_site("Jira", site, item.get("self"), "/rest")
    summary, updated = fields.get("summary"), _instant(fields.get("updated"))
    status = _text_of(fields.get("status"), "name")
    if not isinstance(summary, str) or updated is None or status is None:
        msg = f"acli's view answer for {key} lacks its summary, status or update time; is acli up to date?"
        raise HeinzelError(msg)
    assignee, parent = as_dict(fields.get("assignee")), as_dict(fields.get("parent"))
    parent_key, parent_fields = parent.get("key"), parent.get("fields")
    labels = fields.get("labels")
    comments, total = _comments(fields.get("comment"))
    description = adf_text(fields.get("description")) if fields.get("description") else ""
    assignee_id = assignee.get("accountId")
    return Ticket(
        key=key,
        url=f"{site}/browse/{key}",
        kind=_text_of(fields.get("issuetype"), "name") or "unknown",
        summary=one_line(summary),
        status=status,
        category=_category(fields.get("status")),
        assignee=_text_of(assignee, "displayName"),
        assignee_id=assignee_id if isinstance(assignee_id, str) else None,
        priority=_text_of(fields.get("priority"), "name"),
        labels=[one_line(x, LABEL_CHARS) for x in cast("list[object]", labels) if isinstance(x, str) and x.strip()]
        if isinstance(labels, list)
        else [],
        due=_day(fields.get("duedate")),
        created_at=_instant(fields.get("created")),
        updated_at=updated,
        parent=parent_key if isinstance(parent_key, str) and _KEY.fullmatch(parent_key) else None,
        parent_summary=_text_of(parent_fields, "summary"),
        description=description or None,
        comments=comments,
        comment_total=total,
    )


def _listing(document: object) -> list[dict[str, Any]]:
    """The work items in one search document: a list of them, or an object holding them under `issues`.

    Raises:
        HeinzelError: If it is neither.
    """
    items: object = as_dict(document).get("issues") if is_object(document) else document
    if not is_list(items):
        msg = "acli's search answer is not a list of Jira work items; is acli up to date?"
        raise HeinzelError(msg)
    return [as_dict(item) for item in as_list(items)]


def _keys(documents: Sequence[Any]) -> list[str]:
    keys = [
        k
        for document in documents
        for item in _listing(document)
        if isinstance(k := item.get("key"), str) and _KEY.fullmatch(k)
    ]
    return list(dict.fromkeys(keys))


def _closed(statuses: dict[str, Category]) -> int:
    return sum(1 for c in statuses.values() if c == "done")


class JiraWork:
    """Reads a person's work from Jira through acli: assigned items, epics with progress, what needs attention."""

    def __init__(self, settings: AtlassianSettings, acli: Acli) -> None:
        """Build the reader; the kernel injects the settings and acli."""
        self._settings = settings
        self._client = AcliClient(acli, settings.timeout)

    def _search(self, jql: str, subject: str, fields: str = "key,summary,status") -> list[Any]:
        return self._client.json(
            "Jira", ["jira", "workitem", "search", "--jql", jql, "--fields", fields, "--paginate", "--json"], subject
        )

    def _view(self, site: str, keys: Sequence[str]) -> list[Ticket]:
        def one(key: str) -> Ticket:
            answer = self._client.json("Jira", ["jira", "workitem", "view", key, "--fields", VIEW, "--json"], key)
            if len(answer) != 1 or not isinstance(answer[0], dict):
                msg = f"acli's view answer for {key} is not a Jira work item; is acli up to date?"
                raise HeinzelError(msg)
            return ticket_from(site, cast("dict[str, Any]", answer[0]))

        with ThreadPoolExecutor(max_workers=VIEWERS) as pool:
            return list(pool.map(one, keys))

    def assigned(self, project: str | None = None, limit: int = MAX_ITEMS) -> Assigned:
        """Open work items assigned to the person acli is signed in as, most pressing first.

        Raises:
            HeinzelError: If the project is malformed, the site is not set, or acli fails.
        """
        site = require_site(self._settings)
        scope = f" AND project = {_quoted(project_key(project))}" if project else ""
        jql = f"assignee = currentUser() AND statusCategory != Done{scope} ORDER BY duedate ASC, key ASC"
        keys = _keys(self._search(jql, "your assigned work"))
        bound = max(1, min(limit, MAX_ITEMS))
        tickets = self._view(site, keys[:bound])
        mine = next((t.assignee_id for t in tickets if t.assignee_id), None)
        return Assigned(me=mine, items=tickets, more=len(keys) > bound)

    def epics(self, project: str | None = None, limit: int = MAX_EPICS) -> Epics:
        """Epics not done, each with how many children are done, doing, to do and overdue.

        Raises:
            HeinzelError: If the project is malformed, the site is not set, or acli fails.
        """
        site = require_site(self._settings)
        scope = f" AND project = {_quoted(project_key(project))}" if project else ""
        keys = _keys(self._search(f"issuetype = Epic AND statusCategory != Done{scope} ORDER BY key ASC", "your epics"))
        epics = self._view(site, keys[: max(1, min(limit, MAX_EPICS))])
        return Epics(epics=[self._progress(epic) for epic in epics])

    def _progress(self, epic: Ticket) -> EpicProgress:
        children = self._client.json(
            "Jira",
            [
                "jira",
                "workitem",
                "search",
                "--jql",
                f"parent = {epic.key}",
                "--fields",
                "key,summary,status",
                "--paginate",
                "--json",
            ],
            f"the children of {epic.key}",
        )
        states: dict[str, Category] = {}
        for document in children:
            for child in _listing(document):
                name = child.get("key")
                if isinstance(name, str):
                    states[name] = _category(as_dict(child.get("fields")).get("status"))
        overdue = 0
        if len(states) > _closed(states):
            late = f"parent = {epic.key} AND statusCategory != Done AND duedate < startOfDay()"
            overdue = len(_keys(self._search(late, f"the overdue children of {epic.key}", "key,summary")))
        total = len(states)
        done = _closed(states)
        doing = sum(1 for c in states.values() if c == "doing")
        return EpicProgress(
            epic=epic,
            total=total,
            done=done,
            doing=doing,
            todo=total - done - doing,
            overdue=overdue,
            percent_done=round(100 * done / total) if total else 0,
        )

    def watch(
        self,
        since: datetime,
        previous: Sequence[Snapshot] = (),
        project: str | None = None,
        now: datetime | None = None,
    ) -> Watch:
        """What in the person's own work (assigned to them) changed since `since` and deserves a look.

        Raises:
            HeinzelError: If the project is malformed, `since` has no time zone, the site is not set, or acli fails.
        """
        if since.tzinfo is None:
            msg = "since needs a time zone, e.g. 2026-10-31T09:00:00+01:00"
            raise HeinzelError(msg)
        clock = (now or datetime.now(UTC)).astimezone(UTC)
        site = require_site(self._settings)
        scope = f" AND project = {_quoted(project_key(project))}" if project else ""
        minute = int(since.astimezone(UTC).timestamp() // 60 * 60_000)
        mine_jql = (
            f"assignee = currentUser() AND (statusCategory != Done OR updated >= {minute}){scope} ORDER BY updated DESC"
        )
        mine_keys = _keys(self._search(mine_jql, "your recent work"))[:MAX_ITEMS]
        away_jql = f"assignee WAS currentUser() AND assignee != currentUser() AND updated >= {minute}{scope}"
        away_keys = [k for k in _keys(self._search(away_jql, "work moved away from you")) if k not in mine_keys]
        tickets = self._view(site, [*mine_keys, *away_keys][:MAX_ITEMS])
        mine = next((t.assignee_id for t in tickets if t.key in mine_keys and t.assignee_id), None)
        before = {s.key: s for s in previous}
        found = [a for t in tickets if (a := attention(t, since.astimezone(UTC), clock, mine, before.get(t.key)))]
        found.sort(key=lambda a: (not a.urgent, -len(a.reasons), a.ticket.key))
        snaps = [
            Snapshot(
                key=t.key, status=t.status, category=t.category, assignee_id=t.assignee_id, updated_at=t.updated_at
            )
            for t in tickets
        ]
        return Watch(since=since, checked=len(tickets), attention=found, snapshots=snaps)


def _quoted(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _due_reasons(ticket: Ticket, today: date) -> list[Reason]:
    if ticket.category == "done" or ticket.due is None:
        return []
    days = (ticket.due - today).days
    if days < 0:
        return [Reason(code="overdue", detail=f"Due {ticket.due.isoformat()}, {-days} day(s) ago.")]
    if days <= DUE_SOON_DAYS:
        return [Reason(code="due_soon", detail=f"Due {ticket.due.isoformat()}, in {days} day(s).")]
    return []


def _assignment_reasons(ticket: Ticket, me: str | None, before: Snapshot | None) -> list[Reason]:
    if before is None or me is None:
        return []
    if before.assignee_id != me and ticket.assignee_id == me:
        return [Reason(code="newly_assigned", detail="Assigned to you since the last look.")]
    if before.assignee_id == me and ticket.assignee_id != me:
        return [Reason(code="assigned_away", detail="No longer assigned to you.")]
    return []


def attention(
    ticket: Ticket, since: datetime, now: datetime, me: str | None, before: Snapshot | None
) -> Attention | None:
    """The reasons `ticket` deserves a look since `since`, or None. Pure: free text is never consulted."""
    reasons = _due_reasons(ticket, now.date()) + _assignment_reasons(ticket, me, before)
    others = [c for c in ticket.comments if c.created_at >= since and (me is None or c.author_id != me)]
    if others:
        people = len({c.author_id or c.author for c in others})
        reasons.append(Reason(code="new_comment", detail=f"{len(others)} new comment(s) by {people} other person(s)."))
    if before is not None and before.status != ticket.status:
        reasons.append(
            Reason(code="status_changed", detail=f"Moved from {word(before.status)} to {word(ticket.status)}.")
        )
    if before is None and ticket.created_at is not None and ticket.created_at >= since and ticket.assignee_id == me:
        created = ticket.created_at.date().isoformat()
        reasons.append(Reason(code="new_item", detail=f"Created {created} and assigned to you."))
    if ticket.category != "done" and any(label.lower() in _BLOCKED for label in ticket.labels):
        reasons.append(Reason(code="blocked", detail="Carries a blocked label."))
    if not reasons:
        return None
    pressing = {"overdue", "newly_assigned"}
    urgent = any(r.code in pressing for r in reasons) or (
        any(r.code == "due_soon" for r in reasons) and ticket.category == "todo"
    )
    codes = sorted({r.code for r in reasons})
    stable = hashlib.sha256(f"{ticket.key}|{','.join(codes)}|{ticket.updated_at.isoformat()}".encode()).hexdigest()
    return Attention(
        ticket=ticket,
        reasons=reasons,
        urgent=urgent,
        notice_key=f"jira-{stable[:32]}",
        title=f"{ticket.key}: " + ", ".join(c.replace("_", " ") for c in codes),
        body=" ".join(r.detail for r in reasons)[:500],
    )


__all__ = [
    "Assigned",
    "Attention",
    "Comment",
    "EpicProgress",
    "Epics",
    "JiraWork",
    "Reason",
    "Snapshot",
    "Ticket",
    "Watch",
    "attention",
    "issue_key",
    "project_key",
    "ticket_from",
]
