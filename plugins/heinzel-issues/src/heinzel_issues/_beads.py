"""The Beads connector: items in a local Beads database, through the `bd` command line and its JSON output.

Beads keeps its database inside a folder (`.beads/` in a repository). The connector only runs `bd` in that folder,
on this machine; it never pushes, syncs or publishes anything. Items submitted through Issues carry a label, so a
shared database can hold other work that Issues does not show.
"""

import builtins
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


def state_of(status: str) -> TaskState:
    """The plain state of a Beads status."""
    return STATES.get(status, TaskState.RECEIVED)


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
    bd: str = Field(default="bd", title="bd command", description="The `bd` program, by name or full path.")

    @field_validator("label")
    @classmethod
    def _check_label(cls, value: str) -> str:
        if not _LABEL.fullmatch(value):
            msg = "a label is lowercase letters, digits, ':', '_' or '-', at most 41 characters"
            raise ValueError(msg)
        return value


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
            msg = "No tracker folder is set: run hz setup issues."
            raise TrackerError(msg)
        folder = path.expanduser()
        if not (folder / ".beads").is_dir():
            msg = f"{folder} has no .beads database: run bd init there, or pick another folder with hz setup issues."
            raise TrackerError(msg)
        return folder

    def program(self) -> str:
        """The `bd` program to run.

        Raises:
            TrackerError: If it cannot be found.
        """
        found = shutil.which(self._settings.bd)
        if found is None and self._settings.bd == "bd":
            found = next((path for path in FALLBACK_BD if os.access(path, os.X_OK)), None)
        if found is None:
            msg = f"The {self._settings.bd} program is not installed: brew install beads, or set issues.beads.bd."
            raise TrackerError(msg)
        return found

    def submit(self, title: str, body: str, attachments: Sequence[Attachment] = ()) -> Task:
        """Create an open item with the Issues label; attachments are copied next to the database.

        Raises:
            TrackerError: If `bd` fails.
        """
        row = self._one(
            self.run(
                ["create", title, "--body-file", "-", "--labels", self._settings.label, "--type", "task", "--json"],
                stdin=body or title,
            )
        )
        if attachments:
            saved = [self.save_attachment(row.id, attachment) for attachment in attachments]
            note = "\n".join(f"Attachment: {path}" for path in saved)
            row = self._one(self.run(["update", row.id, "--append-notes", note, "--json"]))
        return _task(row)

    def list(self) -> builtins.list[Task]:
        """Every item with the Issues label, done ones included, newest first.

        Raises:
            TrackerError: If `bd` fails.
        """
        return self._rows(["list", "--all", "--label", self._settings.label, "--sort", "created", "--json"])

    def get(self, task_id: str) -> Task:
        """One item by id.

        Raises:
            TrackerError: If the id is malformed, unknown or `bd` fails.
        """
        if not _ID.fullmatch(task_id):
            msg = f"{task_id!r} is not an item id."
            raise TrackerError(msg)
        rows = self._rows(["show", task_id, "--json"])
        if not rows:
            msg = f"There is no item {task_id}."
            raise TrackerError(msg)
        return rows[0]

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
        tasks = [_task(row) for row in self.rows(args)]
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
            msg = "The tracker did not confirm the new item; check it with bd list."
            raise TrackerError(msg) from None

    def run(self, args: builtins.list[str], stdin: str | None = None) -> str:
        """Run `bd` with `args` in the folder, non-interactively; its standard output.

        Raises:
            TrackerError: If it cannot start, times out or refuses.
        """
        environment = {**os.environ, "BD_NON_INTERACTIVE": "1", "NO_COLOR": "1"}
        try:
            done = subprocess.run(  # noqa: S603 - a fixed program and argument list, no shell
                [self.program(), *args],
                cwd=self.folder,
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
            msg = f"The tracker refused: {reason}"
            raise TrackerError(msg)
        return done.stdout


def _parse(output: str) -> list[_Row]:
    try:
        data = json.loads(output or "[]")
    except json.JSONDecodeError:
        msg = "The tracker answered with something that is not JSON; is bd up to date?"
        raise TrackerError(msg) from None
    items = cast("list[object]", data if isinstance(data, list) else [data])
    try:
        return [_Row.model_validate(item) for item in items]
    except ValidationError:
        msg = "The tracker answered in a shape Issues does not know; is bd up to date?"
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
        references=references,
    )


ATTACHMENT_NOTE = "Attachment: "
"""How a note names a file saved next to the database."""


class BeadsBoard:
    """Heinzel's `tracker` capability (read and write, ADR 0141) over the same local Beads database.

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
        tags = ",".join(dict.fromkeys([project, *labels]))
        args = ["create", title, "--body-file", "-", "--labels", tags, "--type", "task", "--json", "--actor", reporter]
        return self._issue(self._call(self._beads.row, args, body or title))

    def claim(self, key: str, actor: str) -> Issue:
        """Beads' atomic claim: assigned to `actor` and in progress, or refused if another actor holds it."""
        return self._write(key, actor, ["update", key, "--claim"])

    def transition(self, key: str, state: str, actor: str, note: str | None = None) -> Issue:
        """Set the Beads status `state`, appending `note` to the item's notes if given."""
        return self._write(key, actor, ["update", key, "--status", state, *(["--append-notes", note] if note else [])])

    def note(self, key: str, text: str, actor: str) -> Issue:
        """Append `text` to the item's notes."""
        return self._write(key, actor, ["update", key, "--append-notes", text])

    def attach(self, key: str, name: str, data: bytes, media_type: str, actor: str) -> FileRef:
        """Save the file next to the database, privately, and name it in the item's notes."""
        self._known(key)
        try:
            path = self._beads.save_attachment(key, Attachment(name=name, content=data))
        except (TrackerError, ValidationError) as error:
            raise HeinzelError(str(error)) from None
        self._write(key, actor, ["update", key, "--append-notes", f"{ATTACHMENT_NOTE}{path}"])
        return FileRef(name=Path(path).name, media_type=media_type, size=len(data), ref=path)

    def close(self, key: str, actor: str, reason: str) -> Issue:
        """Close the item, saying why."""
        return self._write(key, actor, ["close", key, "--reason", reason])

    def _known(self, key: str) -> None:
        if not _ID.fullmatch(key):
            msg = f"{key!r} is not a Beads item id."
            raise HeinzelError(msg)

    def _write(self, key: str, actor: str, args: builtins.list[str]) -> Issue:
        self._known(key)
        return self._issue(self._call(self._beads.row, [*args, "--json", "--actor", actor]))

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
        for line in notes.splitlines():
            if not line.startswith(ATTACHMENT_NOTE):
                continue
            ref = line.removeprefix(ATTACHMENT_NOTE).strip()
            media_type = mimetypes.guess_type(ref)[0] or "application/octet-stream"
            try:
                size = (self._beads.folder / ref).stat().st_size
            except (OSError, TrackerError):
                size = 0
            files.append(FileRef(name=Path(ref).name, media_type=media_type, size=size, ref=ref))
        return files
