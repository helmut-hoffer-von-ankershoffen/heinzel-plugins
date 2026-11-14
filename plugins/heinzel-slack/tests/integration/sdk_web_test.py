"""The real `SdkWeb` on a local stand-in server: form reads, JSON writes, token in the header, errors told apart."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from heinzel import HeinzelError

from heinzel_slack._slack import SlackRefused, SlackUnknown
from heinzel_slack._web import RateLimited, SdkWeb, Web

pytestmark = pytest.mark.integration
TOKEN = "xoxb-fictional-sentinel"  # noqa: S105 - a fictional sentinel that must never appear


@pytest.fixture
def server():
    seen: list[dict[str, Any]] = []
    replies: dict[str, tuple[int, dict[str, str], dict[str, Any]]] = {}

    class Handler(BaseHTTPRequestHandler):
        def _answer(self, body: str) -> None:
            parts = urlsplit(self.path)
            method = parts.path.rsplit("/", 1)[-1]
            seen.append({
                "verb": self.command, "method": method, "query": parse_qs(parts.query), "body": body,
                "auth": self.headers.get("authorization"),
            })  # fmt: skip
            status, headers, reply = replies.get(method, (200, {}, {"ok": True}))
            data = json.dumps(reply).encode()
            self.send_response(status)
            for name, value in {"content-type": "application/json", **headers}.items():
                self.send_header(name, value)
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            self._answer(self.rfile.read(int(self.headers.get("content-length", 0))).decode())

        def log_message(self, *args):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield SdkWeb(TOKEN, 5, base_url=f"http://127.0.0.1:{httpd.server_port}/"), seen, replies
    httpd.shutdown()
    httpd.server_close()
    thread.join(5)


def test_reads_are_form_posts_and_writes_json_posts_with_the_token_only_in_the_header(server):
    web, seen, replies = server
    replies["conversations.history"] = (200, {}, {"ok": True, "messages": [{"ts": "1.0"}]})
    assert web.call("conversations.history", {"channel": "C0CHAN0001", "inclusive": "true"}, write=False)["messages"]
    web.call("chat.postMessage", {"channel": "C0CHAN0001", "text": "hi", "link_names": False}, write=True)
    read, write = seen
    form = parse_qs(read["body"])
    assert (read["verb"], form["channel"], form["inclusive"]) == ("POST", ["C0CHAN0001"], ["true"])
    assert (write["verb"], json.loads(write["body"])) == (
        "POST", {"channel": "C0CHAN0001", "text": "hi", "link_names": False}
    )  # fmt: skip
    for call in seen:
        assert call["auth"] == f"Bearer {TOKEN}"
        assert TOKEN not in json.dumps(call["query"]) + call["body"]
    assert TOKEN not in repr(web)


@pytest.mark.parametrize("write", [False, True])
def test_429_is_rate_limited_with_slacks_retry_after(server, write):
    web, _, replies = server
    replies["users.info"] = (429, {"Retry-After": "7"}, {"ok": False, "error": "ratelimited"})
    with pytest.raises(RateLimited) as caught:
        web.call("users.info", {"user": "U0ADA0001"}, write=write)
    assert caught.value.retry_after == 7.0


def test_a_429_without_a_usable_retry_after_waits_a_second(server):
    web, _, replies = server
    replies["users.info"] = (429, {"Retry-After": "soon"}, {"ok": False, "error": "ratelimited"})
    with pytest.raises(RateLimited) as caught:
        web.call("users.info", {}, write=False)
    assert caught.value.retry_after == 1.0


def test_a_refused_read_names_slacks_code_and_nothing_else(server):
    web, _, replies = server
    replies["conversations.history"] = (200, {}, {"ok": False, "error": "not_in_channel", "detail": TOKEN})
    with pytest.raises(HeinzelError, match=r"conversations.history \(not_in_channel\)") as caught:
        web.call("conversations.history", {}, write=False)
    assert TOKEN not in str(caught.value)


@pytest.mark.parametrize(("code", "kind"), [("channel_not_found", SlackRefused), ("internal_error", SlackUnknown)])
def test_a_failed_write_is_a_refusal_only_when_slack_says_so_definitely(server, code, kind):
    web, _, replies = server
    replies["chat.postMessage"] = (200, {}, {"ok": False, "error": code})
    with pytest.raises(kind):
        web.call("chat.postMessage", {"channel": "C0CHAN0001", "text": "hi"}, write=True)


@pytest.mark.parametrize(
    ("write", "kind", "match"), [(False, HeinzelError, "did not answer"), (True, SlackUnknown, "may")]
)
def test_a_dead_connection_is_a_safe_error(write, kind, match):
    web = SdkWeb(TOKEN, 1, base_url="http://127.0.0.1:9/")
    with pytest.raises(kind, match=match) as caught:
        web.call("auth.test", {}, write=write)
    assert TOKEN not in str(caught.value)


def test_pages_refuse_a_malformed_page():
    class Odd:
        def call(self, method, params, *, write):
            return {"ok": True, "messages": {"not": "a list"}}

    with pytest.raises(HeinzelError, match="invalid page"):
        list(Web(Odd()).pages("conversations.history", {}, "messages"))


def test_a_429_response_is_closed_not_left_to_the_garbage_collector(server, monkeypatch):
    from urllib.error import HTTPError

    closed: list[int] = []
    original = HTTPError.close

    def close(self):
        closed.append(self.code)
        original(self)

    monkeypatch.setattr(HTTPError, "close", close)
    web, _, replies = server
    replies["users.info"] = (429, {"Retry-After": "3"}, {"ok": False, "error": "ratelimited"})
    with pytest.raises(RateLimited):
        web.call("users.info", {}, write=False)
    assert closed == [429]


def test_the_closing_handler_never_asks_for_a_retry():
    from urllib.error import HTTPError

    from heinzel_slack._sdk import CloseHttpError
    from heinzel_slack._vendor.slack_sdk.http_retry.request import HttpRequest
    from heinzel_slack._vendor.slack_sdk.http_retry.state import RetryState

    error = HTTPError("http://127.0.0.1/", 503, "down", {}, None)  # type: ignore[arg-type]
    request = HttpRequest(method="POST", url="http://127.0.0.1/", headers={})
    handler = CloseHttpError()
    for attempt in range(3):
        assert not handler.can_retry(state=RetryState(current_attempt=attempt), request=request, error=error)
    assert not handler.can_retry(state=RetryState(), request=request, error=RuntimeError("no response"))
