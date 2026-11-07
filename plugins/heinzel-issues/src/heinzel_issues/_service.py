"""Issues as a person sees them: what they sent, whether someone is on it, whether it is done and in which release."""

import json
import os
import tempfile
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from heinzel import ModuleSettings, NoticeKind, Notifications, Settings, clean_text
from pydantic import AwareDatetime, BaseModel, Field, JsonValue, ValidationError

from heinzel_issues._beads import BeadsSettings, BeadsTracker
from heinzel_issues._contract import (
    STATE_LABELS,
    Attachment,
    Factory,
    Task,
    TaskState,
    TaskTracker,
    TrackerError,
    connectors,
)
from heinzel_issues._releases import PullRequest, Release, ReleaseResolver, ReleaseSource, released_text

NONE = "none"
SETUP = "hz setup issues"
ROUTE = "/?panel=issues:requests"
MAX_TEXT = 20_000
MAX_TITLE = 80
MAX_ATTACHMENTS = 4
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
_KINDS = ((b"\x89PNG\r\n\x1a\n", "PNG image"), (b"\xff\xd8\xff", "JPEG image"))
NOT_SET_UP = "Issue tracking is not set up."
BUILTIN: Mapping[str, Factory] = {"beads": BeadsTracker.from_settings}


class IssuesSettings(ModuleSettings):
    """Which tracker holds what you report and request, and where releases are found."""

    tracker: str = Field(
        default=NONE,
        title="Tracker",
        description="Where reports and requests go: none (off), beads, or another installed connector.",
    )
    beads: BeadsSettings = Field(default_factory=BeadsSettings, title="Beads", description="A local Beads database.")
    releases: list[ReleaseSource] = Field(
        default_factory=list[ReleaseSource],
        max_length=16,
        title="Releases",
        description="Local clones whose tags are releases, the main one first, to say which release shipped a fix.",
    )
    connectors: dict[str, dict[str, JsonValue]] = Field(
        default_factory=dict[str, dict[str, JsonValue]],
        title="Other trackers",
        description="Settings of further installed connectors, by connector name.",
    )


class Details(BaseModel):
    """What only experts and agents need: the tracker's own words and the work that shipped it."""

    tracker: str = Field(description="The connector, e.g. beads.")
    id: str = Field(description="The tracker's id of the item.")
    status: str = Field(description="The tracker's own status word.")
    pull_requests: list[PullRequest] = Field(description="Pull requests named in the tracker, with their release.")


class Report(BaseModel):
    """One report or request, in plain words."""

    title: str = Field(description="One line: what was sent.")
    state: TaskState = Field(description="received, working or done.")
    status: str = Field(description="Received, Being worked on, Done, or Released in 0.9.27 on 7 Nov 2026.")
    release: Release | None = Field(default=None, description="The release that shipped it; none until then.")
    submitted_at: AwareDatetime = Field(description="When it was sent.")
    done_at: AwareDatetime | None = Field(default=None, description="When it was done.")
    details: Details = Field(description="For experts and agents only; the app and the table leave it out.")


class Reports(BaseModel):
    """Everything sent through Issues, or why it cannot be shown."""

    ready: bool = Field(description="Whether a tracker is set up and answered.")
    problem: str | None = Field(default=None, description="Why nothing can be shown, in plain words.")
    fix: str | None = Field(default=None, description="The one step that fixes it, e.g. hz setup issues.")
    reports: list[Report] = Field(default_factory=list[Report], description="Newest first.")


class Change(BaseModel):
    """A state change the watch noticed."""

    title: str
    status: str
    key: str


class Watched(BaseModel):
    """What one watch run did."""

    checked: bool = Field(description="Whether the tracker was asked.")
    changes: list[Change] = Field(default_factory=list[Change], description="State changes found.")
    noticed: int = Field(default=0, description="How many became notices.")


class _Seen(BaseModel):
    state: TaskState
    release: str | None = None
    references: str = ""
    title: str = ""


class _Watch(BaseModel):
    checked_at: datetime | None = None
    seen: dict[str, _Seen] = Field(default_factory=dict[str, _Seen])


