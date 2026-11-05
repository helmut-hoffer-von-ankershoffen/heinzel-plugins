"""OAuth helpers keep fixed destinations, bounded private I/O and refusal-specific scope fallback."""

import io
import json
import urllib.error
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from heinzel_google import _token_exchange as tokens

pytestmark = pytest.mark.unit
CREDS = {"client_id": "fictional-client", "client_secret": "fictional-secret", "refresh_token": "fictional-refresh"}


@pytest.mark.parametrize("status", [401, 403, 503])
def test_non_scope_oauth_refusal_is_never_retried_with_broader_permissions(monkeypatch, status):
    refresh = Mock(
        side_effect=urllib.error.HTTPError("https://oauth2.googleapis.com/token", status, "refused", {}, None)
    )
    monkeypatch.setattr(tokens, "_refresh", refresh)
    with pytest.raises(urllib.error.HTTPError) as failure:
        tokens.exchange(json.dumps(CREDS).encode(), artifact="document")
    assert failure.value.code == status
    refresh.assert_called_once_with(
        CREDS,
        (
            "https://www.googleapis.com/auth/drive.metadata.readonly",
            "https://www.googleapis.com/auth/documents.readonly",
        ),
    )


def test_scope_refusal_fallback_stays_with_the_selected_document_service(monkeypatch):
    refusal = urllib.error.HTTPError("https://oauth2.googleapis.com/token", 400, "scope refused", {}, None)
    refresh = Mock(side_effect=[refusal, b'{"access_token":"fictional-access"}'])
    monkeypatch.setattr(tokens, "_refresh", refresh)
    assert tokens.exchange(json.dumps(CREDS).encode(), artifact="document") == b'{"access_token":"fictional-access"}'
    assert [call.args[1] for call in refresh.call_args_list] == [
        (
            "https://www.googleapis.com/auth/drive.metadata.readonly",
            "https://www.googleapis.com/auth/documents.readonly",
        ),
        ("https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/documents"),
    ]


@pytest.mark.parametrize(
    ("status", "payload", "message"), [(401, b"private", "failed"), (200, b"x" * 32769, "too large")]
)
def test_refresh_refuses_bad_status_and_oversized_private_response(monkeypatch, status, payload, message):
    response = SimpleNamespace(status=status, read=Mock(return_value=payload))

    class Reply:
        def __enter__(self):
            return response

        def __exit__(self, *args):
            return None

    requests = []

    def build(*handlers):
        assert len(handlers) == 2
        assert isinstance(handlers[0], tokens.urllib.request.ProxyHandler)
        assert handlers[0].proxies == {}
        assert isinstance(handlers[1], tokens._NoRedirect)

        def send(request, *, timeout):
            requests.append(request)
            assert request.full_url == "https://oauth2.googleapis.com/token"
            assert request.get_method() == "POST"
            assert timeout == 10
            assert CREDS["refresh_token"] not in request.full_url
            assert tokens.urllib.parse.parse_qs(request.data.decode()) == {
                "client_id": ["fictional-client"],
                "client_secret": ["fictional-secret"],
                "refresh_token": ["fictional-refresh"],
                "grant_type": ["refresh_token"],
                "scope": ["https://www.googleapis.com/auth/documents.readonly"],
            }
            return Reply()

        return SimpleNamespace(open=send)

    monkeypatch.setattr(tokens.urllib.request, "build_opener", build)
    with pytest.raises(ValueError, match=message):
        tokens._refresh(CREDS, ("https://www.googleapis.com/auth/documents.readonly",))
    assert len(requests) == 1
    if status == 401:
        response.read.assert_not_called()
    else:
        response.read.assert_called_once_with(32769)
    assert tokens._NoRedirect().redirect_request(None, None, 302, "move", {}, "https://other.example/token") is None


@pytest.mark.parametrize("arguments", [[], ["mail"], ["document"], ["document-write"]])
def test_helper_emits_only_the_private_exchange_response(monkeypatch, arguments):
    private = b'{"access_token":"fictional-access"}'
    stdout, stderr = io.BytesIO(), io.StringIO()
    monkeypatch.setattr(
        tokens,
        "sys",
        SimpleNamespace(
            argv=["helper", *arguments],
            stdin=SimpleNamespace(buffer=io.BytesIO(b"{}")),
            stdout=SimpleNamespace(buffer=stdout),
            stderr=stderr,
        ),
    )
    exchange = Mock(return_value=private)
    monkeypatch.setattr(tokens, "exchange", exchange)
    assert tokens.main() == 0
    exchange.assert_called_once_with(
        b"{}", mail=arguments == ["mail"], artifact=arguments[0] if arguments not in ([], ["mail"]) else None
    )
    assert stdout.getvalue() == private
    assert stderr.getvalue() == ""


@pytest.mark.parametrize(("arguments", "data"), [(["unknown"], b"{}"), ([], b"x" * 32769)])
def test_invalid_private_input_never_reaches_an_exchange(monkeypatch, arguments, data):
    stdout, stderr = io.BytesIO(), io.StringIO()
    monkeypatch.setattr(
        tokens,
        "sys",
        SimpleNamespace(
            argv=["helper", *arguments],
            stdin=SimpleNamespace(buffer=io.BytesIO(data)),
            stdout=SimpleNamespace(buffer=stdout),
            stderr=stderr,
        ),
    )
    exchange = Mock(side_effect=AssertionError("no exchange may start"))
    monkeypatch.setattr(tokens, "exchange", exchange)
    assert tokens.main() == 1
    exchange.assert_not_called()
    assert stdout.getvalue() == b""
    assert stderr.getvalue() == ""


def test_private_exchange_failure_emits_no_credential_diagnostic(monkeypatch):
    stdout, stderr = io.BytesIO(), io.StringIO()
    monkeypatch.setattr(
        tokens,
        "sys",
        SimpleNamespace(
            argv=["helper"],
            stdin=SimpleNamespace(buffer=io.BytesIO(b"{}")),
            stdout=SimpleNamespace(buffer=stdout),
            stderr=stderr,
        ),
    )
    monkeypatch.setattr(tokens, "exchange", Mock(side_effect=ValueError("fictional-refresh-secret")))
    assert tokens.main() == 1
    assert stdout.getvalue() == b""
    assert stderr.getvalue() == ""
