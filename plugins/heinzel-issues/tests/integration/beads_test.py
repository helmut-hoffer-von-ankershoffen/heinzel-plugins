"""The Beads connector through CLI and API heads, with a stand-in `bd` that answers in Beads' JSON shapes."""

import json

import pytest
from heinzel import CallIdentity, Config, CurrentUser, Principal
from heinzel.heads.cli import build
from typer.testing import CliRunner

import heinzel_issues
from heinzel_issues import IssuesService, TrackerError
from heinzel_issues._beads import reporter
from heinzel_issues._identity import authenticated

pytestmark = pytest.mark.integration


def test_authenticated_creators_are_separated_and_only_the_creator_closes(issues_kernel, folder, fake_bd, bd_run):
    kernel = issues_kernel(folder, fake_bd)
    service = kernel.resolve(IssuesService)
    current = kernel.resolve(CurrentUser)
    owner = current.owner()
    other = Principal("u-" + "a" * 32)

    def identity(principal):
        return CallIdentity(principal, "web-session", "fixture", "hz-web", frozenset({"private:read", "private:write"}))

    with current.using(identity(owner)), authenticated(current):
        own = service.submit("First fictional report")
        assert own.can_close
    read_only = CallIdentity(owner, "web-device", "fixture", "hz-web", frozenset({"private:read"}))
    with current.using(read_only), authenticated(current):
        assert not service.get(own.details.id).can_close
        with pytest.raises(TrackerError, match="cannot close"):
            service.close(own.details.id)
        with pytest.raises(TrackerError, match="cannot submit"):
            service.submit("Another fictional report")
    with current.using(identity(other)), authenticated(current):
        assert service.overview().reports == []
        with pytest.raises(TrackerError, match="There is no item"):
            service.get(own.details.id)
        with pytest.raises(TrackerError, match="There is no item"):
            service.close(own.details.id)
        theirs = service.submit("Second fictional report")
    with current.using(identity(owner)), authenticated(current):
        assert [r.details.id for r in service.overview().reports] == [own.details.id]
        with pytest.raises(TrackerError, match="There is no item"):
            service.close(theirs.details.id)
        closed = service.close(own.details.id)
        assert closed.state == "done" and not closed.can_close
    assert json.loads(bd_run([fake_bd, "show", theirs.details.id, "--json"], folder))[0]["status"] == "open"


def test_owner_can_read_legacy_report_but_cannot_close_it(issues_kernel, folder, fake_bd, bd_run):
    kernel = issues_kernel(folder, fake_bd)
    service = kernel.resolve(IssuesService)
    current = kernel.resolve(CurrentUser)
    created = json.loads(
        bd_run(
            [fake_bd, "create", "--title=Legacy fixture", "--labels=heinzel-issues", f"--actor={reporter()}", "--json"],
            folder,
        )
    )
    task_id = created["id"] if isinstance(created, dict) else created[0]["id"]
    with current.local("cli"), authenticated(current):
        assert not service.get(task_id).can_close
        with pytest.raises(TrackerError, match="There is no item"):
            service.close(task_id)


def test_close_is_available_through_the_authenticated_cli(issues_kernel, folder, fake_bd):
    cli = build(issues_kernel(folder, fake_bd))
    sent = CliRunner().invoke(cli, ["issues", "submit", "A fictional report", "--json"])
    assert sent.exit_code == 0, sent.output
    task_id = json.loads(sent.stdout)["details"]["id"]
    closed = CliRunner().invoke(cli, ["issues", "close", task_id, "--json"])
    assert closed.exit_code == 0, closed.output
    assert json.loads(closed.stdout)["state"] == "done"


@pytest.fixture
def folder(tmp_path):
    board = tmp_path / "board"
    (board / ".beads").mkdir(parents=True)
    return board


def test_submit_work_finish_and_release(issues_kernel, folder, fake_bd, journey, tmp_path):
    journey(issues_kernel(folder, fake_bd), folder, fake_bd, tmp_path)


