"""Issues as a person sees them: what they sent, whether someone is on it, whether it is done and in which release."""

import base64
import binascii
import getpass
import json
import logging
import mimetypes
import os
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from datetime import time as Time
from pathlib import Path
from typing import Any

from heinzel import (
    Config,
    ConfigEditor,
    HeinzelError,
    ModuleSettings,
    NoticeKind,
    Notifications,
    Settings,
    Tracker,
    clean_text,
)
from pydantic import AwareDatetime, BaseModel, Field, JsonValue, ValidationError

from heinzel_issues._beads import BeadsSettings, BeadsTracker, checked_label
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
SECTION = "issues"
SETUP = "hz setup issues"
ROUTE = "/?panel=issues:requests"
MAX_TEXT = 20_000
MAX_TITLE = 80
MAX_ATTACHMENTS = 4
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
_KINDS = ((b"\x89PNG\r\n\x1a\n", "PNG image"), (b"\xff\xd8\xff", "JPEG image"))
NOT_SET_UP = "Issue tracking is not set up."
BUILTIN: Mapping[str, Factory] = {"beads": BeadsTracker.from_settings}
NO_FILES = Config.empty()
"""Settings built in code, as tests do: there is no file to read again."""
logger = logging.getLogger("heinzel_issues")


def log_event(name: str, **fields: object) -> None:
    """One structured event: a stable `area.operation.step` name and fields, never what a person typed."""
    logger.info(name, extra={"event": name, **{key: value for key, value in fields.items() if value is not None}})


def reporter() -> str:
    """Who sends from this computer, as Beads records the actor: the login name."""
    try:
        return getpass.getuser()
    except (OSError, KeyError):
        return "heinzel-issues"


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


class Step(BaseModel):
    """One moment in a report's history, in plain words."""

    label: str = Field(description="Sent, Being worked on, Done, or Released in 0.9.27.")
    at: AwareDatetime | None = Field(default=None, description="When it happened; none while it is not known.")