class IssuesService:
    """Connects the configured tracker and the release lookup; nothing runs until it is asked."""

    def __init__(self, settings: IssuesSettings, hz: Settings) -> None:
        """Remember where the watch keeps what it has already seen."""
        self.settings = settings
        self._watch_file = hz.state_dir / "issues" / "watch.json"
        self._tracker: TaskTracker | None = None
        self.resolver = ReleaseResolver(settings.releases)
        self.clock: Callable[[], datetime] = lambda: datetime.now(UTC)
        self.factories: Callable[[], Mapping[str, Factory]] = lambda: connectors(BUILTIN)

    @property
    def enabled(self) -> bool:
        """Whether a tracker is chosen at all."""
        return self.settings.tracker != NONE

    def tracker(self) -> TaskTracker:
        """The configured connector.

        Raises:
            TrackerError: If none is set up or the named one is not installed.
        """
        if self._tracker is not None:
            return self._tracker
        name = self.settings.tracker
        if name == NONE:
            raise TrackerError(NOT_SET_UP)
        factories = self.factories()
        if name not in factories:
            msg = f"The tracker {name!r} is not installed; known: {', '.join(sorted(factories)) or 'none'}."
            raise TrackerError(msg)
        table: Mapping[str, Any] = (
            self.settings.beads.model_dump() if name == "beads" else self.settings.connectors.get(name, {})
        )
        self._tracker = factories[name](table)
        return self._tracker

    def overview(self) -> Reports:
        """Every report and request, newest first; or the reason there are none to show."""
        if not self.enabled:
            return Reports(ready=False, problem=NOT_SET_UP, fix=SETUP)
        try:
            tasks = self.tracker().list()
        except TrackerError as error:
            return Reports(ready=False, problem=str(error), fix=SETUP)
        return Reports(ready=True, reports=[self.report(task) for task in tasks])

    def get(self, task_id: str) -> Report:
        """One report by its tracker id.

        Raises:
            TrackerError: If it cannot be read.
        """
        return self.report(self.tracker().get(task_id))

    def submit(self, text: str, attachments: Sequence[Path] = ()) -> Report:
        """Send a report or request to the tracker.

        Raises:
            TrackerError: If the text is empty or too long, an attachment is refused, or the tracker fails.
        """
        body = clean_text(text).strip()
        if not body:
            msg = "Say what happened or what you would like."
            raise TrackerError(msg)
        if len(body) > MAX_TEXT:
            msg = f"That is {len(body)} characters; at most {MAX_TEXT} fit in one report."
            raise TrackerError(msg)
        files = [read_attachment(path) for path in attachments]
        if len(files) > MAX_ATTACHMENTS:
            msg = f"At most {MAX_ATTACHMENTS} attachments fit in one report."
            raise TrackerError(msg)
        return self.report(self.tracker().submit(title_of(body), body, files))

    def report(self, task: Task) -> Report:
        """A task in plain words, with its release once it shipped."""
        release = self.resolver.release(task.references) if task.state == TaskState.DONE else None
        return Report(
            title=task.title,
            state=task.state,
            status=released_text(release) if release else STATE_LABELS[task.state],
            release=release,
            submitted_at=task.created_at,
            done_at=task.closed_at,
            details=Details(
                tracker=self.settings.tracker,
                id=task.id,
                status=task.status,
                pull_requests=self.resolver.pull_requests(task.references),
            ),
        )

    def watch(self, notifications: Notifications | None) -> Watched:
        """Look at what changed since the last check and record a notice for each new state or release.

        The first check only remembers what is there, so turning Issues on does not flood you with old news.

        Raises:
            TrackerError: If the tracker fails; the daemon reports the run as failed.
        """
        if not self.enabled:
            return Watched(checked=False)
        state = _read(self._watch_file)
        first = state.checked_at is None
        now = self.clock()
        since = state.checked_at - timedelta(minutes=2) if state.checked_at else None
        changed = {task.id: task for task in self.tracker().changes(since)}
        found: list[Change] = []
        for task_id, task in changed.items():
            report = self.report(task)
            before = state.seen.get(task_id)
            version = report.release.version if report.release else None
            if not first and (before is None or before.state != task.state or before.release != version):
                found.append(_change(task_id, report))
            state.seen[task_id] = _Seen(state=task.state, release=version, references=task.references, title=task.title)
        for task_id, seen in state.seen.items():
            if task_id in changed or seen.state != TaskState.DONE or seen.release is not None:
                continue
            release = self.resolver.release(seen.references)
            if release is not None:
                seen.release = release.version
                status = released_text(release)
                found.append(Change(title=seen.title, status=status, key=f"issues:{task_id}:release:{release.version}"))
        state.checked_at = now
        _write(self._watch_file, state)
        noticed = sum(1 for change in found if notifications is not None and _notify(notifications, change))
        return Watched(checked=True, changes=found, noticed=noticed)


def _change(task_id: str, report: Report) -> Change:
    version = report.release.version if report.release else None
    key = f"issues:{task_id}:release:{version}" if version else f"issues:{task_id}:{report.state.value}"
    return Change(title=report.title, status=report.status, key=key)


def _notify(notifications: Notifications, change: Change) -> bool:
    status = change.status.split(" on ")[0] if change.status.startswith("Released") else change.status
    notice = notifications.emit(
        NoticeKind.PLUGIN,
        f"{status}: {change.title}"[:120],
        "Your report or request changed.",
        route=ROUTE,
        command="hz issues list",
        key=change.key,
    )
    return notice is not None


def title_of(text: str) -> str:
    """The first line of a report, shortened to one line of at most 80 characters."""
    line = next((line.strip() for line in text.splitlines() if line.strip()), text.strip())
    return line if len(line) <= MAX_TITLE else line[: MAX_TITLE - 1].rstrip() + "…"


def read_attachment(path: Path) -> Attachment:
    """A PNG, JPEG or UTF-8 text file of at most 5 MiB.

    Raises:
        TrackerError: If it is not a regular file, too large, or of another kind.
    """
    try:
        if not path.is_file():
            msg = f"{path.name} is not a file."
            raise TrackerError(msg)
        if path.stat().st_size > MAX_ATTACHMENT_BYTES:
            msg = f"{path.name} is larger than 5 MiB."
            raise TrackerError(msg)
        content = path.read_bytes()
    except OSError as error:
        msg = f"{path.name} cannot be read: {error.strerror}."
        raise TrackerError(msg) from None
    if not any(content.startswith(magic) for magic, _ in _KINDS):
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            msg = f"{path.name} is not a PNG or JPEG image or a text file."
            raise TrackerError(msg) from None
    return Attachment(name=path.name, content=content)


def _read(path: Path) -> _Watch:
    try:
        return _Watch.model_validate_json(path.read_bytes())
    except (OSError, ValidationError):
        return _Watch()


def _write(path: Path, state: _Watch) -> None:
    """Replace atomically, readable by you only; a failure loses the memory of one check, no more."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(state.model_dump(mode="json"), file)
        Path(temporary).replace(path)
    except OSError:
        return
