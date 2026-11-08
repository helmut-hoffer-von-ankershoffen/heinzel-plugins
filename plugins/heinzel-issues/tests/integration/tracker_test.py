"""Beads through the `Tracker` contract (ADR 0141): writes name their actor, claims are atomic, nothing is bound."""

import json
import logging
from datetime import UTC, datetime, timedelta

import pytest
from heinzel import Config, HeinzelError, Issue, Module, Tracker, Window
from heinzel.heads.cli import build
from typer.testing import CliRunner

import heinzel_issues
from heinzel_issues import BeadsBoard, BeadsSettings, IssuesService

pytestmark = pytest.mark.integration


@pytest.fixture
def board(tmp_path):
    folder = tmp_path / "board"
    (folder / ".beads").mkdir(parents=True)
    return folder


@pytest.fixture
def tracker(board, fake_bd) -> Tracker:
    return BeadsBoard(BeadsSettings(path=board, bd=fake_bd))


def test_an_issue_round_trips_create_claim_note_attach_and_close(tracker, board):
    issue = tracker.create("heinzel-issues", "Crash on save", "It crashes.", "mira", ["owner-ask"])
    assert (issue.state, issue.reporter, issue.labels) == ("open", "mira", ["heinzel-issues", "owner-ask"])
    assert tracker.claim(issue.key, "builder").assignee == "builder"
    with pytest.raises(HeinzelError, match="already claimed by builder"):
        tracker.claim(issue.key, "reviewer")
    tracker.note(issue.key, "Found the cause.", "builder")
    file = tracker.attach(issue.key, "screen.png", b"\x89PNG\r\n\x1a\n", "image/png", "builder")
    assert (file.size, file.ref) == (8, f".beads/attachments/{issue.key}/screen.png")
    assert (board / file.ref).read_bytes().startswith(b"\x89PNG")
    closed = tracker.close(issue.key, "builder", "Fixed in #7")
    assert closed.state == "closed"
    assert closed.closed_at is not None
    assert [a.name for a in closed.attachments] == ["screen.png"]

    window = Window(since=datetime.now(UTC) - timedelta(hours=1), until=datetime.now(UTC) + timedelta(hours=1))
    assert [i.key for i in tracker.issues_updated("heinzel-issues", window)] == [issue.key]
    assert tracker.issues_updated("elsewhere", window) == []


def test_an_unknown_or_malformed_key_is_refused(tracker):
    with pytest.raises(HeinzelError, match="no issue found"):
        tracker.claim("demo-9", "builder")
    with pytest.raises(HeinzelError, match="not a Beads item id"):
        tracker.close("../etc", "builder", "no")


def test_installing_issues_binds_and_replaces_no_tracker(issues_kernel, board, fake_bd):
    kernel = issues_kernel(board, fake_bd)
    result = CliRunner().invoke(build(kernel), ["system", "capability", "list", "--json"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert [a for a in report["adapters"] if a["module"] == "issues"] == []
    assert [u for u in report["uses"] if u["requester"].startswith("issues")] == []


class Hub:
    """A read-only tracker adapter like GitHub's or Atlassian's."""

    def issues_updated(self, project: str, window: Window) -> list[Issue]:
        return []


def test_another_tracker_stays_bound_automatically_with_issues_installed(make_kernel, tmp_path):
    hub = Module("hub", "Test-only read-only tracker adapter.")
    hub.provides("tracker", modes={"read"}, hosts=["hub.invalid"])(Hub)
    settings = {"hz": {"state_dir": str(tmp_path / "state")}}
    kernel = make_kernel(builtins=True, config=Config(files=(), data=settings), hub=hub, issues=heinzel_issues.module)
    result = CliRunner().invoke(build(kernel), ["system", "capability", "list", "--json"])
    assert result.exit_code == 0, result.output
    tracker = next(c for c in json.loads(result.stdout)["capabilities"] if c["name"] == "tracker")
    assert tracker["bound"] == "hub"
    assert [a["adapter"] for a in json.loads(result.stdout)["adapters"] if a["capability"] == "tracker"] == ["hub"]


def test_submit_goes_through_the_tracker_and_logs_without_the_text(issues_kernel, board, fake_bd, caplog):
    kernel = issues_kernel(board, fake_bd)
    caplog.set_level(logging.INFO, logger="heinzel_issues")
    sent = CliRunner().invoke(build(kernel), ["issues", "submit", "Secret words in the footer", "--json"])
    assert sent.exit_code == 0, sent.output
    task_id = json.loads(sent.stdout)["details"]["id"]
    row = json.loads((board / ".beads" / "fake.json").read_text())[0]
    assert (row["id"], row["labels"]) == (task_id, ["heinzel-issues"])
    assert row["created_by"]  # the actor Beads recorded
    events = [(r.event, getattr(r, "outcome", None)) for r in caplog.records if hasattr(r, "event")]
    assert events == [("issues.submit.start", None), ("issues.submit.outcome", "ok")]
    assert caplog.records[-1].tracker == "beads"
    assert caplog.records[-1].duration_ms >= 0
    assert "Secret" not in caplog.text
    assert all("Secret" not in json.dumps(r.__dict__, default=str) for r in caplog.records)


def test_a_failed_submit_and_watch_log_their_outcome(issues_kernel, board, tmp_path, caplog):
    service = issues_kernel(board, str(tmp_path / "no-bd")).resolve(IssuesService)
    caplog.set_level(logging.INFO, logger="heinzel_issues")
    with pytest.raises(heinzel_issues.TrackerError):
        service.submit("Secret words")
    with pytest.raises(heinzel_issues.TrackerError):
        service.watch(None)
    outcomes = [(r.event, r.outcome) for r in caplog.records if r.event.endswith(".outcome")]
    assert outcomes == [("issues.submit.outcome", "failed"), ("issues.watch.outcome", "failed")]
    assert "Secret" not in caplog.text
