"""TLS and proxy helpers keep credentials off logs while preserving the real protocol bytes."""

import base64
import logging
import ssl
from threading import Lock

import pytest

from heinzel_slack._vendor.slack_sdk import proxy_env_variable_loader
from heinzel_slack._vendor.slack_sdk.socket_mode.builtin import internals
from heinzel_slack._vendor.slack_sdk.socket_mode.builtin.connection import Connection
from heinzel_slack._vendor.slack_sdk.web.internal_utils import _build_req_args

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("pending", [None, b"", b"pending"])
def test_newline_preserves_present_partial_message_including_empty_bytes(pending):
    messages = internals._fetch_messages(
        [],
        receive=lambda: b"",
        logger=logging.getLogger("transport-proof"),
        remaining_bytes=b"\n",
        current_data=pending,
    )
    expected = [] if pending is None else [(None, pending)]
    assert messages == [*expected, (None, b"\n")]


@pytest.mark.parametrize(
    ("client", "query_token", "body_token", "expected"),
    [
        ("client", None, None, "client"),
        ("client", "query", None, "query"),
        ("client", None, "body", "body"),
        ("client", "query", "body", "body"),
    ],
)
def test_request_token_precedence_and_payload_removal(client, query_token, body_token, expected):
    request = _build_req_args(
        token=client,
        http_verb="POST",
        files=None,
        data=None,
        default_params={},
        params={"token": query_token} if query_token else None,
        json={"token": body_token} if body_token else None,
        headers={},
        auth=None,
        ssl=None,
        proxy=None,
    )
    assert request["headers"]["Authorization"] == f"Bearer {expected}"
    assert "token" not in (request["params"] or {}) and "token" not in (request["json"] or {})


class CapturedSocket:
    """Record network operations without opening any socket."""

    def __init__(self):
        self.sent = []

    def setsockopt(self, *_args):
        pass

    def send(self, data):
        self.sent.append(data)
        return len(data)


class CapturedTLS:
    """Record whether the SDK wraps the raw connection before returning it."""

    def __init__(self, secured):
        self.secured = secured
        self.calls = []

    def wrap_socket(self, sock, **kwargs):
        self.calls.append((sock, kwargs))
        return self.secured


@pytest.fixture
def transport(monkeypatch):
    raw, secured = CapturedSocket(), CapturedSocket()
    context = CapturedTLS(secured)
    connected = []

    def connect(address, timeout):
        connected.append((address, timeout))
        return raw

    monkeypatch.setattr(internals.socket, "create_connection", connect)
    return raw, secured, context, connected


def establish(context, *, port=443, proxy=None, trace=False):
    return internals._establish_new_socket_connection(
        session_id="fictional-session",
        server_hostname="socket.example.invalid",
        server_port=port,
        logger=logging.getLogger("transport-proof"),
        sock_send_lock=Lock(),
        receive_timeout=7,
        proxy=proxy,
        proxy_headers=None,
        trace_enabled=trace,
        ssl_context=context,
    )


@pytest.mark.parametrize("port", [443, 8443, 80])
def test_every_direct_endpoint_port_uses_tls_before_protocol_data(transport, port):
    raw, secured, context, connected = transport
    assert establish(context, port=port) is secured
    assert connected == [(("socket.example.invalid", port), 7)]
    assert raw.sent == []
    assert context.calls == [
        (
            raw,
            {
                "do_handshake_on_connect": True,
                "suppress_ragged_eofs": True,
                "server_hostname": "socket.example.invalid",
            },
        )
    ]


@pytest.mark.parametrize("port", [443, 8443, 80])
def test_failed_tls_never_returns_or_retries_a_plaintext_socket(transport, monkeypatch, port):
    raw, _secured, context, connected = transport

    def deny(*_args, **_kwargs):
        raise ssl.SSLCertVerificationError("synthetic certificate rejection")

    monkeypatch.setattr(context, "wrap_socket", deny)
    with pytest.raises(ssl.SSLCertVerificationError, match="synthetic certificate rejection"):
        establish(context, port=port)
    assert len(connected) == 1 and raw.sent == []


