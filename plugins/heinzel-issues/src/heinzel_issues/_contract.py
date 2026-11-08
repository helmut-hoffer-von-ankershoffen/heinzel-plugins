"""The task-tracking contract: what any tracker behind Issues must do, whoever makes it.

A connector turns one tracker (Beads, Linear, Jira, GitHub issues, cards in git) into `Task`s with one of three plain
states. Issues never sees a vendor's statuses, ids or workflow beyond the connector; a new tracker is a new connector,
registered under the `heinzel_issues.connectors` entry point group, with no change here or in Heinzel's core.
"""

import builtins
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from enum import StrEnum
from importlib.metadata import entry_points
from typing import Any, Protocol, runtime_checkable

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

ENTRY_POINTS = "heinzel_issues.connectors"
"""Where other packages register further connectors: `name = "package.module:factory"`."""


class TaskState(StrEnum):
    """The only states a person sees, whatever the tracker calls them."""

    RECEIVED = "received"
    """Submitted; nobody is on it yet."""
    WORKING = "working"
    """Someone is working on it."""
    DONE = "done"
    """Finished."""


STATE_LABELS: Mapping[TaskState, str] = {
    TaskState.RECEIVED: "Received",
    TaskState.WORKING: "Being worked on",
    TaskState.DONE: "Done",
}


class Attachment(BaseModel):
    """A file sent with a report, such as an annotated screenshot."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=120, description="The file name, without folders.")
    content: bytes = Field(max_length=5 * 1024 * 1024, description="The file's bytes, at most 5 MiB.")


class Task(BaseModel):
    """One tracked item as the tracker reports it, already mapped to a plain state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(description="The tracker's identifier of the item.")
    title: str = Field(description="One line: what was reported or requested.")
    body: str = Field(default="", description="The full text as submitted.")
    state: TaskState = Field(description="Received, being worked on, or done.")
    status: str = Field(description="The tracker's own status word, for experts only.")
    created_at: AwareDatetime = Field(description="When it was submitted.")
    updated_at: AwareDatetime = Field(description="When the tracker last changed it.")
    closed_at: AwareDatetime | None = Field(default=None, description="When it was done, if it is.")
    references: str = Field(
        default="",
        description="Tracker text written by whoever works on it (notes, links, close reason), where pull request "
        "numbers are found; never the submitter's own text.",
    )


@runtime_checkable
class TaskTracker(Protocol):
    """What a connector provides: submit, list, get and the changes since a moment."""

    name: str
    """The connector's name in `issues.tracker`, e.g. `beads`."""

    def submit(self, title: str, body: str, attachments: Sequence[Attachment] = ()) -> Task:
        """Create a new item from a person's report or request; it starts as received."""
        ...

    def list(self) -> builtins.list[Task]:
        """Every item submitted through Issues, newest first."""
        ...

    def get(self, task_id: str) -> Task:
        """One item by its tracker id."""
        ...

    def changes(self, since: datetime | None) -> builtins.list[Task]:
        """The items changed after `since` (all of them for None): what a subscriber looks at on each check."""
        ...


class TrackerError(Exception):
    """A tracker could not be reached or refused; the message says what to do, in plain words."""


Factory = Callable[[Mapping[str, Any]], TaskTracker]
"""Builds a connector from its own settings table, e.g. `issues.beads`."""


def connectors(builtin: Mapping[str, Factory]) -> dict[str, Factory]:
    """The built-in connectors plus every one another installed package registers; a built-in name wins."""
    found: dict[str, Factory] = {}
    for point in entry_points(group=ENTRY_POINTS):
        try:
            found[point.name] = point.load()
        except Exception:  # noqa: BLE001, S112 - a broken third-party connector must not take Issues down
            continue
    return {**found, **builtin}
