"""The same journey against a real temporary Beads database, when `bd` is installed."""

import pytest
from heinzel import HeinzelError

from heinzel_issues import BeadsBoard, BeadsSettings

pytestmark = pytest.mark.e2e


def test_submit_work_finish_and_release_with_real_beads(issues_kernel, real_bd, bd_run, journey, tmp_path):
    folder = tmp_path / "board"
    folder.mkdir()
    bd_run(["git", "init", "-q"], folder)
    bd_run([real_bd, "init", "--prefix", "demo", "--stealth", "--skip-agents"], folder)
    journey(issues_kernel(folder, real_bd), folder, real_bd, tmp_path)


def test_the_tracker_contract_records_actors_and_refuses_a_held_claim_with_real_beads(real_bd, bd_run, tmp_path):
    folder = tmp_path / "board"
    folder.mkdir()
    bd_run(["git", "init", "-q"], folder)
    bd_run([real_bd, "init", "--prefix", "demo", "--stealth", "--skip-agents"], folder)
    tracker = BeadsBoard(BeadsSettings(path=folder, bd=real_bd))
    issue = tracker.create("heinzel-issues", "Crash on save", "It crashes.", "mira", [])
    assert (issue.state, issue.reporter, issue.labels) == ("open", "mira", ["heinzel-issues"])
    assert tracker.claim(issue.key, "builder").assignee == "builder"
    with pytest.raises(HeinzelError):
        tracker.claim(issue.key, "reviewer")
    tracker.attach(issue.key, "screen.png", b"\x89PNG\r\n\x1a\n", "image/png", "builder")
    closed = tracker.close(issue.key, "builder", "Fixed in #7")
    assert (closed.state, [a.size for a in closed.attachments]) == ("closed", [8])
    assert closed.assignee == "builder"
