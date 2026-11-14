"""State mapping, release resolution and change notices, with fixtures instead of a tracker or git."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from heinzel import Config, HeinzelError, Settings
from heinzel.kernel import user_config_dir

from heinzel_issues import (
    NOT_SET_UP,
    IssuesService,
    IssuesSettings,
    Release,
    ReleaseResolver,
    ReleaseSource,
    Task,
    TaskState,
    TaskTracker,
    TrackerError,
    released_text,
    state_of,
)
from heinzel_issues._beads import BeadsSettings
from heinzel_issues._releases import references
from heinzel_issues._service import history, read_attachment, title_of, upload

pytestmark = pytest.mark.unit

T0 = datetime(2026, 11, 7, 9, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("status", "state"),
    [
        ("open", TaskState.RECEIVED),
        ("deferred", TaskState.RECEIVED),
        ("in_progress", TaskState.WORKING),
        ("blocked", TaskState.WORKING),
        ("closed", TaskState.DONE),
        ("something_custom", TaskState.RECEIVED),
    ],
)
def test_beads_statuses_become_three_plain_states(status, state):
    assert state_of(status) is state


CORE = ReleaseSource(path=Path("/clones/harbor"), names=["core"])
PLUGINS = ReleaseSource(path=Path("/clones/harbor-plugins"), names=["plugins"])


@pytest.mark.parametrize(
    ("text", "found"),
    [
        ("Fixed in #562", [(0, 562)]),
        ("gh-562", [(0, 562)]),
        ("PR #12 and plugins #38", [(0, 12), (1, 38)]),
        ("https://github.com/acme/harbor-plugins/pull/40", [(1, 40)]),
        ("step #2 of the recipe", []),
        ("#5, #5 again", [(0, 5)]),
        ("", []),
    ],
)
def test_pull_request_references_are_read_from_tracker_notes(text, found):
    assert references(text, [CORE, PLUGINS]) == found


def test_no_release_source_means_no_references():
    assert references("Fixed in #562", []) == []


class FakeGit:
    """Answers `git log --grep` and `git tag --contains` like a clone with a few squash merges and tags."""

    def __init__(self, merged, tags):
        self.merged = merged  # number -> sha
        self.tags = tags  # sha -> lines "tag date"
        self.calls = 0

    def __call__(self, path, args):
        self.calls += 1
        if args[0] == "log":
            number = int(next(a for a in args if a.startswith("--grep="))[len("--grep=(#") : -1])
            return self.merged.get(number, "") + "\n"
        if args[0] == "tag":
            return "\n".join(self.tags.get(args[2], [])) + "\n"
        return None


def resolver(git):
    return ReleaseResolver([CORE, PLUGINS], git=git)


def test_release_is_the_first_matching_tag_that_contains_the_merge():
    git = FakeGit({562: "abc"}, {"abc": ["v0.9.27 2026-11-07T10:00:00+01:00", "v0.9.28 2026-11-08T10:00:00+01:00"]})
    assert resolver(git).release("Fixed in #562") == Release(version="0.9.27", date=date(2026, 11, 7))


def test_unmerged_or_untagged_work_has_no_release():
    git = FakeGit({562: "abc"}, {})
    assert resolver(git).release("Fixed in #562") is None
    assert resolver(git).release("Fixed in #999") is None
    assert resolver(git).release("no number here") is None


def test_every_pull_request_must_ship_and_the_latest_release_counts():
    git = FakeGit(
        {1: "a", 2: "b"},
        {"a": ["v0.9.20 2026-11-01T00:00:00+00:00"], "b": ["v0.9.27 2026-11-07T00:00:00+00:00"]},
    )
    assert resolver(git).release("#1 and #2").version == "0.9.27"
    assert resolver(FakeGit({1: "a"}, {"a": ["v0.9.20 2026-11-01T00:00:00+00:00"]})).release("#1 and #2") is None


def test_tags_without_a_version_are_skipped_and_lookups_are_cached():
    git = FakeGit({7: "c"}, {"c": ["nightly 2026-11-01T00:00:00+00:00", "harbor-v1.2.3 2026-11-02T00:00:00+00:00"]})
    found = resolver(git)
    assert found.release("#7").version == "1.2.3"
    calls = git.calls
    found.release("#7")
    assert git.calls == calls


def test_released_text_names_version_and_day():
    assert released_text(Release(version="0.9.27", date=date(2026, 11, 7))) == "Released in 0.9.27 on 7 Nov 2026"


def test_a_title_is_the_first_line_shortened():
    assert title_of("\n  The clock is wrong  \nmore") == "The clock is wrong"
    long = title_of("x" * 200)
    assert len(long) == 80
    assert long.endswith("…")


def test_attachments_are_images_or_text(tmp_path):
    png = tmp_path / "shot.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\nrest")
    assert read_attachment(png).name == "shot.png"
    binary = tmp_path / "blob.bin"
    binary.write_bytes(b"\xff\xfe\x00\x81")
    with pytest.raises(TrackerError, match="not a PNG"):
        read_attachment(binary)
    with pytest.raises(TrackerError, match="not a file"):
        read_attachment(tmp_path)


class FakeTracker:
    name = "fake"

    def __init__(self):
        self.tasks = {}

    def submit(self, title, body, attachments=()):
        task = Task(
            id=f"t-{len(self.tasks) + 1}",
            title=title,
            body=body,
            state=TaskState.RECEIVED,
            status="open",
            created_at=T0,
            updated_at=T0,
        )
        self.tasks[task.id] = task
        return task

    def list(self):
        return list(self.tasks.values())

    def get(self, task_id):
        return self.tasks[task_id]

    def changes(self, since):
        return [task for task in self.tasks.values() if since is None or task.updated_at > since]

    def move(self, task_id, state, references="", at=None):
        task = self.tasks[task_id]
        self.tasks[task_id] = task.model_copy(
            update={
                "state": state,
                "status": state.value,
                "references": references,
                "updated_at": at or task.updated_at,
            }
        )


class Notices:
    def __init__(self):
        self.sent = []

    def emit(self, kind, title, body="", **fields):
        self.sent.append((title, fields["key"]))
        return object()


def service(tmp_path, tracker, git=None, **settings):
    found = IssuesService(IssuesSettings(tracker="fake", **settings), Settings(state_dir=tmp_path))
    found.factories = lambda: {"fake": lambda _table: tracker}
    found.resolver = ReleaseResolver([CORE], git=git or FakeGit({}, {}))
    return found


def test_the_fake_tracker_meets_the_contract():
    assert isinstance(FakeTracker(), TaskTracker)


def test_off_by_default_says_it_is_not_set_up(tmp_path):
    result = IssuesService(IssuesSettings(), Settings(state_dir=tmp_path)).overview()
    assert not result.ready
    assert result.problem == NOT_SET_UP
    assert result.fix == "hz setup issues"


def test_an_unknown_tracker_is_reported_not_raised(tmp_path):
    found = IssuesService(IssuesSettings(tracker="nowhere"), Settings(state_dir=tmp_path))
    found.factories = dict
    assert "not installed" in str(found.overview().problem)


def test_submit_cleans_text_and_reports_received(tmp_path):
    tracker = FakeTracker()
    report = service(tmp_path, tracker).submit("The clock is wrong​\nIt shows Tokyo.")
    assert report.status == "Received"
    assert report.title == "The clock is wrong"
    assert report.details.id == "t-1"
    with pytest.raises(TrackerError, match="Say what happened"):
        service(tmp_path, tracker).submit("   ")


def test_done_work_shows_its_release(tmp_path):
    tracker = FakeTracker()
    tracker.submit("Clock", "Clock")
    tracker.move("t-1", TaskState.DONE, "Fixed in #562")
    git = FakeGit({562: "abc"}, {"abc": ["v0.9.27 2026-11-07T10:00:00+01:00"]})
    report = service(tmp_path, tracker, git).overview().reports[0]
    assert report.status == "Released in 0.9.27 on 7 Nov 2026"
    assert report.details.pull_requests[0].number == 562


def test_the_watch_is_quiet_first_then_notices_each_new_state_and_the_release(tmp_path):
    tracker = FakeTracker()
    tracker.submit("Clock", "Clock")
    git = FakeGit({}, {})
    issues = service(tmp_path, tracker, git)
    notices = Notices()
    issues.clock = lambda: T0
    assert issues.watch(notices).changes == []
    tracker.move("t-1", TaskState.WORKING, at=T0 + timedelta(minutes=1))
    issues.clock = lambda: T0 + timedelta(minutes=5)
    issues.watch(notices)
    tracker.move("t-1", TaskState.DONE, "Fixed in #562", at=T0 + timedelta(minutes=6))
    issues.clock = lambda: T0 + timedelta(minutes=10)
    issues.watch(notices)
    git.merged[562] = "abc"
    git.tags["abc"] = ["v0.9.27 2026-11-07T10:00:00+01:00"]
    issues.resolver = ReleaseResolver([CORE], git=git)
    issues.clock = lambda: T0 + timedelta(hours=1)
    issues.watch(notices)
    issues.watch(notices)
    assert notices.sent == [
        ("Being worked on: Clock", "issues:t-1:working"),
        ("Done: Clock", "issues:t-1:done"),
        ("Released in 0.9.27: Clock", "issues:t-1:release:0.9.27"),
    ]


def test_the_watch_does_nothing_while_off(tmp_path):
    assert not IssuesService(IssuesSettings(), Settings(state_dir=tmp_path)).watch(Notices()).checked


def write_config(text: str, load: bool = True) -> Config | None:
    file = user_config_dir() / "config.toml"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")
    return Config.load() if load else None


def test_settings_saved_by_another_program_are_followed_without_a_restart(tmp_path):
    config = write_config("[hz]\n")
    found = IssuesService(IssuesSettings(), Settings(state_dir=tmp_path), config)
    assert not found.overview().ready
    assert not found.watch(Notices()).checked
    write_config(f'[issues]\ntracker = "beads"\n[issues.beads]\npath = "{tmp_path}"\n')
    result = found.overview()  # the daemon and the app each read the files again
    assert found.enabled
    assert result.folder == str(tmp_path)
    assert "has no .beads database" in str(result.problem)
    assert "hz " not in str(result.problem)  # the app shows this; it names no terminal command

    write_config("[issues]\ntracker = 3\n[[[", load=False)  # a half-written file leaves the settings as they were
    found.refresh()
    assert found.settings.tracker == "beads"
    write_config('[issues]\ntracker = ["no"]\n')
    found.refresh()
    assert found.settings.tracker == "beads"


class Editor:
    def __init__(self, fail=False):
        self.written = {}
        self.fail = fail

    def write(self, key, value, scope="user"):
        if self.fail:
            raise HeinzelError("A higher-priority source sets it")
        self.written[key] = value
        return Path("config.toml")


def test_connect_checks_the_folder_before_it_saves_anything(tmp_path, fake_bd):
    found = IssuesService(IssuesSettings(beads=BeadsSettings(bd=fake_bd)), Settings(state_dir=tmp_path))
    editor = Editor()
    board = tmp_path / "board"
    (board / ".beads").mkdir(parents=True)
    clone = tmp_path / "harbor"
    clone.mkdir()
    refusals = [
        (("relative/board",), "must be a full path"),
        ((str(tmp_path / "nowhere"),), "has no Beads database"),
        ((str(board), "Not A Label"), "That label cannot be used"),
        ((str(board), "", "clones/harbor"), "A release clone must be a full path"),
        ((str(board), "", str(tmp_path / "gone")), "is not a folder"),
    ]
    for arguments, words in refusals:
        with pytest.raises(TrackerError, match=words):
            found.connect(editor, *arguments)
    assert editor.written == {}
    assert not found.enabled

    with pytest.raises(TrackerError, match="higher-priority"):
        found.connect(Editor(fail=True), str(board))
    assert not found.enabled

    result = found.connect(editor, f" {board} ", "owner-ask, intake", f"{clone}")
    assert result.ready
    assert editor.written["issues.tracker"] == "beads"
    assert editor.written["issues.beads"]["path"] == str(board)
    assert editor.written["issues.beads"]["extra_labels"] == ["owner-ask", "intake"]
    assert editor.written["issues.releases"] == [{"path": str(clone), "names": [], "ref": "origin/main", "tags": "v*"}]
    assert found.settings.beads.labels == ["heinzel-issues", "owner-ask", "intake"]

    again = Editor()
    found.connect(again, str(board), "owner-ask")  # the labels are the whole list; empty clones keep what is set
    assert again.written["issues.beads"]["extra_labels"] == ["owner-ask"]
    overview = found.overview()
    assert (overview.labels, overview.extra_labels) == (["heinzel-issues", "owner-ask"], ["owner-ask"])
    assert overview.sender  # the login name a report is stored under, shown before sending
    assert "issues.releases" not in again.written
    assert [source.path for source in found.settings.releases] == [clone]
    found.connect(again, str(board))  # an empty field clears the labels
    assert again.written["issues.beads"]["extra_labels"] == []
    assert found.settings.beads.labels == ["heinzel-issues"]


def test_a_broken_bd_refuses_connect(tmp_path):
    (tmp_path / ".beads").mkdir()
    found = IssuesService(IssuesSettings(beads=BeadsSettings(bd=str(tmp_path / "no-bd"))), Settings(state_dir=tmp_path))
    editor = Editor()
    with pytest.raises(TrackerError, match="not installed"):
        found.connect(editor, str(tmp_path))
    assert editor.written == {}


def test_labels_are_checked_and_the_issues_label_comes_first():
    assert BeadsSettings(extra_labels=["owner-ask", "heinzel-issues"]).labels == ["heinzel-issues", "owner-ask"]
    with pytest.raises(ValueError, match="a label is lowercase"):
        BeadsSettings(extra_labels=["Owner Ask"])


def test_history_is_the_plain_states_in_order():
    task = Task(id="a", title="t", state=TaskState.RECEIVED, status="open", created_at=T0, updated_at=T0)
    assert [(step.label, step.at) for step in history(task, None)] == [("Sent", T0)]
    working = task.model_copy(update={"state": TaskState.WORKING})
    assert [(step.label, step.at) for step in history(working, None)] == [("Sent", T0), ("Being worked on", None)]
    later = T0 + timedelta(hours=1)
    done = task.model_copy(update={"state": TaskState.DONE, "started_at": later, "closed_at": later})
    steps = history(done, Release(version="0.9.27", date=date(2026, 11, 8)))
    assert [step.label for step in steps] == ["Sent", "Being worked on", "Done", "Released in 0.9.27"]
    assert steps[-1].at == datetime(2026, 11, 8, tzinfo=UTC)


def test_a_file_from_the_app_follows_the_rules_of_a_file_from_disk():
    assert upload("../shots/shot.png", "iVBORw0KGgpmYWtl").name == "shot.png"
    assert upload(" ", "aGVsbG8=").name == "attachment"
    with pytest.raises(TrackerError, match="did not arrive whole"):
        upload("shot.png", "not base64!")
    with pytest.raises(TrackerError, match="not a PNG or JPEG image or a text file"):
        upload("blob.bin", "//79/A==")
    with pytest.raises(TrackerError, match="larger than 5 MiB"):
        upload("big.txt", "QUFB" * (5 * 1024 * 1024 // 3 + 1))
