"""Private Gmail metadata-only lease bound to a reviewed query and captured account."""

import json
import math
import re
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from heinzel import CurrentUser, HeinzelError, MailQuery, Window

from heinzel_google._connected_items import MAX_ITEMS
from heinzel_google._existing_lease import (
    _MAX_CREDENTIAL_BYTES,
    _MAX_TIMEOUT,
    DriveIdentity,
    ReadWindow,
    _exchange_token,
    _invalid_constant,
    _serialized,
    _unique_pairs,
)
from heinzel_google._gws import GoogleSession, Process
from heinzel_google._mail import MAX_MESSAGES, _label_id, _line, gmail_search
from heinzel_google._selected_gws import SelectedCapturedGwsRead

_MAX_LABELS = 1000
_COMMAND_LENGTH = 8
_METADATA_FIELDS = "id,threadId,internalDate,labelIds,payload(headers)"

_ID = re.compile(r"[A-Za-z0-9_-]{1,100}\Z", re.ASCII)


class CapturedGmailRead(SelectedCapturedGwsRead):
    """Same pinned account lease, restricted to exact list query and metadata of listed messages."""

    def __init__(self, current: CurrentUser, session: GoogleSession) -> None:
        self._query: MailQuery | None = None
        self._labels: dict[str, str] = {}
        self._listed: set[str] = set()
        self._fetched: set[str] = set()
        super().__init__(current, session)

    @staticmethod
    def _exchange(exported: bytes) -> tuple[str, float, tuple[str, ...]]:
        return _exchange_token(exported, mail=True)

    @_serialized
    def bind_mail_review(
        self, identity: DriveIdentity, window: ReadWindow, scopes: tuple[str, ...], query: str
    ) -> None:
        """Bind exact query and identity; this does not itself confer human approval.

        Raises:
            HeinzelError: If the query or connection cannot be verified.
        """
        self.bind_review(identity, window, scopes)
        try:
            self._query = MailQuery.parse(query)
        except ValueError:
            self.discard()
            msg = "The reviewed mail query is invalid"
            raise HeinzelError(msg) from None
        self._labels.clear()
        self._listed.clear()
        self._fetched.clear()

    def _labels_read(self, args: list[str], params: dict[str, object], timeout: float) -> Process:
        if params != {"userId": "me"}:
            raise ValueError
        projected = [*args]
        projected[5] = json.dumps({**params, "fields": "labels(id,name)"}, separators=(",", ":"))
        result = self._read(projected, timeout)
        if result.exit_code == 0 and not result.truncated:
            payload = json.loads(result.stdout, object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
            labels = payload.get("labels", [])
            if not isinstance(labels, list) or len(labels) > _MAX_LABELS or set(payload) - {"labels"}:
                raise ValueError
            if any(not isinstance(item, dict) or set(item) - {"id", "name"} for item in labels):
                raise ValueError
            self._labels = {
                item["id"]: _line(item.get("name") or item["id"])
                for item in labels
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            }
        return result

    def _messages_read(self, args: list[str], params: dict[str, object], timeout: float) -> Process:
        if self._query is None or self._window is None:
            raise ValueError
        expected: dict[str, object] = {
            "userId": "me",
            "q": gmail_search(self._query, Window(since=self._window.since, until=self._window.until)),
            "maxResults": MAX_MESSAGES,
        }
        if self._query.label is not None:
            label = _label_id(self._query.label, self._labels)
            if label is None:
                raise ValueError
            expected["labelIds"] = [label]
        if {key: value for key, value in params.items() if key != "pageToken"} != expected:
            raise ValueError
        self._check_page_query(params)
        projected = [*args]
        projected[5] = json.dumps(
            {**params, "maxResults": MAX_ITEMS, "fields": "messages(id),nextPageToken"}, separators=(",", ":")
        )
        result = self._read_page(projected, timeout)
        if result.exit_code == 0 and not result.truncated:
            payload = json.loads(result.stdout, object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
            messages = payload.get("messages", [])
            if not isinstance(messages, list) or set(payload) - {"messages", "nextPageToken"}:
                raise ValueError
            for item in messages:
                if (
                    not isinstance(item, dict)
                    or set(item) - {"id"}
                    or not isinstance(item.get("id"), str)
                    or not _ID.fullmatch(item["id"])
                ):
                    raise ValueError
                self._listed.add(item["id"])
            if len(self._listed) > MAX_ITEMS:
                raise ValueError
        return result

    def _metadata_read(self, args: list[str], params: dict[str, object], timeout: float) -> Process:
        message = params.get("id")
        if (
            params
            != {"userId": "me", "id": message, "format": "metadata", "metadataHeaders": ["From", "To", "Cc", "Subject"]}
            or message not in self._listed
            or message in self._fetched
        ):
            raise ValueError
        projected = [*args]
        projected[5] = json.dumps({**params, "fields": _METADATA_FIELDS}, separators=(",", ":"))
        result = self._read(projected, timeout)
        if result.exit_code == 0 and not result.truncated:
            payload = json.loads(result.stdout, object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
            if not isinstance(payload, dict) or set(payload) - {
                "id",
                "threadId",
                "internalDate",
                "labelIds",
                "payload",
            }:
                raise ValueError
            body = payload.get("payload", {})
            if not isinstance(body, dict) or set(body) - {"headers"} or payload.get("id") != message:
                raise ValueError
            headers = body.get("headers", [])
            if not isinstance(headers, list) or any(
                not isinstance(header, dict)
                or set(header) != {"name", "value"}
                or not isinstance(header["name"], str)
                or header["name"].casefold() not in {"from", "to", "cc", "subject"}
                or not isinstance(header["value"], str)
                for header in headers
            ):
                raise ValueError
            self._fetched.add(message)
        return result

    def _version_read(self, args: list[str], timeout: float) -> Process:
        self._check_current()
        if self._temporary is None:
            msg = "The Google connection lease is closed"
            raise HeinzelError(msg)
        return self._run(
            str(self._executable), args, timeout, (self._source_env, self._temporary.name, _MAX_CREDENTIAL_BYTES)
        )

    def _dispatch(self, args: list[str], params: dict[str, object], timeout: float) -> Process:
        if args[:4] == ["gmail", "users", "labels", "list"]:
            return self._labels_read(args, params, timeout)
        if args[:4] == ["gmail", "users", "messages", "list"]:
            return self._messages_read(args, params, timeout)
        if args[:4] == ["gmail", "users", "messages", "get"]:
            return self._metadata_read(args, params, timeout)
        raise ValueError

    @_serialized
    def run(self, executable: str, arguments: Sequence[str], timeout: float) -> Process:
        """Run only the bound list and metadata reads; no writes, bodies or arbitrary message IDs.

        Raises:
            HeinzelError: If identity, command, query or provider results cannot be verified.
            ValueError: Invalid provider data is mapped to a safe error.
            TypeError: Invalid provider data is mapped to a safe error.
        """
        self._check_owner()
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= _MAX_TIMEOUT:
            msg = "The Google read timeout is invalid"
            raise HeinzelError(msg)
        if (
            Path(executable).resolve() != self.selection.command
            or self._identity is None
            or self._window is None
            or self._query is None
        ):
            msg = "The reviewed Google mail connection is unavailable"
            raise HeinzelError(msg)
        args = list(arguments)
        if args == ["--version"]:
            return self._version_read(args, timeout)
        try:
            if len(args) != _COMMAND_LENGTH or args[4] != "--params" or args[6:] != ["--format", "json"]:
                raise ValueError  # noqa: TRY301
            parsed = json.loads(args[5], object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
            if not isinstance(parsed, dict):
                raise TypeError  # noqa: TRY301
            params = cast("dict[str, object]", parsed)
            if self.inspect_identity() != self._identity:
                raise ValueError  # noqa: TRY301
            return self._dispatch(args, params, timeout)
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            self.discard()
            msg = "The Google mail read did not match its reviewed terms"
            raise HeinzelError(msg) from None
