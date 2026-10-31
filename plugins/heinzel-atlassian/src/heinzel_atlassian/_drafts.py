"""Drafts of Jira changes, and the write operations that carry one out after a person approved it.

A draft is computed without changing anything (P2: drafts over surprises, P3: a ticket comment is visible to others,
so it is proposed, not posted). It carries the exact arguments of the write operation that applies it, and what a
person will see changed. The write operations are `read_only=False` operations: a chat holds them as proposals
until the person confirms exactly those arguments (the `ActionGate`), and the CLI shows what they will do. Nothing
here approves anything; a model's call is not an approval, and text in a ticket never reaches a command, a query or
an approval (`_untrusted`).

Writes are never retried. A create labels the work item `hz-<digest>`, so doing the same approved create twice
(a crash between acli's answer and the journal, T2) finds the first and creates nothing. An update or a comment
carries the time the draft saw the work item and refuses if it changed since: the person approved a state, not a
guess.
"""

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal, cast

from heinzel import HeinzelError
from pydantic import AwareDatetime, BaseModel, Field, JsonValue, TypeAdapter

from heinzel_atlassian._acli import Acli
from heinzel_atlassian._client import AcliClient, require_site
from heinzel_atlassian._models import AtlassianSettings
from heinzel_atlassian._untrusted import NOTICE, as_dict, as_list, is_object
from heinzel_atlassian._work import Ticket, issue_key, project_key, ticket_from

LABEL_PREFIX = "hz-"
MAX_TEXT = 30_000
SUMMARY_CHARS = 255
_TYPE = re.compile(r"^[A-Za-z][A-Za-z -]{0,59}$")
_LABEL = re.compile(r"^[A-Za-z0-9_.:-]{1,255}$")
_STATUS = re.compile(r"^[^\x00-\x1f]{1,60}$")
type Action = Literal["create-issue", "update-issue", "comment-issue"]
VIEW = "summary,status,assignee,priority,labels,issuetype,parent,duedate,created,updated,description,comment"


class Draft(BaseModel):
    """What a change would do, with nothing done yet."""

    notice: str = Field(default=NOTICE)
    action: Action = Field(description="The write operation that applies it, run with `arguments`.")
    target: str = Field(description="The work item key, or the project a new one goes to.")
    arguments: dict[str, JsonValue] = Field(description="Exactly the arguments of that operation.")
    preview: list[str] = Field(description="What a person will see changed, one line each.")
    problems: list[str] = Field(description="What is missing or wrong; the draft cannot be applied until none is left.")
    ready: bool
    digest: str = Field(description="Names this exact draft; a created work item carries it as a label.")
    seen: AwareDatetime | None = Field(
        default=None, description="When the work item was last updated, as the draft saw it."
    )


class Applied(BaseModel):
    """What an approved change did."""

    action: Action
    key: str
    url: str
    done: list[str] = Field(description="Changes made, one line each.")
    already_done: bool = Field(default=False, description="True if the same approved change was found already made.")


def digest_of(action: str, arguments: dict[str, JsonValue]) -> str:
    """A short name of this exact change."""
    encoded = json.dumps([action, arguments], sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:12]


def _text(
    value: str | None, name: str, problems: list[str], *, limit: int = MAX_TEXT, single_line: bool = False
) -> str:
    text = (value or "").replace("\r\n", "\n").strip()
    if "\x00" in text:
        problems.append(f"{name} has a NUL character.")
    if single_line and "\n" in text:
        problems.append(f"{name} must be one line.")
    if len(text) > limit:
        problems.append(f"{name} is {len(text)} characters; Jira takes at most {limit}.")
    return text


def _labels(labels: Sequence[str], problems: list[str]) -> list[str]:
    cleaned = [x.strip() for x in labels if x.strip()]
    problems.extend(
        f"Label {label!r} may only hold letters, digits and _ . : - (Jira labels have no spaces)."
        for label in cleaned
        if not _LABEL.fullmatch(label)
    )
    return list(dict.fromkeys(cleaned))


def _adf(text: str) -> dict[str, Any]:
    paragraphs = [p for p in text.split("\n\n") if p.strip()] or [""]
    content: list[dict[str, Any]] = [
        {"type": "paragraph", "content": [{"type": "text", "text": p}] if p else []} for p in paragraphs
    ]
    return {"type": "doc", "version": 1, "content": content}


def _day(value: str | None, problems: list[str]) -> str | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        problems.append(f"Due date {value!r} is not a date such as 2026-11-05.")
        return None


def _draft(  # noqa: PLR0913, PLR0917 - what a draft is made of
    action: Action,
    target: str,
    arguments: dict[str, JsonValue],
    preview: list[str],
    problems: list[str],
    seen: datetime | None = None,
) -> Draft:
    return Draft(
        action=action,
        target=target,
        arguments=arguments,
        preview=preview,
        problems=problems,
        ready=not problems,
        digest=digest_of(action, arguments),
        seen=seen,
    )


