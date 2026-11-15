"""The Beads connector: items in a local Beads database, through the `bd` command line and its JSON output.

Beads keeps its database inside a folder (`.beads/` in a repository). The connector only runs `bd` in that folder,
on this machine; it never pushes, syncs or publishes anything. Items submitted through Issues carry a label, so a
shared database can hold other work that Issues does not show.
"""

import builtins
import getpass
import json
import mimetypes
import os
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from heinzel import Attachment as FileRef
from heinzel import HeinzelError, Issue, Window
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from heinzel_issues._contract import Attachment, Task, TaskState, TrackerError

REFUSED = "The tracker refused"
TIMEOUT = 30
"""Seconds one `bd` call may take."""
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
_LABEL = re.compile(r"^[a-z0-9][a-z0-9:_-]{0,40}$")
_NAME = re.compile(r"[^A-Za-z0-9._-]+")
FALLBACK_BD = ("/opt/homebrew/bin/bd", "/usr/local/bin/bd")

STATES: Mapping[str, TaskState] = {
    "open": TaskState.RECEIVED,
    "deferred": TaskState.RECEIVED,
    "pinned": TaskState.RECEIVED,
    "in_progress": TaskState.WORKING,
    "blocked": TaskState.WORKING,
    "hooked": TaskState.WORKING,
    "closed": TaskState.DONE,
}
"""Beads' built-in statuses; anything else (a custom status) counts as received until someone maps it."""


def reporter() -> str:
    """Who sends from this computer, as Beads records the actor: the login name."""
    try:
        return getpass.getuser()
    except (OSError, KeyError):
        return "heinzel-issues"


def flag(name: str, value: str) -> str:
    """One `--name=value` token: text a person typed can never be read by `bd` as an option of its own."""
    return f"{name}={value}"


def state_of(status: str) -> TaskState:
    """The plain state of a Beads status."""
    return STATES.get(status, TaskState.RECEIVED)


def checked_label(value: str) -> str:
    """A Beads label Issues may write.

    Raises:
        ValueError: If it has other characters or is too long.
    """
    if not _LABEL.fullmatch(value):
        msg = "a label is lowercase letters, digits, ':', '_' or '-', at most 41 characters"
        raise ValueError(msg)
    return value


class BeadsSettings(BaseModel):
    """Where the Beads database is and which items Issues owns."""

    model_config = ConfigDict(extra="forbid")

    path: Path | None = Field(
        default=None,
        title="Tracker folder",
        description="The folder that holds the `.beads` database, e.g. a private repository on this computer.",
    )
    label: str = Field(
        default="heinzel-issues",
        title="Label",
        description="The label Issues gives what you submit, and the items it shows.",
    )
    extra_labels: builtins.list[str] = Field(
        default_factory=builtins.list[str],
        max_length=8,
        title="More labels",
        description="Further labels every new report gets, e.g. the one a team's intake queue reads.",
    )
    bd: str = Field(default="bd", title="bd command", description="The `bd` program, by name or full path.")

    @field_validator("label")
    @classmethod
    def _check_label(cls, value: str) -> str:
        return checked_label(value)

    @field_validator("extra_labels")
    @classmethod
    def _check_labels(cls, value: builtins.list[str]) -> builtins.list[str]:
        return [checked_label(label) for label in value]

    @property
    def labels(self) -> builtins.list[str]:
        """Every label a new report gets: the Issues label first, each once."""
        return list(dict.fromkeys([self.label, *self.extra_labels]))


