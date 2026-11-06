"""Actual SDK requests retain proxy snapshots and never publish credential diagnostics."""

import io
import json
import logging
import socket
import urllib.request
from email.message import Message
from urllib.response import addinfourl

import pytest
from heinzel import HeinzelError

from heinzel_slack import _sdk, _slack
from heinzel_slack._vendor.slack_sdk.socket_mode.builtin.client import IntervalRunner

pytestmark = pytest.mark.integration
PROXY_NAMES = ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy")
TICKET = "wss://socket.example.invalid/socket?ticket=fictional-private-ticket"


@pytest.fixture(autouse=True)
def no_network_or_ambient_proxy(monkeypatch):
    for name in PROXY_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(socket, "create_connection", lambda *_a, **_kw: pytest.fail("unexpected network"))
    monkeypatch.setattr(IntervalRunner, "start", lambda self: self)


@pytest.mark.parametrize(
    "factory",
    [lambda: _slack.WebApi("fictional-bot", 3), lambda: _slack.SocketListener("fictional-app").start(lambda _: None)],
)
@pytest.mark.parametrize(
    "proxy",
    [
        "https://fictional-user:fictional-password@proxy.example.invalid:443",
        "https://proxy.example.invalid:443",
        "socks5://proxy.example.invalid:1080",
        "http://fictional-user:fictional-password@proxy.example.invalid:80",
        "http://fictional-user@proxy.example.invalid",
        "http://",
        "http://proxy.example.invalid:99999",
        "http://proxy.example.invalid/path",
        "http://proxy.example.invalid?secret=fictional",
        "http://proxy.example.invalid#fragment",
        "http://proxy.example.invalid\n",
    ],
)
def test_unsupported_proxy_is_refused_before_sdk_construction(monkeypatch, caplog, factory, proxy):
    monkeypatch.setenv("HTTPS_PROXY", proxy)
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(_sdk, "WebClient", lambda **_kw: pytest.fail("constructed WebClient before validation"))
    monkeypatch.setattr(_slack, "SocketModeClient", lambda **_kw: pytest.fail("constructed socket before validation"))
    with pytest.raises(HeinzelError, match="unauthenticated HTTP proxy") as error:
        factory()
    assert proxy not in str(error.value) + caplog.text
    assert "fictional-password" not in str(error.value) + caplog.text


@pytest.fixture
def http_transport(monkeypatch):
    seen = []

    def open_https(_self, request):
        seen.append(request)
        headers = Message()
        headers["Content-Type"] = "application/json"
        body = {"ok": True, "url": TICKET, "team_id": "T0TEAM001", "user_id": "U0BOT0001", "team": "Example"}
        response = addinfourl(io.BytesIO(json.dumps(body).encode()), headers, request.full_url, 200)
        response.msg = "OK"
        return response

    monkeypatch.setattr(urllib.request.HTTPSHandler, "https_open", open_https)
    monkeypatch.setattr(urllib.request, "proxy_bypass", lambda _host: False)
    # A direct or explicit snapshot must not ask urllib to discover late OS/env proxies.
    monkeypatch.setattr(urllib.request, "getproxies", lambda: pytest.fail("late proxy discovery"))
    return seen


