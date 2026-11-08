"""Fictional reports and a fictional release clone for documentation captures; no Beads database is touched."""

import builtins
import os
import runpy
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from heinzel_issues import _service
from heinzel_issues._contract import Attachment, Task, TaskState, TrackerError


def at(day: int, hour: int) -> datetime:
    return datetime(2026, 11, day, hour, 0, tzinfo=UTC)


TASKS = [
    Task(
        id="demo-3",
        title="Add a dark theme to the printed agenda",
        state=TaskState.RECEIVED,
        status="open",
        created_at=at(8, 9),
        updated_at=at(8, 9),
    ),
    Task(
        id="demo-2",
        title="The footer clock jumps by a pixel every minute",
        state=TaskState.WORKING,
        status="in_progress",
        created_at=at(6, 14),
        updated_at=at(7, 10),
    ),
    Task(
        id="demo-1",
        title="Weather shows yesterday's rain after waking up",
        state=TaskState.DONE,
        status="closed",
        created_at=at(4, 8),
        updated_at=at(5, 16),
        closed_at=at(5, 16),
        references="Fixed in #7",
    ),
]


class Demo:
    """A tracker in memory with three fictional items, one in each state."""

    name = "beads"

    def submit(self, title: str, body: str, attachments: Sequence[Attachment] = ()) -> Task:
        raise TrackerError("Sending is off in this demonstration.")

    def list(self) -> list[Task]:
        return list(TASKS)

    def get(self, task_id: str) -> Task:
        return next(task for task in TASKS if task.id == task_id)

    def changes(self, since: datetime | None) -> builtins.list[Task]:
        return list(TASKS)


def demo(_table: Mapping[str, Any]) -> Demo:
    return Demo()


def release_clone() -> Path:
    """A git clone whose fix (#7) shipped in the fictional release 0.9.27 on 7 Nov 2026."""
    folder = Path(tempfile.mkdtemp(prefix="issues-demo-"))
    ident = ["-c", "user.name=Ada Example", "-c", "user.email=ada@example.invalid"]
    for date, args in [
        ("2026-11-01T12:00:00Z", ["init", "-q", "-b", "main"]),
        ("2026-11-01T12:00:00Z", [*ident, "commit", "-q", "--allow-empty", "-m", "feat: start (#1)"]),
        ("2026-11-01T12:00:00Z", [*ident, "tag", "-a", "v0.9.26", "-m", "0.9.26"]),
        ("2026-11-05T16:00:00Z", [*ident, "commit", "-q", "--allow-empty", "-m", "fix(weather): fresh rain (#7)"]),
        ("2026-11-07T10:00:00Z", [*ident, "tag", "-a", "v0.9.27", "-m", "0.9.27"]),
    ]:
        environment = {
            **{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_AUTHOR_DATE": date,
            "GIT_COMMITTER_DATE": date,
        }
        subprocess.run(["git", *args], cwd=folder, env=environment, check=True, capture_output=True)  # noqa: S603, S607
    return folder


_service.BUILTIN = {"beads": demo}
os.environ.update(
    HZ_ISSUES__TRACKER="beads",
    HZ_ISSUES__RELEASES=f'[{{"path": "{release_clone()}", "ref": "main"}}]',
)
sys.argv = ["hz", *sys.argv[1:]]
runpy.run_module("heinzel", run_name="__main__")
