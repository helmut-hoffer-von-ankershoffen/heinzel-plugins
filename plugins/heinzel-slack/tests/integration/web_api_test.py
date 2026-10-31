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
        "auth.test": {"ok": True, "team_id": "T0TEAM001", "team": "Test", "user_id": "UBOT"},
        "conversations.open": {"ok": True, "channel": {"id": "D0DM000001"}},
        "chat.postMessage": {"ok": True, "ts": "1.2"},
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
    assert (who.team_id, who.bot_user) == ("T0TEAM001", "UBOT")
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
