"""Deterministic guards decide what a capture may show; no agent review is involved."""

import socket
from pathlib import Path

import pytest

from heinzel_plugin_tools import privacy

pytestmark = pytest.mark.unit


def test_canonical_text_matches_the_commit_hooks():
    assert privacy.canonical_text("a  \r\nb\t\rc\n\n\n") == "a\nb\nc\n"
    assert privacy.canonical_text("  \n\n") == ""


@pytest.mark.parametrize("relative", ["/etc/passwd", "../outside", "docs/../../outside"])
def test_artifact_paths_cannot_leave_the_owning_project(tmp_path, relative):
    with pytest.raises(privacy.CaptureError, match="inside their owning project"):
        privacy.safe_path(tmp_path, relative)


def test_artifact_paths_refuse_to_follow_a_linked_component(tmp_path):
    (tmp_path / "real").mkdir()
    (tmp_path / "linked").symlink_to(tmp_path / "real")
    with pytest.raises(privacy.CaptureError, match="symbolic links"):
        privacy.safe_path(tmp_path, "linked/image.png")
    assert privacy.safe_path(tmp_path, "real/image.png") == tmp_path.resolve() / "real/image.png"


def test_atomic_text_replaces_a_file_and_refuses_a_linked_destination(tmp_path):
    target = tmp_path / "REVIEW.md"
    target.write_text("old")
    privacy.atomic_text(target, "new")
    assert target.read_text() == "new"
    assert [path.name for path in tmp_path.iterdir()] == ["REVIEW.md"]
    victim = tmp_path / "victim.txt"
    victim.write_text("untouched")
    link = tmp_path / "link.txt"
    link.symlink_to(victim)
    with pytest.raises(privacy.CaptureError, match="symbolic links"):
        privacy.atomic_text(link, "overwrite")
    assert victim.read_text() == "untouched"


@pytest.mark.parametrize(
    "text",
    [
        "Open http://127.0.0.1:8123/?token=abc123def",
        "Authorization: Bearer abcdefghijklmnop",
        "ghp_" + "a" * 36,
        "github_pat_" + "A" * 30,
        "sk-proj-" + "b" * 30,
        "xoxb-" + "1" * 20,
        "AKIA" + "ABCDEFGHIJKLMNOP",
        "AIza" + "c" * 35,
        "eyJhbGciOiJIUzI1.eyJzdWIiOiIxMjM0.SflKxwRJSMeKKF2QT4",
        "-----BEGIN OPENSSH " + "PRIVATE KEY-----",  # split so the repository's own key scanners stay quiet
        "api_" + "key = '" + "Zx81Qp0aBc77" + "Lm12Yt'",
    ],
)
def test_credentials_are_refused(text):
    with pytest.raises(privacy.CaptureError, match="credential"):
        privacy.scan_text(text, terms=[])


@pytest.mark.parametrize("text", ["mira@realmail.de", "/Users/someone/notes", "/home/someone", "C:\\Users\\someone"])
def test_personal_identity_and_private_paths_are_refused(text):
    with pytest.raises(privacy.CaptureError, match="personal identity"):
        privacy.scan_text(text, terms=[])


@pytest.mark.parametrize("text", ["printer.office.lan", "build.corp", "nas.local", "host.tailnet-1.ts.net", "10.1.2.3"])
def test_private_hostnames_and_addresses_are_refused(text):
    with pytest.raises(privacy.CaptureError, match="hostname or IP"):
        privacy.scan_text(text, terms=[])


@pytest.mark.parametrize(
    "text",
    [
        "Hello, Mira Example <mira@example.com>",
        "workstation.tail-example.ts.net at 127.0.0.1 and 192.0.2.10",
        "Version 0.9.54 shipped on 2026-11-22",
        "Token: [session hidden]",
        "/demo-profile/.venv/bin/python on demo-host",
    ],
)
def test_fictional_demonstration_data_passes(text):
    privacy.scan_text(text, terms=[])


@pytest.mark.parametrize(
    "text",
    [
        "fd12:3456:789a::1",
        "fe80::1234%demo0",
        "https://[fe80::1234%25demo0]:8123/",
        "https://[fd12:3456:789a::1]:8123/",
        "2606:4700:4700::1111",
        "FD12:3456:789A:0000:0000:0000:0000:0001",
        "::ffff:10.1.2.3",
    ],
)
def test_nonfictional_ipv6_is_refused(text):
    with pytest.raises(privacy.CaptureError, match="hostname or IP"):
        privacy.scan_text(text, terms=[])


