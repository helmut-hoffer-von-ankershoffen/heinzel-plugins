"""Pinned tools and release metadata survive a flapping GitHub download edge without trusting unverified bytes."""

import hashlib
import importlib.util
import io
import runpy
import subprocess
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import pytest

from heinzel_plugin_tools import publishing

pytestmark = pytest.mark.unit
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("tools_under_test", SCRIPTS / "tools.py")
assert spec
assert spec.loader
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)
BINARY = b"#!/bin/sh\necho fixture\n"
DIGEST = hashlib.sha256(BINARY).hexdigest()
RELEASE = "https://github.com/example-owner/example-tool/releases/download/v1.2.3/tool.tar.gz"


def gateway_timeout(url):
    msg = f"gateway timeout for {url}"
    raise TimeoutError(msg)


class Response:
    def __init__(self, url, body):
        self.url, self.body = url, body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, size):
        return self.body[:size]


def scripted(monkeypatch, statuses, body=BINARY):
    """publishing.urlopen answering the statuses in order, then the last one forever."""
    hits = []

    def urlopen(url, timeout):
        hits.append(url)
        status = statuses.pop(0) if len(statuses) > 1 else statuses[0]
        if status != 200:
            raise urllib.error.HTTPError(url, status, "scripted", {}, io.BytesIO())
        return Response(url, body)

    monkeypatch.setattr(publishing, "urlopen", urlopen)
    return hits


WHEEL_URL = "https://github.com/example-owner/heinzel/releases/download/v1.0.0/heinzel-1.0.0-py3-none-any.whl"


@pytest.mark.parametrize("script", ["next_app.py", "compose.py"])
def test_both_release_scripts_use_the_one_shared_helper(script):
    assert runpy.run_path(str(SCRIPTS / script))["fetch_bytes"] is publishing.fetch_bytes


def test_release_download_is_retried_after_a_gateway_timeout(monkeypatch):
    hits, delays = scripted(monkeypatch, [504, 200]), []
    final, content = publishing.fetch_bytes(WHEEL_URL, hosts={"github.com"}, timeout=5, limit=1024, sleep=delays.append)
    assert (final, content) == (WHEEL_URL, BINARY)
    assert len(hits) == 2
    assert 0.5 <= delays[0] <= 1.5


def test_persistent_gateway_timeout_gives_up_after_three_tries_and_404_at_once(monkeypatch):
    hits = scripted(monkeypatch, [504])
    with pytest.raises(urllib.error.HTTPError, match="504"):
        publishing.fetch_bytes(WHEEL_URL, hosts={"github.com"}, timeout=5, limit=1024, sleep=lambda _: None)
    assert len(hits) == 3
    hits = scripted(monkeypatch, [404])
    with pytest.raises(urllib.error.HTTPError, match="404"):
        publishing.fetch_bytes(WHEEL_URL, hosts={"github.com"}, timeout=5, limit=1024, sleep=lambda _: None)
    assert len(hits) == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://example.test/heinzel-1.0.0-py3-none-any.whl",
        "http://github.com/o/r/releases/download/v1/x.whl",
        "https://user:secret@github.com/o/r/releases/download/v1/x.whl",
        "https://github.com/o/r/releases/download/v1/x.whl#fragment",
    ],
)
def test_non_allowlisted_endpoints_are_refused_before_any_request(monkeypatch, url):
    monkeypatch.setattr(publishing, "urlopen", lambda *_, **__: pytest.fail("a refused URL reached the network"))
    with pytest.raises(ValueError, match="official HTTPS release endpoints"):
        publishing.fetch_bytes(url, hosts={"github.com"}, timeout=5, limit=1024)


def test_redirect_away_from_https_is_refused(monkeypatch):
    monkeypatch.setattr(publishing, "urlopen", lambda url, timeout: Response("http://mirror.example.test/x", BINARY))
    with pytest.raises(ValueError, match="redirected away from HTTPS"):
        publishing.fetch_bytes(WHEEL_URL, hosts={"github.com"}, timeout=5, limit=1024)


def test_pinned_tool_falls_back_to_the_authenticated_route_and_caches(tmp_path):
    download = tools.Download(RELEASE, DIGEST)
    assert tools.fetch(download, tmp_path, gateway_timeout, fallback=lambda _: BINARY) == BINARY
    assert (tmp_path / DIGEST).read_bytes() == BINARY

    def offline(_):
        pytest.fail("a verified cache entry needs no network")

    assert tools.fetch(download, tmp_path, offline, fallback=offline) == BINARY


def test_fallback_bytes_must_match_the_pin(tmp_path):
    download = tools.Download(RELEASE, DIGEST)
    with pytest.raises(tools.ToolError, match="checksum mismatch"):
        tools.fetch(download, tmp_path, gateway_timeout, fallback=lambda _: b"tampered")
    assert not (tmp_path / DIGEST).exists()


def test_gh_route_downloads_only_github_release_assets(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    commands = []
    monkeypatch.setattr(tools, "on_path", lambda name, *_: Path("/fictional/gh"))

    def gh(command, **kwargs):
        commands.append(command)
        (Path(command[command.index("-D") + 1]) / "tool.tar.gz").write_bytes(BINARY)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(tools.subprocess, "run", gh)
    assert tools.gh_release_get(RELEASE) == BINARY
    assert commands[0][1:6] == ["release", "download", "v1.2.3", "-R", "example-owner/example-tool"]
    for foreign in ("https://example.com/o/r/releases/download/v1/x", RELEASE.replace("v1.2.3", "--repo=x")):
        with pytest.raises(tools.ToolError, match="no authenticated route"):
            tools.gh_release_get(foreign)
    assert len(commands) == 1


def test_hanging_gh_is_a_route_failure(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(tools, "on_path", lambda name, *_: Path("/fictional/gh"))

    def hang(*args, **kwargs):
        raise subprocess.TimeoutExpired("gh", 120)

    monkeypatch.setattr(tools.subprocess, "run", hang)
    with pytest.raises(tools.ToolError, match="timed out"):
        tools.gh_release_get(RELEASE)


def test_hosted_step_without_token_retries_the_direct_url_instead_of_gh(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(tools, "on_path", lambda name, *_: Path("/fictional/gh"))
    monkeypatch.setattr(tools.subprocess, "run", lambda *_, **__: pytest.fail("gh cannot authenticate here"))
    monkeypatch.setattr(tools.time, "sleep", lambda _: None)
    rounds = []

    def flapping(url):
        rounds.append(url)
        if len(rounds) == 1:
            gateway_timeout(url)
        return BINARY

    assert tools.fetch(tools.Download(RELEASE, DIGEST), tmp_path, flapping) == BINARY
    assert len(rounds) == 2