class _Row(BaseModel):
    """The fields of a `bd ... --json` row Issues reads; Beads adds more, which are ignored."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    description: str = ""
    notes: str = ""
    status: str
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    started_at: datetime | None = None
    close_reason: str = ""
    external_ref: str = ""
    assignee: str | None = None
    labels: builtins.list[str] = Field(default_factory=builtins.list[str])
    created_by: str | None = None


class BeadsTracker:
    """`TaskTracker` over one local Beads database."""

    name = "beads"

    def __init__(self, settings: BeadsSettings) -> None:
        """Check nothing yet: a missing folder or program is reported when Issues is used, in plain words."""
        self._settings = settings

    @classmethod
    def from_settings(cls, table: Mapping[str, Any]) -> "BeadsTracker":
        """Build from the `issues.beads` settings table.

        Raises:
            TrackerError: If the table is not valid.
        """
        try:
            return cls(BeadsSettings.model_validate(dict(table)))
        except ValidationError as error:
            msg = f"The Beads settings are not valid: {error.errors()[0]['msg']}"
            raise TrackerError(msg) from None

    @property
    def folder(self) -> Path:
        """The configured folder, checked to hold a Beads database.

        Raises:
            TrackerError: If no folder is set or it has no `.beads` database.
        """
        path = self._settings.path
        if path is None:
            msg = "No tracker folder is set."
            raise TrackerError(msg)
        folder = path.expanduser()
        if not (folder / ".beads").is_dir():
            msg = f"{folder} has no .beads database; pick the folder that holds it."
            raise TrackerError(msg)
        return folder

    @property
    def label(self) -> str:
        """The label that marks an item as a report sent through Issues."""
        return self._settings.label

    def program(self) -> str:
        """The `bd` program to run.

        Raises:
            TrackerError: If it cannot be found.
        """
        found = shutil.which(self._settings.bd)
        if found is None and self._settings.bd == "bd":
            found = next((path for path in FALLBACK_BD if os.access(path, os.X_OK)), None)
        if found is None:
            msg = "The Beads program is not installed on this computer; Issues needs it to reach the tracker."
            raise TrackerError(msg)
        return found

    def submit(self, title: str, body: str, attachments: Sequence[Attachment] = ()) -> Task:
        """Create an open item with the Issues label; attachments are copied next to the database.

        Raises:
            TrackerError: If `bd` fails.
        """
        row = self._one(self.run(self.create_args(title, self._settings.labels, reporter()), stdin=body or title))
        if attachments:
            saved = [self.save_attachment(row.id, attachment) for attachment in attachments]
            note = "\n".join(f"{ATTACHMENT_NOTE}{path}" for path in saved)
            row = self._one(self.run(["update", row.id, flag("--append-notes", note), "--json"]))
        return _task(row)

    @staticmethod
    def create_args(title: str, labels: Sequence[str], actor: str) -> builtins.list[str]:
        """The `bd create` call for a report: the title and the actor only ever as the value of their own flag."""
        return [
            "create",
            flag("--title", title),
            "--body-file",
            "-",
            flag("--labels", ",".join(labels)),
            "--type",
            "task",
            "--json",
            flag("--actor", actor),
        ]

    def mine(self, row: "_Row") -> bool:
        """Whether Issues may show the item: it carries the Issues label and this person sent it.

        A shared database holds other work and other people's reports; neither is ever read out through Issues.
        """
        return self._settings.label in row.labels and row.created_by == reporter()

    def list(self) -> builtins.list[Task]:
        """Every item with the Issues label, done ones included, newest first.

        Raises:
            TrackerError: If `bd` fails.
        """
        return self._rows(["list", "--all", "--label", self._settings.label, "--sort", "created", "--json"])

    def owned(self, task_id: str) -> "_Row":
        """The item `task_id`, if it is one of this person's reports.

        Raises:
            TrackerError: If the id is malformed or unknown, it is not a report of this person, or `bd` fails.
        """
        if not _ID.fullmatch(task_id):
            msg = f"{task_id!r} is not an item id."
            raise TrackerError(msg)
        try:
            rows = [row for row in self.rows(["show", task_id, "--json"]) if self.mine(row)]
        except TrackerError as error:
            if not str(error).startswith(REFUSED):
                raise
            rows = []  # an unknown id and someone else's item read the same
        if not rows:
            msg = f"There is no item {task_id}."
            raise TrackerError(msg)
        return rows[0]

    def get(self, task_id: str) -> Task:
        """One item by id.

        Raises:
            TrackerError: If the id is malformed, unknown or `bd` fails.
        """
        return _task(self.owned(task_id))

    def changes(self, since: datetime | None) -> builtins.list[Task]:
        """Items with the Issues label changed after `since`; all of them for None.

        Raises:
            TrackerError: If `bd` fails.
        """
        if since is None:
            return self.list()
        return self._rows(
            ["list", "--all", "--label", self._settings.label, "--updated-after", since.isoformat(), "--json"]
        )

    def save_attachment(self, task_id: str, attachment: Attachment) -> str:
        """Copy `attachment` next to the database, under `.beads/attachments/<id>/`; the path relative to the folder.

        Raises:
            TrackerError: If it cannot be saved.
        """
        name = _NAME.sub("-", Path(attachment.name).name).strip(".-") or "attachment"
        relative = Path(".beads") / "attachments" / task_id / name
        target = self.folder / relative
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(attachment.content)
        except OSError as error:
            msg = f"The attachment {name} could not be saved: {error.strerror}."
            raise TrackerError(msg) from None
        return relative.as_posix()

    def _rows(self, args: builtins.list[str]) -> builtins.list[Task]:
        tasks = [_task(row) for row in self.rows(args) if self.mine(row)]
        return sorted(tasks, key=lambda task: task.created_at, reverse=True)

    def row(self, args: builtins.list[str], stdin: str | None = None) -> _Row:
        """The one item a `bd ... --json` call answers with.

        Raises:
            TrackerError: If `bd` fails or confirms no item.
        """
        return self._one(self.run(args, stdin))

    def rows(self, args: builtins.list[str]) -> builtins.list[_Row]:
        """The items a `bd ... --json` call lists.

        Raises:
            TrackerError: If `bd` fails or answers in another shape.
        """
        return _parse(self.run(args))

    def _one(self, output: str) -> _Row:
        try:
            data = json.loads(output)
            return _Row.model_validate(data[0] if isinstance(data, list) else data)
        except (json.JSONDecodeError, ValidationError, IndexError, KeyError):
            msg = "The tracker did not confirm the item; open Issues again in a moment to see it."
            raise TrackerError(msg) from None

    def run(self, args: builtins.list[str], stdin: str | None = None) -> str:
        """Run `bd` with `args` in the folder, non-interactively; its standard output.

        Raises:
            TrackerError: If it cannot start, times out or refuses.
        """
        environment = {**os.environ, "BD_NON_INTERACTIVE": "1", "NO_COLOR": "1"}
        folder = self.folder  # a missing database is what setup fixes; say that before a missing program
        program = self.program()
        try:
            done = subprocess.run(  # noqa: S603 - a fixed program and argument list, no shell
                [program, *args],
                cwd=folder,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
                env=environment,
                check=False,
            )
        except subprocess.TimeoutExpired:
            msg = f"The tracker did not answer within {TIMEOUT} seconds."
            raise TrackerError(msg) from None
        except OSError as error:
            msg = f"The tracker could not be started: {error.strerror}."
            raise TrackerError(msg) from None
        if done.returncode != 0:
            reason = (done.stderr.strip().splitlines() or ["no reason given"])[-1][:200]
            msg = f"{REFUSED}: {reason}"
            raise TrackerError(msg)
        return done.stdout


def _parse(output: str) -> list[_Row]:
    try:
        data = json.loads(output or "[]")
    except json.JSONDecodeError:
        msg = "The tracker answered in a way Issues cannot read; the Beads program may be out of date."
        raise TrackerError(msg) from None
    items = cast("list[object]", data if isinstance(data, list) else [data])
    try:
        return [_Row.model_validate(item) for item in items]
    except ValidationError:
        msg = "The tracker answered in a shape Issues does not know; the Beads program may be out of date."
        raise TrackerError(msg) from None


def _task(row: _Row) -> Task:
    references = "\n".join(part for part in (row.notes, row.external_ref, row.close_reason) if part)
    return Task(
        id=row.id,
        title=row.title,
        body=row.description,
        state=state_of(row.status),
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        closed_at=row.closed_at,
        started_at=row.started_at,
        attachments=tuple(Path(ref).name for ref in attachment_refs(row.notes)),
        references=references,
    )


ATTACHMENT_NOTE = "Attachment: "
"""How a note names a file saved next to the database."""


def attachment_refs(notes: str) -> builtins.list[str]:
    """The paths, relative to the tracker folder, of the files the notes name."""
    lines = (line.strip() for line in notes.splitlines())
    return [line.removeprefix(ATTACHMENT_NOTE).strip() for line in lines if line.startswith(ATTACHMENT_NOTE)]


class BeadsBoard:
    """Heinzel's `Tracker` contract (read and write, ADR 0141) over the same local Beads database.

    Issues uses it directly and registers no capability adapter, so installing Issues never changes the tracker other
    plugins are bound to.

    Every write runs `bd` with `--actor`, so Beads records who it was done for. A project is a label: `create` gives
    it to the new item and `issues_updated` lists the items that carry it. A claim is Beads' own atomic `--claim`,
    which refuses an item another actor holds.
    """

    def __init__(self, settings: BeadsSettings) -> None:
        """Run nothing yet, like the connector."""
        self._beads = BeadsTracker(settings)

    @property
    def beads(self) -> BeadsTracker:
        """The connector it writes through."""
        return self._beads

    def issues_updated(self, project: str, window: Window) -> builtins.list[Issue]:
        """Items labelled `project` updated within `window`, oldest first."""
        rows = self._call(
            self._beads.rows,
            ["list", "--all", "--label", project, "--updated-after", window.since.isoformat(), "--json"],
        )
        inside = [row for row in rows if window.since <= row.updated_at < window.until]
        return [self._issue(row) for row in sorted(inside, key=lambda row: row.updated_at)]

    def create(self, project: str, title: str, body: str, reporter: str, labels: builtins.list[str]) -> Issue:
        """Open an item labelled `project` and `labels`, created by `reporter`."""
        tags = list(dict.fromkeys([project, *labels]))
        for label in tags:
            if not _LABEL.fullmatch(label):
                msg = f"{label!r} cannot be a label."
                raise HeinzelError(msg)
        return self._issue(self._call(self._beads.row, self._beads.create_args(title, tags, reporter), body or title))

    def claim(self, key: str, actor: str) -> Issue:
        """Beads' atomic claim: assigned to `actor` and in progress, or refused if another actor holds it."""
        return self._write(key, actor, ["update", key, "--claim"])

    def transition(self, key: str, state: str, actor: str, note: str | None = None) -> Issue:
        """Set the Beads status `state`, appending `note` to the item's notes if given."""
        if not _LABEL.fullmatch(state):
            msg = f"{state!r} is not a Beads status."
            raise HeinzelError(msg)
        notes = [flag("--append-notes", note)] if note else []
        return self._write(key, actor, ["update", key, "--status", state, *notes])

    def note(self, key: str, text: str, actor: str) -> Issue:
        """Append `text` to the item's notes."""
        return self._write(key, actor, ["update", key, flag("--append-notes", text)])

    def attach(self, key: str, name: str, data: bytes, media_type: str, actor: str) -> FileRef:
        """Save the file next to the database, privately, and name it in the item's notes."""
        self._known(key)
        try:
            path = self._beads.save_attachment(key, Attachment(name=name, content=data))
        except (TrackerError, ValidationError) as error:
            raise HeinzelError(str(error)) from None
        self._write(key, actor, ["update", key, flag("--append-notes", f"{ATTACHMENT_NOTE}{path}")])
        return FileRef(name=Path(path).name, media_type=media_type, size=len(data), ref=path)

    def close(self, key: str, actor: str, reason: str) -> Issue:
        """Close the item, saying why."""
        return self._write(key, actor, ["close", key, flag("--reason", reason)])

    def _known(self, key: str) -> None:
        """Only an item with the Issues label is ever changed; other work in the same database is never touched.

        Raises:
            HeinzelError: If the id is malformed, unknown or names other work in the same database.
        """
        if not _ID.fullmatch(key):
            msg = f"{key!r} is not a Beads item id."
            raise HeinzelError(msg)
        rows = self._call(self._beads.rows, ["show", key, "--json"])
        if not any(self._beads.label in row.labels for row in rows):
            msg = f"There is no item {key}."
            raise HeinzelError(msg)

    def _write(self, key: str, actor: str, args: builtins.list[str]) -> Issue:
        self._known(key)
        return self._issue(self._call(self._beads.row, [*args, "--json", flag("--actor", actor)]))

    def _call[T](self, run: Callable[..., T], *args: object) -> T:
        try:
            return run(*args)
        except TrackerError as error:
            raise HeinzelError(str(error)) from None

    def _issue(self, row: _Row) -> Issue:
        return Issue(
            key=row.id,
            title=row.title,
            url=f"beads:{row.id}",
            state=row.status,
            updated_at=row.updated_at,
            assignee=row.assignee or None,
            labels=row.labels,
            created_at=row.created_at,
            closed_at=row.closed_at,
            reporter=row.created_by or None,
            attachments=self._files(row.notes),
        )

    def _files(self, notes: str) -> builtins.list[FileRef]:
        files: builtins.list[FileRef] = []
        for ref in attachment_refs(notes):
            media_type = mimetypes.guess_type(ref)[0] or "application/octet-stream"
            try:
                size = (self._beads.folder / ref).stat().st_size
            except (OSError, TrackerError):
                size = 0
            files.append(FileRef(name=Path(ref).name, media_type=media_type, size=size, ref=ref))
        return files