def test_option_like_text_other_work_and_other_people_stay_out(issues_kernel, folder, fake_bd, probes):
    probes(issues_kernel(folder, fake_bd), folder, fake_bd)


def test_a_refusal_is_explained(issues_kernel, folder, fake_bd):
    result = CliRunner().invoke(build(issues_kernel(folder, fake_bd)), ["issues", "show", "demo-404"])
    assert result.exit_code != 0
    assert "There is no item demo-404." in result.output


def test_a_malformed_id_never_reaches_the_tracker(issues_kernel, folder, fake_bd):
    result = CliRunner().invoke(build(issues_kernel(folder, fake_bd)), ["issues", "show", "--", "--all"])
    assert "is not an item id" in result.output


def test_a_missing_program_is_explained(issues_kernel, folder, tmp_path):
    result = json.loads(
        CliRunner().invoke(build(issues_kernel(folder, str(tmp_path / "no-bd"))), ["issues", "list", "--json"]).stdout
    )
    assert "is not installed" in result["problem"]


def test_a_folder_without_beads_is_explained(make_kernel, tmp_path):
    settings = {"issues": {"tracker": "beads", "beads": {"path": str(tmp_path)}}}
    kernel = make_kernel(builtins=True, config=Config(files=(), data=settings), issues=heinzel_issues.module)
    result = json.loads(CliRunner().invoke(build(kernel), ["issues", "list", "--json"]).stdout)
    assert not result["ready"]
    assert "has no .beads database" in result["problem"]
    assert result["fix"] == "hz setup issues"


def test_off_by_default_everywhere(make_kernel):
    kernel = make_kernel(builtins=True, issues=heinzel_issues.module)
    result = CliRunner().invoke(build(kernel), ["issues", "list"])
    assert result.exit_code == 0
    assert "Issue tracking is not set up. Run hz setup issues." in result.stdout
    sent = CliRunner().invoke(build(kernel), ["issues", "submit", "hello"])
    assert sent.exit_code != 0
    assert "not set up" in sent.output
    doctor = json.loads(CliRunner().invoke(build(kernel), ["system", "doctor", "--json"]).stdout)
    assert {"name": "tracker", "status": "up", "detail": "off; set it up on the Issues page", "fix": ""} in doctor[
        "checks"
    ]["issues"]


def test_close_rejects_prefix_and_duplicate_rows(issues_kernel, folder, fake_bd, monkeypatch):
    kernel = issues_kernel(folder, fake_bd)
    service = kernel.resolve(IssuesService)
    current = kernel.resolve(CurrentUser)
    with current.local("cli"), authenticated(current):
        report = service.submit("Fictional report")
        tracker = service.tracker()
        row = tracker.owned(report.details.id)
        monkeypatch.setattr(tracker, "rows", lambda _args: [row])
        with pytest.raises(TrackerError, match="There is no item"):
            tracker.close_own(report.details.id[:-1])
        monkeypatch.setattr(tracker, "rows", lambda _args: [row, row])
        with pytest.raises(TrackerError, match="There is no item"):
            tracker.close_own(report.details.id)


def test_legacy_row_cannot_confirm_new_creator(issues_kernel, folder, fake_bd, bd_run):
    kernel = issues_kernel(folder, fake_bd)
    service = kernel.resolve(IssuesService)
    current = kernel.resolve(CurrentUser)
    created = json.loads(
        bd_run(
            [fake_bd, "create", "--title=Legacy fixture", "--labels=heinzel-issues", f"--actor={reporter()}", "--json"],
            folder,
        )
    )
    task_id = created["id"] if isinstance(created, dict) else created[0]["id"]
    with current.local("cli"), authenticated(current):
        with pytest.raises(TrackerError, match="confirm the report owner"):
            service.tracker().created(task_id, current.context().principal.id)
