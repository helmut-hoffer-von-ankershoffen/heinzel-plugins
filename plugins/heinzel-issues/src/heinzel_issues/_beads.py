"""The Beads connector: items in a local Beads database, through the `bd` command line and its JSON output.

Beads keeps its database inside a folder (`.beads/` in a repository). The connector only runs `bd` in that folder,
on this machine; it never pushes, syncs or publishes anything. Items submitted through Issues carry a label, so a
shared database can hold other work that Issues does not show.
"""

import builtins
import json
import os
import re
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, cast

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
            self._run(
                ["create", title, "--body-file", "-", "--labels", self._settings.label, "--type", "task", "--json"],
                stdin=body or title,
            )
        )
        if attachments:
            saved = [self._attach(row.id, attachment) for attachment in attachments]
            note = "\n".join(f"Attachment: {path}" for path in saved)
            row = self._one(self._run(["update", row.id, "--append-notes", note, "--json"]))
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

    def _attach(self, task_id: str, attachment: Attachment) -> str:
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
        output = self._run(args)
        try:
            data = json.loads(output or "[]")
        except json.JSONDecodeError:
            msg = "The tracker answered with something that is not JSON; is bd up to date?"
            raise TrackerError(msg) from None
        items = cast("list[object]", data if isinstance(data, list) else [data])
        try:
            rows = [_Row.model_validate(item) for item in items]
        except ValidationError:
            msg = "The tracker answered in a shape Issues does not know; is bd up to date?"
            raise TrackerError(msg) from None
        tasks = [_task(row) for row in rows]
        return sorted(tasks, key=lambda task: task.created_at, reverse=True)

    def _one(self, output: str) -> _Row:
        try:
            data = json.loads(output)
            return _Row.model_validate(data[0] if isinstance(data, list) else data)
        except (json.JSONDecodeError, ValidationError, IndexError, KeyError):
            msg = "The tracker did not confirm the new item; check it with bd list."
            raise TrackerError(msg) from None

    def _run(self, args: builtins.list[str], stdin: str | None = None) -> str:
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
