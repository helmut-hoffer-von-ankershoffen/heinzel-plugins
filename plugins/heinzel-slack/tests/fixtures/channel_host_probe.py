"""Fresh installed host/adapter proof: all external I/O is a loopback Slack stand-in and a captured fixture writer."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from heinzel import ApprovalChannel, Config, CurrentUser, Settings
from heinzel.heads import web
from heinzel.kernel import boot

state = Path(sys.argv[1])
state.mkdir(mode=0o700)
static = state / "static"
static.mkdir()
(static / "index.html").write_text("<!doctype html>")
features = frozenset({"captured_writes", "connected_channels"})
config = Config(files=(), data={"hz": {"features": sorted(features)}, "capabilities": {"documents": "fixturewrite"}})
settings = Settings(
    features=features,
    plugins_enabled=True,
    state_dir=state / "state",
    data_dir=state / "data",
    cache_dir=state / "cache",
    log_dir=state / "logs",
)

with patch.object(Config, "load", return_value=config):
    kernel = boot(settings)
    assert not kernel.errors, kernel.errors
    slack = sys.modules["heinzel_slack"]
    writer = sys.modules["fixture_captured_writer"]
    assert type(slack.__spec__.loader).__name__ == type(writer.__spec__.loader).__name__ == "SourceOnlyFinder"
    # Start the stand-in only after real boot captured the installed packages. No manual MIME/runtime preload.
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import parse_qs

    seen = {"posts": [], "updates": [], "account": "U0BOT0001", "headers": []}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            method = self.path.rsplit("/", 1)[-1]
            raw = self.rfile.read(int(self.headers.get("content-length", "0"))).decode()
            body = (
                json.loads(raw)
                if raw and self.headers.get("content-type", "").startswith("application/json")
                else {key: value[0] for key, value in parse_qs(raw).items()}
            )
            seen["headers"].append(self.headers.get("authorization"))
            assert self.headers.get("authorization") == "Bearer synthetic-fixture-bot"
            if method == "auth.test":
                reply = {"ok": True, "team_id": "T0TEAM001", "team": "Synthetic", "user_id": seen["account"]}
            elif method == "conversations.open":
                assert body["users"] in ("U0OWNER01", "U0OTHER01")
                reply = {"ok": True, "channel": {"id": "D0DM000001"}}
            elif method == "chat.postMessage":
                assert body["channel"] == "D0DM000001"
                seen["posts"].append(body)
                reply = {"ok": True, "channel": body["channel"], "ts": f"{len(seen['posts'])}.000100"}
            elif method == "chat.update":
                seen["updates"].append(body)
                reply = {"ok": True}
            else:
                raise AssertionError("Unexpected stand-in request")
            data = json.dumps(reply).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_args):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    api_type = sys.modules["heinzel_slack._slack"].WebApi

    class LoopbackTransport:
        def api(self):
            return api_type("synthetic-fixture-bot", 2, base_url=f"http://127.0.0.1:{httpd.server_port}/")

        def has_tokens(self):
            return True, True

        def listener(self):
            raise AssertionError("No real Socket Mode connection in an offline proof")

    try:
        kernel.bind(CurrentUser, CurrentUser(state / "identity"))
        kernel.bind(slack.Transport, LoopbackTransport())
        kernel.bind(slack.SlackSettings, slack.SlackSettings(owner="U0OWNER01", team="T0TEAM001"))
        service = kernel.resolve(slack.SlackService)
        capture = kernel.source_discovery.service_capture(kernel, kernel.module("slack"), ApprovalChannel)
        assert len(capture.finder.snapshot.files) < 256
        assert sum(len(data) for _, data in capture.finder.snapshot.files) < 2_000_000
        session_value = "synthetic-fixture-web-session"
        authorization = {"Authorization": f"Bearer {session_value}"}
        client = TestClient(
            web.build(kernel, port=8000, token=session_value, static=static),
            base_url="http://127.0.0.1:8000",
        )
        created = client.post(
            "/api/heinzel/new-chat", headers=authorization, json={"request_id": "create", "name": "Lotte"}
        )
        assert created.status_code == 200, created.text
        session = created.json()["session_id"]

        def stage(request, *, write_request=None):
            proposed = {"session_id": session, "request_id": request, "channel": "slack"}
            if write_request:
                proposed["write_request"] = write_request
            else:
                proposed["notice"] = {
                    "key": "input-key",
                    "helper": "Lotte",
                    "title": "Ready",
                    "body": "Synthetic fixture only.",
                    "route": "",
                }
            terms = client.post("/api/heinzel/propose-channel-item", headers=authorization, json=proposed)
            assert terms.status_code == 200, terms.text
            staged = client.post(
                "/api/system/runner/chat/propose-channel-item",
                headers=authorization,
                params={"durable_session": session, "request_id": request},
            )
            assert staged.status_code == 200, staged.text
            chat = staged.json()
            action = next(
                item
                for item in chat["actions"]
                if item["operation"] == "deliver-channel-item" and item["arguments"]["request_id"] == request
            )
            return terms.json(), {"session": chat["id"], "action": action["id"]}

        _, decision = stage("notice-one")
        assert seen["posts"] == []
        assert client.post("/api/system/runner/chat/confirm", params=decision).status_code == 401
        confirmed = client.post("/api/system/runner/chat/confirm", headers=authorization, params=decision)
        assert confirmed.status_code == 200, confirmed.text
        assert len(seen["posts"]) == 1
        assert client.post("/api/system/runner/chat/confirm", headers=authorization, params=decision).status_code == 400
        _, decision = stage("account-drift")
        seen["account"] = "U0OTHER01"
        assert client.post("/api/system/runner/chat/confirm", headers=authorization, params=decision).status_code == 400
        seen["account"] = "U0BOT0001"
        assert len(seen["posts"]) == 1
        _, decision = stage("scope-drift")
        original_settings = service.settings
        service._settings = original_settings.model_copy(update={"owner": "U0OTHER01"})
        assert client.post("/api/system/runner/chat/confirm", headers=authorization, params=decision).status_code == 400
        service._settings = original_settings
        assert len(seen["posts"]) == 1
        proposal = {
            "session_id": session,
            "request_id": "draft-one",
            "account": "account-one",
            "source": "source-one",
            "reference": "fixture://document/one",
            "operation": "insert-draft",
            "section": "summary",
            "base_revision": "one",
            "write_scope": "fixture-write",
            "content": "Synthetic exact replacement.",
        }
        drafted = client.post("/api/heinzel/propose-captured-write", headers=authorization, json={"proposal": proposal})
        assert drafted.status_code == 200, drafted.text
        terms, decision = stage("approval-one", write_request="draft-one")
        assert writer.STATE["writes"] == 0
        confirmed = client.post("/api/system/runner/chat/confirm", headers=authorization, params=decision)
        assert confirmed.status_code == 200, confirmed.text
        assert len(seen["posts"]) == 2
        assert writer.STATE["writes"] == 0
        row = service.store.by_external(terms["approval"]["request_id"])
        assert row is not None
        payload = {
            "type": "block_actions",
            "team": {"id": row.team},
            "user": {"id": "U0OTHER01"},
            "channel": {"id": row.channel},
            "container": {"type": "message", "channel_id": row.channel, "message_ts": row.message_ts},
            "message": {"ts": row.message_ts},
            "actions": [
                {
                    "type": "button",
                    "action_id": "hz_approve",
                    "value": f"v1:{row.id}:{row.bound}",
                    "action_ts": str(datetime.now(UTC).timestamp()),
                }
            ],
        }
        assert service.handle(payload).reason == "not_the_owner"
        pending = client.post("/api/fixturewrite/consume-replies", headers=authorization)
        assert pending.status_code == 200 and pending.json() == 0, pending.text
        assert writer.STATE["writes"] == 0
        payload["user"]["id"] = row.owner
        assert service.handle(payload).state == "approved"
        assert writer.STATE["writes"] == 0
        assert client.post("/api/fixturewrite/consume-replies").status_code == 401
        consumed = client.post("/api/fixturewrite/consume-replies", headers=authorization)
        assert consumed.status_code == 200 and consumed.json() == 1, consumed.text
        assert writer.STATE["writes"] == 1
        again = client.post("/api/fixturewrite/consume-replies", headers=authorization)
        assert again.status_code == 200 and again.json() == 0, again.text
        assert service.handle(payload).reason == "already_approved"
        assert writer.STATE["writes"] == 1
        version = Path(slack.__file__).parent / "_vendor/slack_sdk/version.py"
        version.write_text(version.read_text() + "\n# Synthetic source drift in this disposable installation.\n")
        stale = client.post(
            "/api/heinzel/propose-channel-item",
            headers=authorization,
            json={
                "session_id": session,
                "request_id": "tampered-source",
                "channel": "slack",
                "notice": {"key": "new", "helper": "Lotte", "title": "Ready", "body": "Fixture only", "route": ""},
            },
        )
        assert stale.status_code == 400, stale.text
        assert len(seen["posts"]) == 2
        assert all(header == "Bearer synthetic-fixture-bot" for header in seen["headers"])
        print(
            json.dumps(
                {
                    "captured_packages": ["heinzel_slack", "fixture_captured_writer"],
                    "notice_posts": 1,
                    "approval_posts": 1,
                    "captured_writes": writer.STATE["writes"],
                    "wrong_scope_refused": True,
                    "changed_account_refused": True,
                    "nonowner_click_refused": True,
                    "unauthenticated_confirmation_refused": True,
                    "repeat_confirmation_and_consumption_refused": True,
                    "vendor_source_tamper_refused": True,
                }
            )
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(5)
