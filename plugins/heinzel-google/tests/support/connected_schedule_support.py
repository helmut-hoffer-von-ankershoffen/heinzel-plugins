"""Owner-reviewed rolling schedule through the real Google plugin with offline boundaries."""

import json
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import heinzel
import pytest
from fastapi.testclient import TestClient
from heinzel import CompiledJobs, ConnectedReadService, CurrentUser, OperationLet
from heinzel.heads import web

from heinzel_google import _existing_lease as lease_module
from heinzel_google._connected_calendar import GoogleConnectedReadService
from heinzel_google._existing_lease import CapturedGwsRead
from heinzel_google._gws import GoogleSession, Process

pytestmark = pytest.mark.integration

_SCOPES = (
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
)


def _fake_claude(path: Path, calls: Path) -> None:
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
if n == 3: open({str(calls.with_suffix(".input"))!r},'w').write(json.dumps(payload))
if n in (0,2):
 name='agent:propose' if n == 0 else 'connected_read'
 args={{'expected_revision':0,'contract':'Inspect my selected source.','timeout_seconds':30}} if n == 0 else {{}}
 wire={{'kind':'tool','name':'use_tool','arguments':{{'name':name,'arguments':args}},'text':None}}
else:
 name=next(t['name'] for t in payload['tools'] if t['name'] != 'use_tool')
 wire={{'kind':'tool','name':name,'arguments':{{'report':'Source inspected.'}},'text':None}}
