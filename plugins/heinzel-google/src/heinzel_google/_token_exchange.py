"""Isolated bounded OAuth exchange helper, invoked with private input on stdin."""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus
from typing import override

_LIMIT = 32_768
_SCOPES = (
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
)
_MAIL_SCOPES = (
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    # Gmail disallows the bounded list query with gmail.metadata; the lease separately restricts commands to metadata.
    "https://www.googleapis.com/auth/gmail.readonly",
)

_METADATA = "https://www.googleapis.com/auth/drive.metadata.readonly"
ARTIFACT_SCOPES = {
    "document": (_METADATA, "https://www.googleapis.com/auth/documents.readonly"),
    "spreadsheet": (_METADATA, "https://www.googleapis.com/auth/spreadsheets.readonly"),
    "presentation": (_METADATA, "https://www.googleapis.com/auth/presentations.readonly"),
    "document-write": (_METADATA, "https://www.googleapis.com/auth/documents"),
    "spreadsheet-write": (_METADATA, "https://www.googleapis.com/auth/spreadsheets"),
    "presentation-write": (_METADATA, "https://www.googleapis.com/auth/presentations"),
}


BROADER = {
    "https://www.googleapis.com/auth/drive.metadata.readonly": "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar.readonly": "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly": "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/documents.readonly": "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets.readonly": "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/presentations.readonly": "https://www.googleapis.com/auth/presentations",
}
"""Google refuses a refresh that asks for a scope the sign-in did not name, even a narrower one. A person signed in
with the broader scope gets a token for that one service: it could write, so the lease runs only its fixed reads."""


def covered(required: tuple[str, ...], granted: set[str]) -> bool:
    """Whether every required scope, or the broader one Google granted in its place, is in `granted`."""
    return all(scope in granted or BROADER.get(scope) in granted for scope in required)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    @override
    def redirect_request(self, req: object, fp: object, code: int, msg: str, headers: object, newurl: str) -> None:
        del req, fp, code, msg, headers, newurl


def exchange(data: bytes, *, mail: bool = False, artifact: str | None = None) -> bytes:
    """Send one fixed HTTPS token request without proxy, redirects, or diagnostic logging.

    Raises:
        ValueError: If the response is invalid or oversized.
        urllib.error.HTTPError: If Google refuses in a way other than a scope it won't narrow.
    """
    creds = json.loads(data)
    scopes = ARTIFACT_SCOPES[artifact] if artifact else _MAIL_SCOPES if mail else _SCOPES
    try:
        return _refresh(creds, scopes)
    except urllib.error.HTTPError as refused:
        if refused.code != HTTPStatus.BAD_REQUEST:
            raise
    return _refresh(creds, tuple(BROADER.get(scope, scope) for scope in scopes))


def _refresh(creds: dict[str, str], scopes: tuple[str, ...]) -> bytes:
    payload = urllib.parse.urlencode(
        {
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": creds["refresh_token"],
            "grant_type": "refresh_token",
            "scope": " ".join(scopes),
        }
    ).encode()
    request = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    with opener.open(request, timeout=10) as response:
        if response.status != HTTPStatus.OK:
            msg = "OAuth token request failed"
            raise ValueError(msg)
        raw: bytes = response.read(_LIMIT + 1)
    if len(raw) > _LIMIT:
        msg = "OAuth response too large"
        raise ValueError(msg)
    return raw


def main() -> int:
    """Read only bounded private input, emit bounded response, suppress all errors."""
    try:
        data = sys.stdin.buffer.read(_LIMIT + 1)
        if len(data) > _LIMIT:
            return 1
        if sys.argv[1:] not in ([], ["mail"], *([kind] for kind in ARTIFACT_SCOPES)):
            return 1
        sys.stdout.buffer.write(
            exchange(
                data,
                mail=sys.argv[1:] == ["mail"],
                artifact=sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "mail" else None,
            )
        )
    except Exception:  # noqa: BLE001 - the helper must never print secret diagnostics
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
