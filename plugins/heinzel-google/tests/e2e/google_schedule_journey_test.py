"""Mounted registered Google read and rolling schedule through isolated offline boundaries."""

import json
import os
import runpy
import subprocess
import sys
import threading
from pathlib import Path
from typing import ClassVar
from urllib.parse import parse_qs, urlsplit

import nodejs_wheel
import pytest
import uvicorn
from heinzel import Notifications
from heinzel.heads import web

from tests.support.installed_browser_support import run_installed_browser

pytestmark = pytest.mark.e2e


class LocalNotices(Notifications):
    """In-memory notification sink; never invokes native delivery."""

    def __init__(self):
        self.calls = []
        self.keys = set()

    def emit_once(self, kind, title, body, *, route, command, key):  # noqa: PLR0913 - interface
        if key not in self.keys:
            self.calls.append((kind, title, body, route, command, key))
            self.keys.add(key)
        return True

    def has_once(self, key):
        return key in self.keys

    def forget_completed(self, keys):
        self.keys.difference_update(keys)
        return True

    def post_native(self):
        return 0

    def watched(self):
        pass

    def due(self, now=None):
        return []

    def recent(self, limit=50):
        return []


def _fake_notice_claude(path, calls):
    path.write_text(
        f"""#!{sys.executable}
import json,sys
if sys.argv[1:] == ['auth','status','--json']:
 print(json.dumps({{'loggedIn':True,'authMethod':'claude.ai','apiProvider':'firstParty'}})); raise SystemExit
if sys.argv[1:] == ['--version']:
 print('2.1.312 (Claude Code)'); raise SystemExit
payload=json.load(sys.stdin)
try: n=len(open({str(calls)!r}).read())
except FileNotFoundError: n=0
open({str(calls)!r},'a').write('x')
if n in (0,2,4,5):
 name={{0:'agent:propose',2:'connected_read',4:'connected_read',5:'notification:propose'}}[n]
 args={{}}
 if n == 0: args={{'expected_revision':0,'contract':'Inspect my selected source.','timeout_seconds':30}}
 if n == 5: args={{'topic':'example','title':'Review requested','body':'The source was read; please review.'}}
 wire={{'kind':'tool','name':'use_tool','arguments':{{'name':name,'arguments':args}},'text':None}}
else:
 name=next(t['name'] for t in payload['tools'] if t['name'] != 'use_tool')
 wire={{'kind':'tool','name':name,'arguments':{{'report':'Source inspected.'}},'text':None}}
print(json.dumps({{'type':'result','subtype':'success','is_error':False,'permission_denials':[],'structured_output':wire}}))
""",
        encoding="utf-8",
    )
    path.chmod(0o700)


def _require_rendered(report):
    if not any(item.disposition == "rendered" for item in report.runs):
        msg = "The helper did not render a run"
        raise RuntimeError(msg)


def _daemon_probe(kernel, boot, directory, notices, helper):
    result = {"failure": None, "deduplicated": False}

    def run():
        try:
            signal = directory / "daemon-start.json"
            waiter = threading.Event()
            for _ in range(1200):
                if signal.exists():
                    break
                waiter.wait(0.05)
            json.loads(signal.read_text())
            report = helper(kernel)
            _require_rendered(report)
            previous = (directory / "model-calls").read_text()
            restarted = boot()
            restarted.bind(Notifications, notices)
            helper(restarted)
            result["deduplicated"] = (directory / "model-calls").read_text() == previous
        except Exception as error:  # noqa: BLE001 - fixture diagnostics contain only fictional data
            result["failure"] = str(error)
        finally:
            (directory / "daemon-finished.json").write_text(
                json.dumps(
                    {
                        "ok": result["failure"] is None,
                        "deduplicated": result["deduplicated"],
                        "failure": result["failure"],
                    }
                )
            )

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, result


@pytest.mark.timeout(180)
@pytest.mark.parametrize("engine", ["chromium", "webkit"])
def test_mounted_registered_google_schedule(tmp_path, engine):
    run_installed_browser(Path(__file__), "_exercise_mounted_registered_google_schedule", tmp_path, engine)


def _exercise_mounted_registered_google_schedule(boot, tmp_path, monkeypatch, engine):
    package = Path(os.environ["HZ_TEST_BROWSER_PACKAGE"])
    browser_cache = Path(os.environ["HZ_TEST_BROWSER_CACHE"])
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(browser_cache))
    source = Path(__file__).parents[1] / "support" / "connected_schedule_support.py"
    helpers = runpy.run_path(str(source))
    kernel, calls, model_calls, _launches = helpers["_setup"](boot, tmp_path, monkeypatch)
    _fake_notice_claude(tmp_path / "fake-claude", model_calls)
    notices = LocalNotices()
    kernel.bind(Notifications, notices)

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
    worker, outcome = _daemon_probe(kernel, boot, tmp_path, notices, helpers["_daemon_tick"])
    try:
        assert ready.wait(15)
        token = parse_qs(urlsplit(urls[0]).fragment).get("token", [""])[0]
        assert token
        script = Path(__file__).with_name("google_schedule_journey.mjs")
        result = subprocess.run(
            [
                str(Path(nodejs_wheel.__file__).parent / "bin" / "node"),
                str(script),
                urls[0],
                engine,
                str(tmp_path),
                "rolling",
                str(package),
            ],
            cwd=package.parent,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert result.returncode == 0, (result.stdout + result.stderr).replace(token, "<redacted-session>")
        assert outcome["failure"] is None
        assert outcome["deduplicated"]
        assert len(calls) == 2
        assert all(call["calendarId"] == "primary" for call in calls)
        assert model_calls.read_text() == "xxxxxxx"
        assert len(notices.calls) == 1
        assert notices.calls[0][1:3] == ("Review requested", "The source was read; please review.")
    finally:
        if Server.instances:
            Server.instances[0].should_exit = True
        server.join(15)
        worker.join(15)
        assert not server.is_alive()