@pytest.mark.parametrize("proxy", [None, "http://proxy.example.invalid:8080"])
@pytest.mark.parametrize("level", [logging.WARNING, logging.DEBUG])
def test_real_web_and_socket_ticket_requests_keep_snapshot_and_private_logs(
    monkeypatch, caplog, http_transport, proxy, level
):
    if proxy:
        monkeypatch.setenv("HTTPS_PROXY", proxy)
    caplog.set_level(level)
    root = logging.getLogger()
    before_handlers = tuple(root.handlers)
    web = _slack.WebApi("fictional-bot", 3)
    captured = []
    original_init = _slack.SocketModeClient.__init__

    def construct(client, *args, **kwargs):
        # Simulate ambient configuration changing during constructor fallback.
        monkeypatch.setenv("HTTPS_PROXY", "https://fictional-user:fictional-password@late.example.invalid")
        original_init(client, *args, **kwargs)

    def connect(client):
        captured.append(client)
        assert client.issue_new_wss_url() == TICKET

    monkeypatch.setattr(_slack.SocketModeClient, "__init__", construct)
    monkeypatch.setattr(_slack.SocketModeClient, "connect", connect)
    listener = _slack.SocketListener("fictional-app")
    try:
        listener.start(lambda _: None)
        client = captured[0]
        assert client.proxy == client.web_client.proxy == web._client.proxy == proxy
        assert client.trace_enabled is False
        assert client.logger is client.web_client.logger is web._client.logger is _sdk.SDK_LOGGER
        assert web.identity().team_id == "T0TEAM001"
        assert len(http_transport) == 2
        for request in http_transport:
            assert request.host == ("proxy.example.invalid:8080" if proxy else "slack.com")
            assert request.get_header("Proxy-authorization") is None
        for secret in (TICKET, "fictional-private-ticket", "fictional-app", "fictional-bot", "fictional-password"):
            assert secret not in caplog.text
        assert tuple(root.handlers) == before_handlers
        assert root.level == level
        assert _sdk.SDK_LOGGER.name not in logging.Logger.manager.loggerDict
    finally:
        listener.stop()


def test_web_constructor_environment_fallback_is_reset_to_the_validated_direct_snapshot(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "https://fictional-user:fictional-password@late.example.invalid")
    client = _sdk.sdk_web_client(proxy=None)
    assert client.proxy is None and client.logger is _sdk.SDK_LOGGER


@pytest.mark.parametrize("proxy", [None, "http://proxy.example.invalid:8080"])
def test_real_socket_connection_uses_snapshot_after_environment_changes(monkeypatch, http_transport, proxy):
    from heinzel_slack._vendor.slack_sdk.socket_mode.builtin import connection, internals

    if proxy:
        monkeypatch.setenv("HTTPS_PROXY", proxy)
    raw_sent, tls_sent, destinations, wrapped = [], [], [], []

    class Wire:
        def __init__(self, sent):
            self.sent = sent

        def send(self, data):
            self.sent.append(data)
            return len(data)

        def setsockopt(self, *_args):
            pass

        def close(self):
            pass

    raw, secured = Wire(raw_sent), Wire(tls_sent)

    class TLS:
        def wrap_socket(self, sock, **kwargs):
            wrapped.append((sock, kwargs["server_hostname"]))
            return secured

    def dial(address, _timeout=None, **_kwargs):
        destinations.append(address)
        return raw

    monkeypatch.setattr(internals.socket, "create_connection", dial)
    monkeypatch.setattr(internals.ssl, "create_default_context", TLS)
    monkeypatch.setattr(internals, "_parse_connect_response", lambda _sock: (200, "HTTP/1.0 200 OK"))
    monkeypatch.setattr(connection, "_parse_handshake_response", lambda _sock: (101, {}, ""))
    monkeypatch.setattr(connection, "_validate_sec_websocket_accept", lambda *_args: True)
    original_init = _slack.SocketModeClient.__init__

    def construct(client, *args, **kwargs):
        monkeypatch.setenv("HTTPS_PROXY", "https://fictional-user:fictional-password@late.example.invalid")
        original_init(client, *args, **kwargs)

    monkeypatch.setattr(_slack.SocketModeClient, "__init__", construct)
    listener = _slack.SocketListener("fictional-app")
    try:
        listener.start(lambda _: None)
        assert listener._client.is_connected()
        assert destinations == [("proxy.example.invalid", 8080) if proxy else ("socket.example.invalid", 443)]
        assert wrapped == [(raw, "socket.example.invalid")]
        assert tls_sent[0].startswith(b"GET /socket?ticket=fictional-private-ticket HTTP/1.1")
        assert len(tls_sent) == 2  # verified TLS handshake request followed by masked ping
        assert len(raw_sent) == (1 if proxy else 0)
        if proxy:
            assert raw_sent[0].startswith(b"CONNECT socket.example.invalid:443 HTTP/1.0")
            assert b"Proxy-Authorization" not in raw_sent[0]
        assert all(b"fictional-private-ticket" not in message for message in raw_sent)
        assert len(http_transport) == 1
    finally:
        listener.stop()
