"""Mounted Gmail consent against registered Google and a fake existing connection."""

import json
import os
import subprocess
import threading
from pathlib import Path
from typing import ClassVar
from urllib.parse import parse_qs, urlsplit

import nodejs_wheel
import pytest
import uvicorn
from heinzel.heads import web

from tests.support.installed_browser_support import run_installed_browser

pytestmark = pytest.mark.e2e


@pytest.mark.timeout(180)
@pytest.mark.parametrize("engine", ["chromium", "webkit"])
def test_mounted_google_mail_review(tmp_path, engine):
    run_installed_browser(Path(__file__), "_exercise_mounted_google_mail_review", tmp_path, engine)


def _exercise_mounted_google_mail_review(boot, tmp_path, monkeypatch, engine):
    from tests.support.connected_mail_support import _setup_mail

    package = Path(os.environ["HZ_TEST_BROWSER_PACKAGE"])
    browser_cache = Path(os.environ["HZ_TEST_BROWSER_CACHE"])
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(browser_cache))
    kernel, calls = _setup_mail(boot, tmp_path, monkeypatch)

    class Server(uvicorn.Server):
        instances: ClassVar[list[uvicorn.Server]] = []

        def __init__(self, config):
            super().__init__(config)
            self.instances.append(self)

    monkeypatch.setattr(uvicorn, "Server", Server)
    ready = threading.Event()
    urls = []

    def announce(url):
        urls.append(url)
        ready.set()

    server = threading.Thread(target=lambda: web.serve(kernel, port=0, browser=False, announce=announce), daemon=True)
    server.start()
    try:
        assert ready.wait(15)
        token = parse_qs(urlsplit(urls[0]).fragment).get("token", [""])[0]
        assert token
        result = subprocess.run(
            [
                str(Path(nodejs_wheel.__file__).parent / "bin" / "node"),
                str(Path(__file__).with_name("google_mail_review.mjs")),
                urls[0],
                engine,
                str(package),
            ],
            cwd=package.parent,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert result.returncode == 0, (result.stdout + result.stderr).replace(token, "<redacted-session>")
        assert json.loads(result.stdout.strip().splitlines()[-1])["accepted"] is True
        assert calls == [
            ["gmail", "users", "labels", "list"],
            ["gmail", "users", "messages", "list"],
            ["gmail", "users", "messages", "get"],
        ]
    finally:
        if Server.instances:
            Server.instances[0].should_exit = True
        server.join(15)
        assert not server.is_alive()