class JiraDrafts:
    """Drafts and applies Jira changes through acli, as the person acli is signed in as."""

    def __init__(self, settings: AtlassianSettings, acli: Acli) -> None:
        """Build the drafter; the kernel injects the settings and acli."""
        self._settings = settings
        self._client = AcliClient(acli, settings.timeout)

    def _target(self, key: str) -> Ticket:
        site = require_site(self._settings)
        answer = self._client.json("Jira", ["jira", "workitem", "view", key, "--fields", VIEW, "--json"], key)
        if len(answer) != 1 or not isinstance(answer[0], dict):
            msg = f"acli's view answer for {key} is not a Jira work item; is acli up to date?"
            raise HeinzelError(msg)
        return ticket_from(site, cast("dict[str, Any]", answer[0]))

    # ---- drafts: they read, they change nothing ----

    def draft_create(  # noqa: PLR0913, PLR0917 - the fields of a new work item
        self,
        project: str,
        kind: str,
        summary: str,
        description: str = "",
        parent: str | None = None,
        labels: Sequence[str] = (),
        assign_to_me: bool = False,
        due: str | None = None,
    ) -> Draft:
        """A new work item, checked for what Jira would refuse; nothing is created.

        Raises:
            HeinzelError: If acli fails while the parent is looked up.
        """
        problems: list[str] = []
        key = _project_or(project, problems)
        kind = kind.strip()
        if not _TYPE.fullmatch(kind):
            problems.append("A work item type is needed, e.g. Task, Story or Epic.")
        text = _text(summary, "The summary", problems, limit=SUMMARY_CHARS, single_line=True)
        if not text:
            problems.append("A summary is needed.")
        body = _text(description, "The description", problems)
        names = _labels(labels, problems)
        day = _day(due, problems)
        parent_key = _parent(parent, kind, problems)
        shown: list[str] = []
        if parent_key and not problems:
            found = self._target(parent_key)
            shown.append(f"Parent: {found.key} ({found.kind}) {found.summary}")
        arguments: dict[str, JsonValue] = {
            "project": key or project,
            "kind": kind,
            "summary": text,
            "description": body,
            "parent": parent_key,
            "labels": cast("list[JsonValue]", names),
            "assign_to_me": assign_to_me,
            "due": day,
        }
        preview = [f"Create a {kind or '?'} in {key or '?'}: {text or '(no summary)'}", *shown]
        if body:
            preview.append(f"Description: {len(body)} characters")
        if names:
            preview.append("Labels: " + ", ".join(names))
        if day:
            preview.append(f"Due: {day}")
        if assign_to_me:
            preview.append("Assigned to you")
        return _draft("create-issue", key or project, arguments, preview, problems)

    def draft_update(  # noqa: PLR0913, PLR0917 - the changes one update can make
        self,
        key: str,
        summary: str | None = None,
        description: str | None = None,
        add_labels: Sequence[str] = (),
        remove_labels: Sequence[str] = (),
        assign_to_me: bool = False,
        status: str | None = None,
    ) -> Draft:
        """A change to an existing work item, shown against what it is now; nothing is changed.

        Raises:
            HeinzelError: If the key is malformed or acli fails reading the work item.
        """
        target = self._target(issue_key(key))
        return self._update_draft(target, summary, description, (add_labels, remove_labels), assign_to_me, status)

    @staticmethod
    def _update_draft(  # noqa: PLR0913, PLR0917 - the changes one update can make, and the work item they are against
        target: Ticket,
        summary: str | None,
        description: str | None,
        labels: tuple[Sequence[str], Sequence[str]],
        assign_to_me: bool,
        status: str | None,
    ) -> Draft:
        problems: list[str] = []
        arguments: dict[str, JsonValue] = {"key": target.key, "seen": target.updated_at.isoformat()}
        preview = [f"Change {target.key}: {target.summary}"]
        if summary is not None:
            text = _text(summary, "The summary", problems, limit=SUMMARY_CHARS, single_line=True)
            if not text:
                problems.append("The summary cannot be empty.")
            arguments["summary"] = text
            preview.append(f"Summary: {target.summary!r} -> {text!r}")
        if description is not None:
            body = _text(description, "The description", problems)
            arguments["description"] = body
            preview.append(f"Description: {len(target.description or '')} -> {len(body)} characters")
        add, remove = _labels(labels[0], problems), _labels(labels[1], problems)
        if add:
            arguments["add_labels"] = cast("list[JsonValue]", add)
            preview.append("Add labels: " + ", ".join(add))
        if remove:
            arguments["remove_labels"] = cast("list[JsonValue]", remove)
            preview.append("Remove labels: " + ", ".join(remove))
        if assign_to_me:
            arguments["assign_to_me"] = True
            preview.append(f"Assignee: {target.assignee or 'nobody'} -> you")
        if status is not None:
            if not _STATUS.fullmatch(status.strip()):
                problems.append("A status name is needed, e.g. In Progress.")
            arguments["status"] = status.strip()
            preview.append(f"Status: {target.status} -> {status.strip()}")
        if len(arguments) == 2:  # noqa: PLR2004 - only key and seen
            problems.append("Nothing to change: give a summary, description, labels, assignee or status.")
        return _draft("update-issue", target.key, arguments, preview, problems, target.updated_at)

    def draft_comment(self, key: str, text: str) -> Draft:
        """A comment on a work item. Others can read it once posted, so it is proposed, never posted, here.

        Raises:
            HeinzelError: If the key is malformed or acli fails reading the work item.
        """
        return self._comment_draft(self._target(issue_key(key)), text)

    @staticmethod
    def _comment_draft(target: Ticket, text: str) -> Draft:
        problems: list[str] = []
        body = _text(text, "The comment", problems)
        if not body:
            problems.append("A comment needs text.")
        arguments: dict[str, JsonValue] = {"key": target.key, "text": body, "seen": target.updated_at.isoformat()}
        preview = [f"Comment on {target.key}: {target.summary}", f"Text ({len(body)} characters): {body[:500]}"]
        return _draft("comment-issue", target.key, arguments, preview, problems, target.updated_at)

    # ---- writes: run only after a person approved exactly these arguments ----

    def create_issue(  # noqa: PLR0913, PLR0917 - the same fields as the draft
        self,
        project: str,
        kind: str,
        summary: str,
        description: str = "",
        parent: str | None = None,
        labels: Sequence[str] = (),
        assign_to_me: bool = False,
        due: str | None = None,
    ) -> Applied:
        """Create the work item; run again with the same arguments it finds the first and creates nothing.

        Raises:
            HeinzelError: If the arguments are not a ready draft, or Jira or acli refuses.
        """
        site = require_site(self._settings)
        draft = self.draft_create(project, kind, summary, description, parent, labels, assign_to_me, due)
        _ready(draft)
        a = draft.arguments
        key, marker = cast("str", a["project"]), LABEL_PREFIX + draft.digest
        earlier = self._client.json(
            "Jira",
            [
                "jira",
                "workitem",
                "search",
                "--jql",
                f'project = "{key}" AND labels = "{marker}"',
                "--fields",
                "key,summary",
                "--json",
            ],
            "the earlier attempt",
        )
        found = [
            name
            for d in earlier
            for i in as_list(as_dict(d).get("issues") if is_object(d) else d)
            if isinstance(name := as_dict(i).get("key"), str)
        ]
        if found:
            return Applied(
                action="create-issue",
                key=found[0],
                url=f"{site}/browse/{found[0]}",
                done=[f"Already created as {found[0]}."],
                already_done=True,
            )
        attributes: dict[str, Any] = {}
        if a["parent"]:
            attributes["parent"] = {"key": a["parent"]}
        if a["due"]:
            attributes["duedate"] = a["due"]
        definition: dict[str, Any] = {
            "projectKey": key,
            "type": a["kind"],
            "summary": a["summary"],
            "labels": [*cast("list[str]", a["labels"]), marker],
        }
        if a["description"]:
            definition["description"] = _adf(cast("str", a["description"]))
        if attributes:
            definition["additionalAttributes"] = attributes
        answer = self._run_with_file(definition, ["jira", "workitem", "create", "--from-json"], key, "Create issues")
        made = as_dict(answer).get("key")
        if not isinstance(made, str) or not made.startswith(f"{key}-"):
            msg = f"acli created a work item in {key} but did not say which; look for the label {marker}."
            raise HeinzelError(msg)
        done = [f"Created {made}."]
        if a["assign_to_me"]:
            try:
                self._client.json(
                    "Jira",
                    ["jira", "workitem", "assign", "--key", made, "--assignee", "@me", "--yes", "--json"],
                    made,
                    write="Assign issues",
                )
            except HeinzelError as exc:
                msg = f"{made} was created, but assigning it to you failed: {exc}"
                raise HeinzelError(msg) from None
            done.append("Assigned to you.")
        return Applied(action="create-issue", key=made, url=f"{site}/browse/{made}", done=done)

    def update_issue(  # noqa: PLR0913, PLR0917 - the same fields as the draft, and what it saw
        self,
        key: str,
        seen: AwareDatetime | str,
        summary: str | None = None,
        description: str | None = None,
        add_labels: Sequence[str] = (),
        remove_labels: Sequence[str] = (),
        assign_to_me: bool = False,
        status: str | None = None,
    ) -> Applied:
        """Change the work item as drafted, if it has not changed since the draft saw it.

        Raises:
            HeinzelError: If the arguments are not a ready draft, the work item changed, or Jira or acli refuses.
        """
        site = require_site(self._settings)
        target = self._target(issue_key(key))
        draft = self._update_draft(target, summary, description, (add_labels, remove_labels), assign_to_me, status)
        _ready(draft)
        _unchanged(target, seen)
        a = draft.arguments
        done: list[str] = []
        flags = [f"--key={target.key}", "--yes", "--json"]
        if "summary" in a:
            flags.append(f"--summary={a['summary']}")
        if "description" in a:
            flags.append(f"--description={a['description']}")
        if "add_labels" in a:
            flags.append("--labels=" + ",".join(cast("list[str]", a["add_labels"])))
        if "remove_labels" in a:
            flags.append("--remove-labels=" + ",".join(cast("list[str]", a["remove_labels"])))
        if a.get("assign_to_me"):
            flags.append("--assignee=@me")
        if len(flags) > 3:  # noqa: PLR2004 - more than key, yes and json
            self._client.json("Jira", ["jira", "workitem", "edit", *flags], target.key, write="Edit issues")
            done.append("Edited " + ", ".join(x.split("=")[0].removeprefix("--") for x in flags[3:]) + ".")
        if "status" in a:
            move = [
                "jira",
                "workitem",
                "transition",
                f"--key={target.key}",
                f"--status={a['status']}",
                "--yes",
                "--json",
            ]
            try:
                self._client.json("Jira", move, target.key, write="Transition issues")
            except HeinzelError as exc:
                before = " ".join(done) or "Nothing else was changed."
                msg = f"{before} Moving {target.key} to {a['status']} failed: {exc}"
                raise HeinzelError(msg) from None
            done.append(f"Moved to {a['status']}.")
        return Applied(action="update-issue", key=target.key, url=f"{site}/browse/{target.key}", done=done)

    def comment_issue(self, key: str, text: str, seen: AwareDatetime | str) -> Applied:
        """Post the comment unless the work item changed since the draft saw it; never twice.

        Raises:
            HeinzelError: If the arguments are not a ready draft, the work item changed, or Jira or acli refuses.
        """
        site = require_site(self._settings)
        target = self._target(issue_key(key))
        draft = self._comment_draft(target, text)
        _ready(draft)
        body = cast("str", draft.arguments["text"])
        if target.updated_at != seen:
            if any(c.text == body for c in target.comments):  # the first attempt got through
                return Applied(
                    action="comment-issue",
                    key=target.key,
                    url=f"{site}/browse/{target.key}",
                    done=["Already posted."],
                    already_done=True,
                )
            _unchanged(target, seen)
        self._client.json(
            "Jira",
            ["jira", "workitem", "comment", "create", f"--key={target.key}", f"--body={body}", "--json"],
            target.key,
            write="Add comments",
        )
        return Applied(
            action="comment-issue", key=target.key, url=f"{site}/browse/{target.key}", done=["Comment posted."]
        )

    def _run_with_file(self, definition: dict[str, Any], command: list[str], subject: str, permission: str) -> object:
        descriptor, name = tempfile.mkstemp(suffix=".json", prefix="hz-atlassian-")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(definition, handle)
            answer = self._client.json("Jira", [*command, name, "--json"], subject, write=permission)
        finally:
            Path(name).unlink(missing_ok=True)
        return answer[0] if answer else None


