"""Mounted owner-only source review with a fake native file and no Google process."""

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

from heinzel_google import Gws, Process
from tests.support.installed_browser_support import run_installed_browser

pytestmark = pytest.mark.e2e


@pytest.mark.timeout(120)
@pytest.mark.parametrize("engine", ["chromium", "webkit"])
def test_mounted_source_review(tmp_path, engine):
    run_installed_browser(Path(__file__), "_exercise_mounted_source_review", tmp_path, engine)


def _exercise_mounted_source_review(boot, tmp_path, monkeypatch, engine):
    package = Path(os.environ["HZ_TEST_BROWSER_PACKAGE"])
    monkeypatch.setenv("HOME", str(tmp_path))
    executable = tmp_path / ("selected-" + "long-name-" * 12 + "gws")
    executable.write_bytes(b"\xcf\xfa\xed\xfe" + b"fake native file")
    executable.chmod(0o700)
    monkeypatch.setenv("HZ_GOOGLE__GWS_PATH", str(executable))
    calls = []

    def fake_run(_self, _executable, arguments, _timeout):
        calls.append(list(arguments))
        return Process(0, b"gws 0.22.5" if list(arguments) == ["--version"] else b"{}")

    monkeypatch.setattr(Gws, "run", fake_run)
    kernel = boot()
    assert any(record.qualname == "google" for record in kernel.modules)

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

    thread = threading.Thread(target=lambda: web.serve(kernel, port=0, browser=False, announce=announce), daemon=True)
    thread.start()
    try:
        assert ready.wait(15)
        token = parse_qs(urlsplit(urls[0]).fragment).get("token", [""])[0]
        assert token
        browser_script = Path(__file__).with_name("source_review.mjs")
        run = subprocess.run(
            [
                str(Path(nodejs_wheel.__file__).parent / "bin" / "node"),
                str(browser_script),
                urls[0],
                engine,
                str(package),
                str(executable),
            ],
            cwd=package.parent,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        assert run.returncode == 0, (run.stdout + run.stderr).replace(token, "<redacted-session>")
        assert ["auth", "export", "--unmasked"] not in calls
    finally:
        if Server.instances:
            Server.instances[0].should_exit = True
        thread.join(15)
        assert not thread.is_alive()