@pytest.mark.parametrize(
    "text",
    [
        "2001:db8::1234",
        "https://[2001:db8::1234]:8123/",
        "2001:DB8:0:0:0:0:0:1",
        "http://[::1]:8123/",
        "::",
        "::1%demo0",
        "2001:db8::1%25demo0",
        "At 10:30:45",
        "aa:bb:cc:dd:ee:ff",
        "label: value",
        "urn:example:harbor",
        "Version 0.9.54",
        "not:an:ipv6:address",
    ],
)
def test_documentation_ipv6_and_non_ip_forms_pass(text):
    privacy.scan_text(text, terms=[])


def test_this_machine_is_refused(monkeypatch):
    monkeypatch.setattr(socket, "gethostname", lambda: "harbor-laptop")
    with pytest.raises(privacy.CaptureError, match="host-specific"):
        privacy.scan_text("Connected from harbor-laptop", terms=[])


def test_confidential_terms_are_matched_like_the_commit_hook_without_naming_them(monkeypatch):
    monkeypatch.setenv("CONFIDENTIAL_TERMS", "Quux Corp\n")
    with pytest.raises(privacy.CaptureError, match="confidential term") as refused:
        privacy.scan_text("A note from quux-corp about tides")
    assert "uux" not in str(refused.value)
    monkeypatch.setenv("CONFIDENTIAL_TERMS", "# none\n")
    monkeypatch.setenv("CONFIDENTIAL_TERMS_FILE", "/nonexistent")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    privacy.scan_text("A note from quux-corp about tides")


class Page:
    url = "http://127.0.0.1:8123/inventory"

    def __init__(self, body="", value="", title="Harbor"):
        self.parts = {"body": body, "input,textarea": value}
        self.page_title = title

    def locator(self, selector):
        page = self

        class Locator:
            def inner_text(self):
                return page.parts[selector]

            def evaluate_all(self, script):
                return page.parts[selector]

        return Locator()

    def title(self):
        return self.page_title


@pytest.mark.parametrize(
    "page",
    [
        Page(body="ok", value="ghp_" + "z" * 36),
        Page(body="ok", title="mira@realmail.de"),
        Page(body="ok"),
    ],
)
def test_page_text_covers_dom_text_input_values_title_and_url(page):
    if page.parts["input,textarea"] == "" and page.page_title == "Harbor":
        page.url = "http://nas.local/inventory"
    with pytest.raises(privacy.CaptureError):
        privacy.scan_text(privacy.page_text(page), terms=[])


def test_the_screenshot_path_never_invokes_an_agent():
    """Taking screenshots needs no AI: no module of the screenshot path names an agent CLI or model API."""
    root = Path(__file__).resolve().parents[1] / "src/heinzel_plugin_tools"
    banned = ("codex", "claude", "anthropic", "openai")
    for name in ("capture.py", "planning.py", "privacy.py", "_presentation.py", "cli.py"):
        source = (root / name).read_text().lower()
        found = [word for word in banned if word in source]
        assert not found, f"{name} mentions {found}"


def test_ci_refuses_to_scan_without_confidential_terms(monkeypatch):
    monkeypatch.delenv("CONFIDENTIAL_TERMS", raising=False)
    monkeypatch.setenv("CONFIDENTIAL_TERMS_FILE", "/nonexistent")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("CONFIDENTIALITY_REQUIRED", raising=False)
    with pytest.raises(privacy.CaptureError, match="No confidential terms are configured"):
        privacy.scan_text("A fictional harbor")
    monkeypatch.setenv("CONFIDENTIALITY_REQUIRED", "false")
    privacy.scan_text("A fictional harbor")


def test_a_local_run_without_terms_warns_once_and_scans_the_rest(monkeypatch, capsys):
    monkeypatch.delenv("CONFIDENTIAL_TERMS", raising=False)
    monkeypatch.setenv("CONFIDENTIAL_TERMS_FILE", "/nonexistent")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(privacy, "_WARNED", [])
    privacy.scan_text("A fictional harbor")
    privacy.scan_text("A fictional harbor")
    assert capsys.readouterr().err.count("no confidential terms are configured") == 1