@pytest.mark.parametrize("status", [200, 407])
@pytest.mark.parametrize("trace", [True, False])
def test_proxy_connect_keeps_wire_auth_but_never_logs_or_raises_credentials(
    transport, monkeypatch, caplog, status, trace
):
    raw, secured, context, connected = transport
    proxy = "http://fictional-user:fictional-password@proxy.example.invalid:8080"
    encoded = base64.b64encode(b"fictional-user:fictional-password").decode()
    # A failed proxy may echo request headers. Raw response text must not reach logs either.
    monkeypatch.setattr(internals, "_parse_connect_response", lambda sock: (status, f"echo {proxy} {encoded}"))
    caplog.set_level(logging.DEBUG)
    if status == 200:
        assert establish(context, port=8443, proxy=proxy, trace=trace) is secured
        assert context.calls[0][1]["server_hostname"] == "socket.example.invalid"
        error = ""
    else:
        with pytest.raises(Exception, match="connect status code: 407") as caught:
            establish(context, port=8443, proxy=proxy, trace=trace)
        error = str(caught.value)
        assert context.calls == []
    assert connected == [(("proxy.example.invalid", 8080), 7)]
    assert len(raw.sent) == 1
    assert raw.sent[0].startswith(b"CONNECT socket.example.invalid:8443 HTTP/1.0\r\n")
    assert f"Proxy-Authorization: Basic {encoded}".encode() in raw.sent[0]
    for secret in (proxy, "fictional-user", "fictional-password", encoded, "Proxy-Authorization"):
        assert secret not in caplog.text + error


def test_proxy_environment_selection_does_not_log_its_credentials(monkeypatch, caplog):
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        monkeypatch.delenv(name, raising=False)
    proxy = "http://fictional-user:fictional-password@proxy.example.invalid:8080"
    monkeypatch.setenv("HTTPS_PROXY", proxy)
    caplog.set_level(logging.DEBUG)
    assert proxy_env_variable_loader.load_http_proxy_from_env() == proxy
    assert "loaded from an env variable" in caplog.text
    assert "fictional-user" not in caplog.text and "fictional-password" not in caplog.text


def test_supported_python_default_context_already_requires_verified_tls_12_or_newer():
    context = internals._use_or_create_ssl_context()
    assert context.minimum_version >= ssl.TLSVersion.TLSv1_2
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.parametrize("trace", [False, True])
@pytest.mark.parametrize("response", ["secret-status", "missing-status", "invalid-utf8"])
def test_real_connection_never_logs_malformed_proxy_response_contents(transport, monkeypatch, caplog, trace, response):
    raw, _secured, context, _connected = transport
    secret = base64.b64encode(b"fictional-user:fictional-password").decode()
    lines = {
        "secret-status": f"HTTP/1.0 {secret} Malformed\r\n\r\n".encode(),
        "missing-status": f"{secret}\r\n\r\n".encode(),
        "invalid-utf8": b"HTTP/1.0 \xff" + secret.encode() + b"\r\n\r\n",
    }
    received = iter(lines[response])
    monkeypatch.setattr(raw, "recv", lambda _count: bytes([next(received)]), raising=False)
    caplog.set_level(logging.DEBUG)
    errors = []
    connection = Connection(
        "wss://socket.example.invalid/socket",
        logging.getLogger("malformed-proxy-proof"),
        proxy="http://fictional-user:fictional-password@proxy.example.invalid:8080",
        trace_enabled=trace,
        ssl_context=context,
        on_error_listener=errors.append,
    )
    connection.connect()
    assert connection.sock is None and context.calls == []
    assert len(errors) == 1 and isinstance(errors[0], ConnectionError)
    assert str(errors[0]) == "Malformed proxy CONNECT response"
    assert errors[0].__suppress_context__ is True
    assert "Malformed proxy CONNECT response" in caplog.text
    for marker in (secret, "fictional-password", "fictional-user", "invalid literal", "UnicodeDecodeError"):
        assert marker not in caplog.text
    assert len(raw.sent) == 1 and secret.encode() in raw.sent[0]