def _parent(parent: str | None, kind: str, problems: list[str]) -> str | None:
    key = None
    if parent:
        try:
            key = issue_key(parent)
        except HeinzelError as exc:
            problems.append(str(exc))
    if kind.lower() == "subtask" and not key:
        problems.append("A Subtask needs a parent work item.")
    if kind.lower() == "epic" and key:
        problems.append("An Epic has no parent.")
    return key


def _project_or(project: str, problems: list[str]) -> str | None:
    try:
        return project_key(project)
    except HeinzelError as exc:
        problems.append(str(exc))
        return None


def _ready(draft: Draft) -> None:
    if not draft.ready:
        msg = "Not applied; the draft is not ready: " + " ".join(draft.problems)
        raise HeinzelError(msg)


def _unchanged(target: Ticket, seen: datetime | str) -> None:
    """Refuse unless the work item is as the draft saw it; `seen` may be the draft's ISO text.

    Raises:
        HeinzelError: If the work item changed after the draft saw it.
    """
    if isinstance(seen, str):
        seen = TypeAdapter(AwareDatetime).validate_python(seen)
    if target.updated_at != seen.astimezone(UTC):
        msg = (
            f"{target.key} changed at {target.updated_at.isoformat()}, after the draft saw it at "
            f"{seen.astimezone(UTC).isoformat()}. Nothing was changed; draft again and approve what you then see."
        )
        raise HeinzelError(msg)