print(json.dumps({{'type':'result','subtype':'success','is_error':False,'permission_denials':[],'structured_output':wire}}))
""",
        encoding="utf-8",
    )
    path.chmod(0o700)


def _fake_transport(monkeypatch, calls, launches):
    credential = json.dumps(
        {
            "type": "authorized_user",
            "client_id": "fixture",
            "client_secret": "fixture-secret",
            "refresh_token": "fixture-refresh",
        }
    ).encode()

    def run(_self, _executable, arguments, _timeout, context):
        args = list(arguments)
        launches.append(args[:3])
        if args == ["--version"]:
            return Process(0, b"gws 0.22.5")
        if args == ["auth", "export", "--unmasked"]:
            return Process(0, credential)
        assert context[0]["GOOGLE_WORKSPACE_CLI_TOKEN"] == "fixture-access"
        if args[:3] == ["drive", "about", "get"]:
            return Process(0, b'{"user":{"permissionId":"fixture-account","me":true}}')
        assert args[:3] == ["calendar", "events", "list"]
        params = json.loads(args[args.index("--params") + 1])
        calls.append(params)
        start = datetime.fromisoformat(params["timeMin"]) + timedelta(seconds=120)
        item = {
            "id": "fictional-1",
            "summary": "Example",
            "start": {"dateTime": start.isoformat()},
            "end": {"dateTime": (start + timedelta(seconds=60)).isoformat()},
        }
        return Process(0, json.dumps({"items": [item]}).encode())

    class ExchangeProcess:
        pid = 123456789
        returncode = 0

        def communicate(self, data=None, timeout=None):
            if data is not None:
                assert data == credential
            return json.dumps(
                {
                    "access_token": "fixture-access",
                    "expires_in": 300,
                    "scope": " ".join(_SCOPES),
                    "token_type": "Bearer",
                }
            ).encode(), b""

    original_popen = subprocess.Popen

    def popen(args, *positional, **keywords):
        if (
            isinstance(args, list)
            and len(args) >= 5
            and args[1:4] == ["-I", "-S", "-c"]
            and "OAuth token request failed" in args[4]
        ):
            return ExchangeProcess()
        return original_popen(args, *positional, **keywords)

    monkeypatch.setattr(CapturedGwsRead, "_run", run)
    monkeypatch.setattr(lease_module.subprocess, "Popen", popen)
    monkeypatch.setattr(lease_module, "signal_group", lambda *_args: None)


def _post(client, path, *, body=None, params=None):
    response = client.post(path, json=body, params=params, headers={"Authorization": "Bearer fixture-token"})
    assert response.status_code == 200, response.text
    return response.json()


def _confirm(client, session, request, route, operation, *, expected):  # noqa: PLR0913 - exact action review
    chat = _post(client, route, params={"durable_session": session, "request_id": request})
    action = next(item for item in chat["actions"] if item["operation"] == operation)
    assert "approval_proof" not in action["arguments"]
    assert action["arguments"]["review"] == expected
    result = _post(client, "/api/system/runner/chat/confirm", params={"session": chat["id"], "action": action["id"]})
    assert next(item for item in result["actions"] if item["id"] == action["id"])["status"] == "done"
    return action


def _observed_items(value):
    if isinstance(value, dict):
        if "observed_items" in value:
            return value["observed_items"]
        for child in value.values():
            found = _observed_items(child)
            if found is not None:
                return found
    if isinstance(value, list):
        for child in value:
            found = _observed_items(child)
            if found is not None:
                return found
    if isinstance(value, str):
        try:
            return _observed_items(json.loads(value))
        except (ValueError, RecursionError):
            pass
    return None


def _assert_item_reference(path):
    observed = _observed_items(json.loads(path.read_text()))
    assert isinstance(observed, list)
    assert len(observed) == 1
    assert observed[0]["index"] == 0
    assert re.fullmatch(r"[0-9a-f]{64}", observed[0]["reference"])


def _assert_connected_completed(client, session, model_calls):
    activity = client.get(
        "/api/heinzel/tool-activity",
        params={"session_id": session},
        headers={"Authorization": "Bearer fixture-token"},
    ).json()
    assert any(item["tool"] == "connected_read" and item["status"] == "completed" for item in activity["items"])
    if hasattr(heinzel, "ConnectedItemIdentity"):
        _assert_item_reference(model_calls.with_suffix(".input"))


def _daemon_tick(kernel):
    current = kernel.resolve(CurrentUser)
    with current.local("daemon"):
        jobs = kernel.resolve(CompiledJobs).jobs
        scheduled = [job for job in jobs if job.name.startswith("agent-")]
        assert len(scheduled) == 1
        operations = [
            (record, op)
            for record, op in kernel.lets(OperationLet)
            if record.qualname == "system.daemon" and op.name == "tick"
        ]
        assert len(operations) == 1
        return kernel.invoke(operations[0][1])


def _setup(boot, tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    gws = tmp_path / "gws"
    gws.write_bytes(b"\xcf\xfa\xed\xfe" + b"offline-fixture")
    gws.chmod(0o700)
    model = tmp_path / "fake-claude"
    model_calls = tmp_path / "model-calls"
    _fake_claude(model, model_calls)
    monkeypatch.setenv("HZ_GOOGLE__GWS_PATH", str(gws))
    monkeypatch.setenv("HZ_CAPABILITIES__CALENDAR", "google")
    monkeypatch.setenv("HZ_SYSTEM_RUNNER__CLAUDE_EXECUTABLE", str(model))
    monkeypatch.setenv("HZ_CAPABILITIES__AI_ACCESS", "claude-code")
    monkeypatch.setenv("HZ_CAPABILITIES__AGENT_RUNNER", "claude-code")
    calls = []
    launches = []
    _fake_transport(monkeypatch, calls, launches)
    kernel = boot()
    record, provider = kernel.selected_capability_service(ConnectedReadService, "calendar")
    assert record.origin.distribution == "heinzel-google"
    assert type(provider) is GoogleConnectedReadService
    assert kernel.resolve_registered_service(GoogleSession, record).settings.gws_path == str(gws)
    return kernel, calls, model_calls, launches


def test_owner_reviewed_rolling_calendar_schedule_survives_daemon_restart(boot, tmp_path, monkeypatch):
    kernel, calls, model_calls, launches = _setup(boot, tmp_path, monkeypatch)
    with TestClient(
        web.build(kernel, port=None, token="fixture-token", static=None), base_url="http://localhost"
    ) as client:
        session = _post(client, "/api/heinzel/new-chat", body={"request_id": "new"})["session_id"]
        _post(
            client,
            "/api/heinzel/chat",
            body={"session_id": session, "request_id": "ask", "message": "Inspect my selected source."},
        )
        _post(client, "/api/heinzel/answer-chat", body={"session_id": session, "request_id": "ask"})
        contract = client.get(
            "/api/heinzel/latest-scheduled-agent-proposal",
            params={"session_id": session},
            headers={"Authorization": "Bearer fixture-token"},
        ).json()
        _confirm(
            client,
            session,
            contract["request_id"],
            "/api/system/runner/chat/propose-agent-contract",
            "accept-agent-contract",
            expected=contract,
        )
        options = client.get(
            "/api/heinzel/connected-read-options",
            params={"session_id": session},
            headers={"Authorization": "Bearer fixture-token"},
        )
        assert options.status_code == 200
        assert [(item["capability"], item["method"]) for item in options.json()] == [
            ("calendar", "events"),
            ("documents", "read"),
        ]
        assert calls == []
        assert launches == []
        unsupported = client.post(
            "/api/heinzel/propose-connected-read",
            headers={"Authorization": "Bearer fixture-token"},
            json={
                "session_id": session,
                "request_id": "unsupported",
                "capability": "calendar",
                "method": "free_busy",
                "fixed_arguments": {
                    "people": "",
                    "window": {"since": "2026-01-01T00:00:00Z", "until": "2026-01-02T00:00:00Z"},
                },
            },
        )
        assert unsupported.status_code == 400
        assert launches == []
        grant = _post(
            client,
            "/api/heinzel/propose-rolling-connected-read",
            body={
                "session_id": session,
                "request_id": "grant",
                "capability": "calendar",
                "method": "events",
                "fixed_arguments": {},
                "window_policy": {
                    "parameter": "window",
                    "lookback_seconds": 60,
                    "lookahead_seconds": 600,
                    "timezone": "Europe/Berlin",
                },
            },
        )
        assert grant["review"]["account_identity"] == "fixture-account"
        assert grant["review"]["provider_scopes"] == list(_SCOPES)
        if hasattr(heinzel, "ConnectedItemIdentity"):
            assert grant["review"]["item_identity"] == {
                "collection": [],
                "identity_field": "id",
                "revision_field": None,
            }
        _confirm(
            client,
            session,
            "grant",
            "/api/system/runner/chat/propose-connected-read-review",
            "approve-connected-read",
            expected=grant,
        )
        schedule = _post(
            client,
            "/api/heinzel/propose-agent-schedule",
            body={
                "session_id": session,
                "request_id": "schedule",
                "contract_request_id": contract["request_id"],
                "cadence_seconds": 300,
                "max_requests": 4,
                "timeout_seconds": 30,
                "connected_request_id": "grant",
            },
        )
        assert schedule["connected_grant"] == grant
        _confirm(
            client,
            session,
            "schedule",
            "/api/system/runner/chat/propose-agent-schedule-review",
            "approve-agent-schedule",
            expected=schedule,
        )
        report = _daemon_tick(kernel)
        assert any(run.disposition == "rendered" for run in report.runs)
        assert len(calls) == 1
        assert calls[0]["calendarId"] == "primary"
        start = datetime.fromisoformat(calls[0]["timeMin"])
        end = datetime.fromisoformat(calls[0]["timeMax"])
        assert (end - start).total_seconds() == 660
        assert abs((datetime.now(UTC) - start).total_seconds() - 60) < 60
        assert model_calls.read_text() == "xxxx"
        _assert_connected_completed(client, session, model_calls)
        # If the real clock crosses a cadence boundary, compare another restart in the new slot.
        previous = report
        for _ in range(3):
            previous_calls, previous_model = len(calls), model_calls.read_text()
            restarted = _daemon_tick(boot())
            if int(previous.at.timestamp()) // 300 == int(restarted.at.timestamp()) // 300:
                assert len(calls) == previous_calls
                assert model_calls.read_text() == previous_model
                break
            previous = restarted
        else:
            pytest.fail("Could not test two daemon ticks within one schedule slot")
        before_revoke = len(calls)
        _post(client, "/api/heinzel/revoke-connected-read", body={"session_id": session, "request_id": "grant"})
        response = client.get(
            "/api/heinzel/agent-schedule",
            params={"session_id": session, "request_id": "schedule"},
            headers={"Authorization": "Bearer fixture-token"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "stale"
        assert len(calls) == before_revoke