class Report(BaseModel):
    """One report or request, in plain words."""

    title: str = Field(description="One line: what was sent.")
    body: str = Field(default="", description="The full text as it was sent.")
    attachments: list[str] = Field(default_factory=list[str], description="The names of the files sent with it.")
    history: list[Step] = Field(default_factory=list[Step], description="What happened so far, oldest first.")
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
    folder: str | None = Field(default=None, description="The tracker folder in use or last tried, to set it up.")
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

    def __init__(self, settings: IssuesSettings, hz: Settings, config: Config = NO_FILES) -> None:
        """Remember where the watch keeps what it has already seen, and which files hold the settings."""
        self.settings = settings
        self._config = config
        self._watch_file = hz.state_dir / "issues" / "watch.json"
        self._tracker: TaskTracker | None = None
        self.resolver = ReleaseResolver(settings.releases)
        self.clock: Callable[[], datetime] = lambda: datetime.now(UTC)
        self.factories: Callable[[], Mapping[str, Factory]] = lambda: connectors(BUILTIN)

    @property
    def enabled(self) -> bool:
        """Whether a tracker is chosen at all."""
        return self.settings.tracker != NONE

    def use(self, settings: IssuesSettings) -> None:
        """Work with `settings` from now on; the tracker and the release lookup are built again when they differ."""
        if settings == self.settings:
            return
        self.settings = settings
        self._tracker = None
        self.resolver = ReleaseResolver(settings.releases)

    def refresh(self) -> None:
        """Follow the settings files as they are now, so setting Issues up in the app needs no restart.

        The app and the daemon are separate programs; each sees the other's change at its next use. Settings built
        in code (no file exists) and files that are invalid right now leave the current settings in place.
        """
        if not any(file.exists for file in self._config.files):
            return
        try:
            self.use(self._config.reread().settings(IssuesSettings, SECTION))
        except (HeinzelError, ValidationError):
            return

    def connect(self, editor: ConfigEditor, path: str, labels: str = "", releases: str = "") -> Reports:
        """Send reports to the Beads database in the folder `path`, after checking that it answers.

        `labels` are further labels for every new report and `releases` are git clones whose tags are releases;
        both are lists separated by commas or spaces, and an empty one keeps what is set.

        Raises:
            TrackerError: If the folder has no Beads database, `bd` does not answer, or a value is not valid.
        """
        self.refresh()
        folder = _folder(path, "The tracker folder")
        if not (folder / ".beads").is_dir():
            msg = f"{folder} has no Beads database (a .beads folder). Pick the folder that holds it."
            raise TrackerError(msg)
        try:
            extra = [checked_label(label) for label in _words(labels)] or self.settings.beads.extra_labels
            beads = BeadsSettings.model_validate(
                {**self.settings.beads.model_dump(), "path": folder, "extra_labels": extra}
            )
        except ValueError as error:
            msg = f"That label cannot be used: {str(error).splitlines()[-1].strip()}."
            raise TrackerError(msg) from None
        clones = [_folder(clone, "A release clone") for clone in _words(releases)]
        for clone in clones:
            if not clone.is_dir():
                msg = f"{clone} is not a folder on this computer."
                raise TrackerError(msg)
        sources = [ReleaseSource(path=clone) for clone in clones] or self.settings.releases
        BeadsTracker(beads).list()  # the database and the bd program answer, before anything is saved
        try:
            editor.write(f"{SECTION}.beads", beads.model_dump(mode="json", exclude_none=True))
            if clones:
                editor.write(f"{SECTION}.releases", [source.model_dump(mode="json") for source in sources])
            editor.write(f"{SECTION}.tracker", "beads")
        except HeinzelError as error:
            raise TrackerError(str(error)) from None
        self.use(self.settings.model_copy(update={"tracker": "beads", "beads": beads, "releases": sources}))
        log_event("issues.connect.outcome", operation="connect", tracker="beads", outcome="ok")
        return self.overview()

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
        self.refresh()
        folder = str(self.settings.beads.path) if self.settings.beads.path else None
        if not self.enabled:
            return Reports(ready=False, problem=NOT_SET_UP, fix=SETUP, folder=folder)
        try:
            tasks = self.tracker().list()
        except TrackerError as error:
            return Reports(ready=False, problem=str(error), fix=SETUP, folder=folder)
        return Reports(ready=True, reports=[self.report(task) for task in tasks], folder=folder)

    def get(self, task_id: str) -> Report:
        """One report by its tracker id.

        Raises:
            TrackerError: If it cannot be read.
        """
        self.refresh()
        return self.report(self.tracker().get(task_id))

    def submit(
        self,
        text: str,
        attachments: Sequence[Path] = (),
        board: Tracker | None = None,
        uploads: Sequence[Attachment] = (),
    ) -> Report:
        """Send a report or request to the tracker; for Beads through `board`, which implements Heinzel's `Tracker`.

        `uploads` are files that arrive as content, as the app sends them, and follow the same rules as paths.

        Logs `issues.submit.start` and one `issues.submit.outcome` with the tracker, attachment count, outcome and
        duration; never the text.

        Raises:
            TrackerError: If the text is empty or too long, an attachment is refused, or the tracker fails.
        """
        self.refresh()
        started = time.monotonic()
        fields: dict[str, object] = {"operation": "submit", "tracker": self.settings.tracker}
        log_event("issues.submit.start", **fields, attachments=len(attachments) + len(uploads))
        try:
            report = self._submit(text, [*map(read_attachment, attachments), *uploads], board)
        except TrackerError:
            # No message: a tracker's refusal may quote what was typed.
            duration = round((time.monotonic() - started) * 1000)
            log_event("issues.submit.outcome", **fields, outcome="failed", duration_ms=duration)
            raise
        duration = round((time.monotonic() - started) * 1000)
        log_event("issues.submit.outcome", **fields, outcome="ok", duration_ms=duration, state=report.state.value)
        return report

    def _submit(self, text: str, files: Sequence[Attachment], board: Tracker | None) -> Report:
        body = clean_text(text).strip()
        if not body:
            msg = "Say what happened or what you would like."
            raise TrackerError(msg)
        if len(body) > MAX_TEXT:
            msg = f"That is {len(body)} characters; at most {MAX_TEXT} fit in one report."
            raise TrackerError(msg)
        if len(files) > MAX_ATTACHMENTS:
            msg = f"At most {MAX_ATTACHMENTS} attachments fit in one report."
            raise TrackerError(msg)
        if board is None or self.settings.tracker != "beads":
            return self.report(self.tracker().submit(title_of(body), body, files))
        tracker = self.tracker()  # checks the folder and program before anything is written
        actor = reporter()
        try:
            issue = board.create(
                self.settings.beads.label, title_of(body), body, actor, self.settings.beads.extra_labels
            )
            for file in files:
                media_type = mimetypes.guess_type(file.name)[0] or "text/plain"
                board.attach(issue.key, file.name, file.content, media_type, actor)
        except HeinzelError as error:
            raise TrackerError(str(error)) from None
        return self.report(tracker.get(issue.key))

    def report(self, task: Task) -> Report:
        """A task in plain words, with its release once it shipped."""
        release = self.resolver.release(task.references) if task.state == TaskState.DONE else None
        return Report(
            title=task.title,
            body=task.body,
            attachments=list(task.attachments),
            history=history(task, release),
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
        self.refresh()
        if not self.enabled:
            return Watched(checked=False)
        started = time.monotonic()
        fields: dict[str, object] = {"operation": "watch", "tracker": self.settings.tracker}
        log_event("issues.watch.start", **fields)
        try:
            result = self._watch(notifications)
        except TrackerError as error:
            duration = round((time.monotonic() - started) * 1000)
            log_event("issues.watch.outcome", **fields, outcome="failed", duration_ms=duration, error=str(error))
            raise
        duration = round((time.monotonic() - started) * 1000)
        log_event(
            "issues.watch.outcome",
            **fields,
            outcome="ok",
            duration_ms=duration,
            changes=len(result.changes),
            noticed=result.noticed,
        )
        return result

    def _watch(self, notifications: Notifications | None) -> Watched:
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


def history(task: Task, release: Release | None) -> list[Step]:
    """What happened to a report so far, oldest first, in the words of its states."""
    steps = [Step(label="Sent", at=task.created_at)]
    if task.started_at is not None or task.state == TaskState.WORKING:
        steps.append(Step(label=STATE_LABELS[TaskState.WORKING], at=task.started_at))
    if task.state == TaskState.DONE:
        steps.append(Step(label=STATE_LABELS[TaskState.DONE], at=task.closed_at))
    if release is not None:
        steps.append(Step(label=f"Released in {release.version}", at=datetime.combine(release.date, Time(), UTC)))
    return steps


def _words(text: str) -> list[str]:
    return [word for word in text.replace(",", " ").split() if word]


def _folder(text: str, what: str) -> Path:
    folder = Path(clean_text(text).strip()).expanduser()
    if not folder.is_absolute():
        msg = f"{what} must be a full path, e.g. ~/Code/team-board."
        raise TrackerError(msg)
    return folder


def upload(name: str, data: str) -> Attachment:
    """A file the app sent as base64 text, under the same rules as a file from disk.

    Raises:
        TrackerError: If the text is not base64, or the file is too large or of another kind.
    """
    label = Path(clean_text(name).strip()).name or "attachment"
    try:
        content = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        msg = f"{label} did not arrive whole; attach it again."
        raise TrackerError(msg) from None
    return checked_attachment(label, content)


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
    return checked_attachment(path.name, content)


def checked_attachment(name: str, content: bytes) -> Attachment:
    """`content` as an attachment, if it is a PNG, a JPEG or UTF-8 text of at most 5 MiB.

    Raises:
        TrackerError: If it is too large or of another kind.
    """
    if len(content) > MAX_ATTACHMENT_BYTES:
        msg = f"{name} is larger than 5 MiB."
        raise TrackerError(msg)
    if not any(content.startswith(magic) for magic, _ in _KINDS):
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            msg = f"{name} is not a PNG or JPEG image or a text file."
            raise TrackerError(msg) from None
    return Attachment(name=name[:120], content=content)


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
