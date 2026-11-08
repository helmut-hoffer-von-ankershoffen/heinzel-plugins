"""Pinned tools and release metadata survive a flapping GitHub download edge without trusting unverified bytes."""

import hashlib
import importlib.util
import runpy
import subprocess
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

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


class LoopbackServer(ThreadingHTTPServer):
    """Binds without asking DNS for a display name, which stalls on macOS runners."""

    def server_bind(self):
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()
        self.server_name, self.server_port = "127.0.0.1", self.server_address[1]


@pytest.fixture
def release():
    servers = []

    def start(statuses, body=BINARY):
        hits = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.path)
                status = statuses.pop(0) if len(statuses) > 1 else statuses[0]
                self.send_response(status)
                self.end_headers()
                if status == 200:
                    self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = LoopbackServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}/asset", hits

    yield start
    for server in servers:
        server.shutdown()
        server.server_close()


def gateway_timeout(url):
    msg = f"gateway timeout for {url}"
    raise TimeoutError(msg)


@pytest.mark.parametrize("script", ["next_app.py", "compose.py"])
def test_release_metadata_is_retried_after_a_gateway_timeout(release, script):
    fetch_bytes = runpy.run_path(str(SCRIPTS / script))["fetch_bytes"]
    url, hits = release([504, 200])
    delays = []
    final, content = fetch_bytes(url, timeout=5, limit=1024, sleep=delays.append)
    assert (final, content) == (url, BINARY)
    assert len(hits) == 2
    assert 0.5 <= delays[0] <= 1.5


@pytest.mark.parametrize("script", ["next_app.py", "compose.py"])
def test_persistent_gateway_timeout_gives_up_after_three_tries_and_404_at_once(release, script):
    fetch_bytes = runpy.run_path(str(SCRIPTS / script))["fetch_bytes"]
    url, hits = release([504])
    with pytest.raises(urllib.error.HTTPError, match="504"):
        fetch_bytes(url, timeout=5, limit=1024, sleep=lambda _: None)
    assert len(hits) == 3
    url, hits = release([404])
    with pytest.raises(urllib.error.HTTPError, match="404"):
        fetch_bytes(url, timeout=5, limit=1024, sleep=lambda _: None)
    assert len(hits) == 1


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
    monkeypatch.setattr(tools, "on_path", lambda name, *_: Path("/fictional/gh"))

    def hang(*args, **kwargs):
        raise subprocess.TimeoutExpired("gh", 120)

    monkeypatch.setattr(tools.subprocess, "run", hang)
    with pytest.raises(tools.ToolError, match="timed out"):
        tools.gh_release_get(RELEASE)
