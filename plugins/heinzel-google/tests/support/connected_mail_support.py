"""A separate human-approved mail read through the registered plugin and private head, all offline."""

import json
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from heinzel.heads import web

from heinzel_google import _existing_lease as lease_module
from heinzel_google._existing_lease import CapturedGwsRead
from heinzel_google._gws import Process
from tests.support.connected_schedule_support import _confirm, _post

pytestmark = pytest.mark.integration


def _setup_mail(boot, tmp_path, monkeypatch):  # noqa: C901 - fake process and connection setup
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    gws = tmp_path / "gws"
    gws.write_bytes(b"\xcf\xfa\xed\xfe" + b"offline-fixture")
    gws.chmod(0o700)
    model, model_calls = tmp_path / "fake-claude", tmp_path / "model-calls"
    model.write_text(
        f"""#!{sys.executable}
import json,sys
if sys.argv[1:] == ['auth','status','--json']:
 print(json.dumps({{'loggedIn':True,'authMethod':'claude.ai','apiProvider':'firstParty'}})); raise SystemExit
if sys.argv[1:] == ['--version']:
 print('2.1.312 (Claude Code)'); raise SystemExit
payload=json.load(sys.stdin)
try: n=len(open({str(model_calls)!r}).read())
except FileNotFoundError: n=0
open({str(model_calls)!r},'a').write('x')
if n in (0,2,4):
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
    model.chmod(0o700)
    monkeypatch.setenv("HZ_GOOGLE__GWS_PATH", str(gws))
    monkeypatch.setenv("HZ_CAPABILITIES__MAIL", "google")
    monkeypatch.setenv("HZ_SYSTEM_RUNNER__CLAUDE_EXECUTABLE", str(model))
    monkeypatch.setenv("HZ_CAPABILITIES__AI_ACCESS", "claude-code")
    monkeypatch.setenv("HZ_CAPABILITIES__AGENT_RUNNER", "claude-code")
    credential = json.dumps(
        {"type": "authorized_user", "client_id": "fixture", "client_secret": "private", "refresh_token": "private"}
    ).encode()
    calls = []

    def run(_self, _executable, arguments, _timeout, context):
        args = list(arguments)
        if args == ["--version"]:
            return Process(0, b"gws 0.22.5")
        if args == ["auth", "export", "--unmasked"]:
            return Process(0, credential)
        assert context[0]["GOOGLE_WORKSPACE_CLI_TOKEN"] == "fixture-access"
        if args[:3] == ["drive", "about", "get"]:
            return Process(0, b'{"user":{"permissionId":"fixture-account","me":true}}')
        calls.append(args[:4])
        if args[:4] == ["gmail", "users", "labels", "list"]:
            return Process(0, b'{"labels":[]}')
        if args[:4] == ["gmail", "users", "messages", "list"]:
            return Process(0, b'{"messages":[{"id":"m1"}]}')
        if args[:4] == ["gmail", "users", "messages", "get"]:
            return Process(
                0,
                b'{"id":"m1","internalDate":"1767261600000","payload":{"headers":[{"name":"Subject","value":"Example"}]}}',
            )
        raise AssertionError(args[:4])

    class ExchangeProcess:
        pid = 123456789
        returncode = 0

        def communicate(self, data=None, timeout=None):
            del data, timeout
            return json.dumps(
                {
                    "access_token": "fixture-access",
                    "expires_in": 300,
                    "scope": " ".join(lease_module._MAIL_SCOPES),
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
            assert args[-1] == "mail"
            return ExchangeProcess()
        return original_popen(args, *positional, **keywords)

    monkeypatch.setattr(CapturedGwsRead, "_run", run)
    monkeypatch.setattr(lease_module.subprocess, "Popen", popen)
    monkeypatch.setattr(lease_module, "signal_group", lambda *_args: None)
    return boot(), calls


def test_mail_read_requires_its_own_review_and_revocation(boot, tmp_path, monkeypatch):
    kernel, calls = _setup_mail(boot, tmp_path, monkeypatch)
    auth = {"Authorization": "Bearer fixture-token"}
    with TestClient(
        web.build(kernel, port=None, token="fixture-token", static=None), base_url="http://localhost"
    ) as client:
        session = _post(client, "/api/heinzel/new-chat", body={"request_id": "new"})["session_id"]
        _post(
            client,
            "/api/heinzel/chat",
            body={"session_id": session, "request_id": "first", "message": "Inspect the source."},
        )
        _post(client, "/api/heinzel/answer-chat", body={"session_id": session, "request_id": "first"})
        options = client.get("/api/heinzel/connected-read-options", params={"session_id": session}, headers=auth)
        assert ("mail", "messages") in {(item["capability"], item["method"]) for item in options.json()}
        assert calls == []
        fixed = {"query": "", "window": {"since": "2026-01-01T00:00:00Z", "until": "2026-01-02T00:00:00Z"}}
        grant = _post(
            client,
            "/api/heinzel/propose-connected-read",
            body={
                "session_id": session,
                "request_id": "mail",
                "capability": "mail",
                "method": "messages",
                "fixed_arguments": fixed,
            },
        )
        assert grant["review"]["fixed_arguments"] == fixed
        assert "candidate metadata outside" in grant["review"]["candidate_read_disclosure"]
        assert "gmail.readonly" in grant["review"]["candidate_read_disclosure"]
        assert grant["review"]["provider_scopes"] == sorted(lease_module._MAIL_SCOPES)
        assert calls == []
        _confirm(
            client,
            session,
            "mail",
            "/api/system/runner/chat/propose-connected-read-review",
            "approve-connected-read",
            expected=grant,
        )
        _post(
            client, "/api/heinzel/chat", body={"session_id": session, "request_id": "second", "message": "Inspect now."}
        )
        _post(client, "/api/heinzel/answer-chat", body={"session_id": session, "request_id": "second"})
        assert calls == [
            ["gmail", "users", "labels", "list"],
            ["gmail", "users", "messages", "list"],
            ["gmail", "users", "messages", "get"],
        ]
        _post(client, "/api/heinzel/revoke-connected-read", body={"session_id": session, "request_id": "mail"})
        status = client.get("/api/heinzel/connected-read-state", params={"session_id": session}, headers=auth).json()
        assert status["status"] == "revoked"
        _post(
            client,
            "/api/heinzel/chat",
            body={"session_id": session, "request_id": "third", "message": "Inspect again."},
        )
        _post(client, "/api/heinzel/answer-chat", body={"session_id": session, "request_id": "third"})
        assert len(calls) == 3
        activity = client.get("/api/heinzel/tool-activity", params={"session_id": session}, headers=auth).json()
        assert any(item["tool"] == "connected_read" and item["status"] == "denied" for item in activity["items"])
