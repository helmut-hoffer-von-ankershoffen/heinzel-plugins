"""The real Web API client against a local stand-in server: what we send, and how failures are told apart."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from heinzel import Credentials, HeinzelError

from heinzel_slack import APP_TOKEN, BOT_TOKEN, SlackSettings, Transport
from heinzel_slack._slack import SlackRefused, SlackUnknown, SocketListener, WebApi

pytestmark = pytest.mark.integration


class Memory:
    name = "memory"

    def __init__(self, values):
        self.values = values

    def get(self, service, name):
        return self.values.get(name)

    def set(self, service, name, value):
        self.values[name] = value

    def delete(self, service, name):
        return self.values.pop(name, None) is not None


@pytest.fixture
def server():
    seen: list[tuple[str, dict]] = []
    replies: dict[str, dict] = {
        "auth.test": {"ok": True, "team_id": "T0TEAM001", "team": "Test", "user_id": "U0BOT0001"},
        "conversations.open": {"ok": True, "channel": {"id": "D0DM000001"}},
        "chat.postMessage": {"ok": True, "ts": "1.2", "channel": "D0DM000001"},
        "chat.update": {"ok": True},
        "users.info": {"ok": True, "user": {"real_name": "Ada Lovelace", "name": "ada"}},
    }

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            method = self.path.rsplit("/", 1)[-1]
            body = self.rfile.read(int(self.headers.get("content-length", 0))).decode()
            seen.append((method, {"auth": self.headers.get("authorization"), "body": body}))
            data = json.dumps(replies[method]).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}/", seen, replies
    httpd.shutdown()
    httpd.server_close()
    thread.join(5)


def test_the_calls_go_where_they_should_and_never_unfurl_or_link_names(server):
    url, seen, _ = server
    api = WebApi("xoxb-test", 5, base_url=url)
    who = api.identity()
    assert (who.team_id, who.bot_user) == ("T0TEAM001", "U0BOT0001")
    assert api.open_dm("U0OWNER01") == "D0DM000001"
    assert api.post("D0DM000001", "hi", [{"type": "section"}]) == "1.2"
    api.update("D0DM000001", "1.2", "hi", [])
    assert api.display_name("U0OWNER01") == "Ada Lovelace"
    post = next(call for method, call in seen if method == "chat.postMessage")
    assert "unfurl_links=False" in post["body"] or '"unfurl_links": false' in post["body"].lower()
    assert post["auth"] == "Bearer xoxb-test"


def test_slack_saying_no_is_a_refusal_without_the_token_in_the_message(server):
    url, _, replies = server
    replies["chat.postMessage"] = {"ok": False, "error": "invalid_auth"}
    with pytest.raises(SlackRefused) as caught:
        WebApi("xoxb-secret", 5, base_url=url).post("D1", "hi", [])
    assert "invalid_auth" in str(caught.value)
    assert "xoxb-secret" not in str(caught.value)


def test_not_a_direct_message_is_refused(server):
    url, _, replies = server
    replies["conversations.open"] = {"ok": True, "channel": {"id": "C0PUBLIC01"}}
    with pytest.raises(HeinzelError, match="direct message"):
        WebApi("xoxb-test", 5, base_url=url).open_dm("U0OWNER01")


def test_a_dead_connection_on_post_is_unknown_not_refused():
    with pytest.raises(SlackUnknown):
        WebApi("xoxb-test", 2, base_url="http://127.0.0.1:9/").post("D1", "hi", [])


@pytest.mark.parametrize("method", ["update", "display_name"])
def test_transport_errors_have_fixed_safe_messages(method, monkeypatch):
    api = WebApi("xoxb-sentinel-secret", 1)

    def broken(**_kwargs):
        raise RuntimeError("xoxb-sentinel-secret /private/sentinel/transport")

    monkeypatch.setattr(api._client, "chat_update" if method == "update" else "users_info", broken)
    with pytest.raises(HeinzelError) as caught:
        if method == "update":
            api.update("D0DM000001", "1.2", "draft", [])
        else:
            api.display_name("U0OWNER01")
    assert str(caught.value) == (
        "Slack did not confirm the message update" if method == "update" else "Slack display name could not be read"
    )
    assert caught.value.__suppress_context__


def test_a_name_that_cannot_be_read_is_none(server):
    url, _, replies = server
    replies["users.info"] = {"ok": False, "error": "missing_scope"}
    assert WebApi("xoxb-test", 5, base_url=url).display_name("U1") is None


def test_transport_needs_stored_tokens_and_says_how_to_store_them():
    settings = SlackSettings(owner="U0OWNER01")
    credentials = Credentials(Memory({}), [("slack", BOT_TOKEN), ("slack", APP_TOKEN)])
    transport = Transport(settings, credentials)
    assert transport.has_tokens() == (False, False)
    with pytest.raises(HeinzelError, match="hz system credential set"):
        transport.api()
    with pytest.raises(HeinzelError, match="hz system credential set"):
        transport.listener()
    credentials.set(BOT_TOKEN, "xoxb-1")
    credentials.set(APP_TOKEN, "xapp-1")
    assert transport.has_tokens() == (True, True)
    assert isinstance(transport.listener(), SocketListener)
    transport.listener().stop()  # stopping what never started is fine


@pytest.mark.parametrize(
    "reply",
    [
        {"ok": True},
        {"ok": True, "ts": None},
        {"ok": True, "ts": "1.2", "channel": "C0PUBLIC01"},
        {"ok": True, "ts": "garbage", "channel": "D0DM000001"},
        {"ok": False, "error": "internal_error"},
    ],
)
def test_ambiguous_post_acknowledgement_is_unknown(server, reply):
    url, seen, replies = server
    replies["chat.postMessage"] = reply
    with pytest.raises(SlackUnknown):
        WebApi("xoxb-test", 5, base_url=url).post("D0DM000001", "hi", [])
    assert len(seen) == 1


@pytest.mark.parametrize("value", [None, {}, {"id": "D"}, {"id": "D0DM000001/foreign"}, {"id": 123}])
def test_malformed_dm_target_is_refused(server, value):
    url, _, replies = server
    replies["conversations.open"] = {"ok": True, "channel": value}
    with pytest.raises(HeinzelError, match="direct message"):
        WebApi("xoxb-test", 5, base_url=url).open_dm("U0OWNER01")


@pytest.mark.parametrize("field", ["account", "destination", "scope"])
def test_reviewed_transport_checks_all_target_fields_before_any_post(server, field):
    url, seen, _ = server
    api = WebApi("xoxb-pinned", 5, base_url=url)
    target = api.delivery_target("U0OWNER01", "T0TEAM001")
    assert target.account == "slack:T0TEAM001:U0BOT0001"
    assert target.destination == "D0DM000001"
    assert target.scope == "slack:owner-dm:U0OWNER01:chat.write:v1"
    with pytest.raises(SlackRefused, match="changed"):
        api.post_reviewed(target.model_copy(update={field: "different"}), "U0OWNER01", "T0TEAM001", "draft", [])
    assert not any(method == "chat.postMessage" for method, _ in seen)


def test_reviewed_post_pins_token_through_identity_dm_and_actual_http_mutation(server, monkeypatch):
    from dataclasses import FrozenInstanceError

    url, seen, _ = server
    api = WebApi("xoxb-pinned-sentinel", 5, base_url=url)
    target = api.delivery_target("U0OWNER01", "T0TEAM001")
    original = api._client.conversations_open
    replacement = "xoxb-foreign-sentinel"

    def rotate_after_dm(**kwargs):
        result = original(**kwargs)
        api._client.token = replacement
        return result

    monkeypatch.setattr(api._client, "conversations_open", rotate_after_dm)
    with pytest.raises(FrozenInstanceError):
        api._token = replacement
    assert api.post_reviewed(target, "U0OWNER01", "T0TEAM001", "exact draft", []) == "1.2"
    assert len([method for method, _ in seen if method == "chat.postMessage"]) == 1
    assert all(call["auth"] == "Bearer xoxb-pinned-sentinel" for _, call in seen)
    assert "xoxb-pinned-sentinel" not in repr(api)
    # The only handler closes an HTTP error response and never asks for a retry (sdk_web_test proves both).
    assert [type(handler).__name__ for handler in api._client.retry_handlers] == ["CloseHttpError"]


def test_new_credentials_for_another_account_refuse_without_posting(server):
    url, seen, replies = server
    target = WebApi("xoxb-original", 5, base_url=url).delivery_target("U0OWNER01", "T0TEAM001")
    replies["auth.test"]["user_id"] = "U0OTHER01"
    with pytest.raises(SlackRefused, match="changed"):
        WebApi("xoxb-new-credentials", 5, base_url=url).post_reviewed(target, "U0OWNER01", "T0TEAM001", "draft", [])
    assert not any(method == "chat.postMessage" for method, _ in seen)


@pytest.mark.parametrize("user", [None, "", "UBOT", "/private/sentinel", 123])
def test_invalid_authenticated_posting_account_never_produces_a_target(server, user):
    url, seen, replies = server
    replies["auth.test"]["user_id"] = user
    with pytest.raises(HeinzelError, match="invalid posting account identity"):
        WebApi("xoxb-sentinel", 5, base_url=url).delivery_target("U0OWNER01", "T0TEAM001")
    assert len(seen) == 1
