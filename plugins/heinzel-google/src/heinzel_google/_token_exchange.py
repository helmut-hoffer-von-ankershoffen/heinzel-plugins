"""Isolated bounded OAuth exchange helper, invoked with private input on stdin."""

import json
import sys
import urllib.parse
import urllib.request
from http import HTTPStatus
from typing import Literal, override

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

_DOC_SCOPES = (
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
)
_SHEET_SCOPES = (
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    @override
    def redirect_request(self, req: object, fp: object, code: int, msg: str, headers: object, newurl: str) -> None:
        del req, fp, code, msg, headers, newurl


def exchange(data: bytes, *, mail: bool = False, artifact: Literal["document", "spreadsheet"] | None = None) -> bytes:
    """Send one fixed HTTPS token request without proxy, redirects, or diagnostic logging.

    Raises:
        ValueError: If the response is invalid or oversized.
    """
    creds = json.loads(data)
    payload = urllib.parse.urlencode(
        {
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": creds["refresh_token"],
            "grant_type": "refresh_token",
            "scope": " ".join(
                _DOC_SCOPES
                if artifact == "document"
                else _SHEET_SCOPES
                if artifact == "spreadsheet"
                else _MAIL_SCOPES
                if mail
                else _SCOPES
            ),
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
        if sys.argv[1:] not in ([], ["mail"], ["document"], ["spreadsheet"]):
            return 1
        sys.stdout.buffer.write(
            exchange(
                data,
                mail=sys.argv[1:] == ["mail"],
                artifact="document"
                if sys.argv[1:] == ["document"]
                else "spreadsheet"
                if sys.argv[1:] == ["spreadsheet"]
                else None,
            )
        )
    except Exception:  # noqa: BLE001 - the helper must never print secret diagnostics
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
