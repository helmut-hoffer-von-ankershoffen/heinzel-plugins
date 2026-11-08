"""Setup, health, the Today widget, the app view and the watch job, through the kernel and the installed plugin."""

import json
import tomllib

import pytest
from fastapi.testclient import TestClient
from heinzel import ListWidget
from heinzel.heads import web
from heinzel.kernel import user_config_dir

import heinzel_issues
from heinzel_issues import IssuesService, today, watch

pytestmark = pytest.mark.integration


def config() -> dict:
    return tomllib.loads((user_config_dir() / "config.toml").read_text(encoding="utf-8"))


def test_setup_asks_for_a_beads_folder_and_a_release_clone(hz, hz_prompter, tmp_path):
    board = tmp_path / "board"
    (board / ".beads").mkdir(parents=True)
    hz_prompter.answers += ["beads", str(tmp_path / "nowhere"), str(board), str(tmp_path / "harbor"), "y"]
    result = hz("setup", "issues", json=False)
    assert result.exit_code == 0, result.output
    assert "has no .beads database" in "\n".join(hz_prompter.transcript)
    saved = config()["issues"]
    assert saved["tracker"] == "beads"
    assert saved["beads"]["path"] == str(board)
    assert saved["releases"] == [{"path": str(tmp_path / "harbor")}]


def test_setup_can_turn_it_off(hz, hz_prompter):
    hz_prompter.answers += ["none"]
    assert hz("setup", "issues", json=False).exit_code == 0
    assert config()["issues"] == {"tracker": "none"}


def test_setup_saves_nothing_when_declined(hz, hz_prompter, tmp_path):
    (tmp_path / ".beads").mkdir()
    hz_prompter.answers += ["beads", str(tmp_path), "", "n"]
    assert hz("setup", "issues", json=False).exit_code == 0
    assert "Nothing was saved." in hz_prompter.transcript
    assert not (user_config_dir() / "config.toml").exists()


@pytest.fixture
def board(tmp_path):
    folder = tmp_path / "board"
    (folder / ".beads").mkdir(parents=True)
    return folder


def test_health_today_and_the_view_follow_the_tracker(issues_kernel, board, fake_bd, bd_run):
    kernel = issues_kernel(board, fake_bd)
    service = kernel.resolve(IssuesService)
    assert today(service.overview()) is None  # nothing sent yet
    report = service.submit("The footer clock jumps")
    widget = today(service.overview())
    assert isinstance(widget, ListWidget)
    assert widget.items[0].text == "The footer clock jumps"
    assert widget.items[0].detail == "Received"
    bd_run([fake_bd, "close", report.details.id, "--reason", "Fixed in #7"], board)
    assert today(service.overview()) is None  # all done

    checks = heinzel_issues.tracking(service)
    assert checks[0].status == "up"
    assert checks[0].detail == "beads: 1 reports and requests"

    token = "t" * 43
    ui = TestClient(web.build(kernel, port=8000, token=token, static=None), base_url="http://127.0.0.1:8000")
    views = ui.get("/api/system/ui/views", headers={"Authorization": f"Bearer {token}"}).json()
    view = next(entry for entry in views if entry["id"] == "issues:requests")
    assert view["problem"] is None
    assert view["source"]["path"] == "/issues/list"
    assert set(view["actions"]) == {"setup", "send", "report"}
    send = view["actions"]["send"]
    assert (send["kind"], send["operation"], send["inputs"]) == ("operation", "submit", ["text"])
    assert send["call"] is not None  # system.ui accepted the typed input of a private mutation
    assert any(style.endswith("style.css") for style in view["styles"])
    sent = ui.post(
        "/api/issues/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={"text": "Dark mode loses the focus ring"},
    )
    assert sent.status_code == 200, sent.text
    assert sent.json()["status"] == "Received"


def test_a_broken_tracker_is_down_in_health(issues_kernel, board, tmp_path):
    service = issues_kernel(board, str(tmp_path / "no-bd")).resolve(IssuesService)
    check = heinzel_issues.tracking(service)[0]
    assert check.status == "down"
    assert check.fix == "hz setup issues"


class Notices:
    def __init__(self):
        self.sent = []

    def emit(self, kind, title, body="", **fields):
        self.sent.append(title)
        return object()


def test_the_watch_job_notices_state_changes(issues_kernel, board, fake_bd, bd_run, monkeypatch):
    kernel = issues_kernel(board, fake_bd)
    service = kernel.resolve(IssuesService)
    report = service.submit("The footer clock jumps")
    notices = Notices()
    monkeypatch.setattr(kernel, "provides", lambda _type: True)
    monkeypatch.setattr(kernel, "resolve", lambda _type: notices)
    assert watch(service, kernel)["checked"] is True
    bd_run([fake_bd, "update", report.details.id, "--status", "in_progress"], board)
    result = watch(service, kernel)
    assert result["noticed"] == 1
    assert notices.sent == ["Being worked on: The footer clock jumps"]
    assert json.loads(json.dumps(result))["changes"][0]["status"] == "Being worked on"
