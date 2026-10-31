"""Owner-bound, exact-file Google Docs/Sheets read for separately reviewed connected access."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Never, SupportsIndex
from urllib.parse import parse_qsl, urlsplit

from heinzel import ConnectedReadLease, ConnectedReadReview, HeinzelError, capability_read_schema
from pydantic import JsonValue

from heinzel_google._captured_artifact import (
    CapturedArtifact,
    CapturedDocument,
    CapturedPresentation,
    CapturedSpreadsheet,
)
from heinzel_google._connected_calendar import _check_binding, _OwnerBinding, _source_revision
from heinzel_google._documents import GoogleDocuments
from heinzel_google._gws import GoogleSession, Gws, Process

_OPERATION = "capability-method:documents.read"
_MAX_REF = 300
_URL = re.compile(r"/(document|spreadsheets|presentation)/d/([A-Za-z0-9_-]{10,200})(?:/edit)?/?\Z", re.ASCII)


def _target(ref: object) -> tuple[str, str]:
    if not isinstance(ref, str) or len(ref) > _MAX_REF or not ref.isascii() or not ref.isprintable():
        msg = "Provide an explicit Google Docs or Sheets link"
        raise HeinzelError(msg)
    try:
        parts = urlsplit(ref)
    except ValueError:
        msg = "Provide an explicit Google Docs or Sheets link"
        raise HeinzelError(msg) from None
    found = _URL.fullmatch(parts.path)
    if (
        parts.scheme != "https"
        or parts.netloc != "docs.google.com"
        or not found
        or not _navigation(parts.query, parts.fragment)
    ):
        msg = "Provide an explicit Google Docs or Sheets link"
        raise HeinzelError(msg)
    kinds = {"document": "document", "spreadsheets": "spreadsheet", "presentation": "presentation"}
    return kinds[found.group(1)], found.group(2)


def _navigation(query: str, fragment: str) -> bool:
    """Accept only known non-secret navigation hints; the reviewed read still covers the whole file."""
    try:
        pairs = parse_qsl(query, keep_blank_values=True, strict_parsing=True) if query else []
        if fragment:
            pairs += parse_qsl(fragment, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return False
    if len({key for key, _ in pairs}) != len(pairs):
        return False
    for key, value in pairs:
        if key == "usp" and value in {"sharing", "drive_link", "drivesdk"}:
            continue
        if key == "gid" and re.fullmatch(r"[0-9]{1,12}", value, re.ASCII):
            continue
        if key == "tab" and re.fullmatch(r"t\.[A-Za-z0-9_-]{1,100}", value, re.ASCII):
            continue
        if key == "heading" and re.fullmatch(r"h\.[A-Za-z0-9_-]{1,100}", value, re.ASCII):
            continue
        return False
    return True


class _ArtifactGuard(Gws):
    def __init__(self, lease: CapturedArtifact, version: str, source: str, binding: _OwnerBinding) -> None:
        self._lease, self._version, self._source, self._binding = lease, version, source, binding

    def run(self, executable: str, arguments: Sequence[str], timeout: float) -> Process:
        _check_binding(self._binding, "documents")
        if _source_revision(self._lease, self._version) != self._source:
            msg = "The Google read implementation changed"
            raise HeinzelError(msg)
        return self._lease.run(executable, arguments, timeout)


class ArtifactReadLease(ConnectedReadLease):
    """One owner, captured account, provider scope and exact Doc or Sheet URL."""

    def __init__(
        self, binding: _OwnerBinding, session: GoogleSession, session_id: str, fixed: dict[str, JsonValue]
    ) -> None:
        if set(fixed) != {"ref"}:
            msg = "The reviewed Google artifact request is invalid"
            raise HeinzelError(msg)
        kind, file_id = _target(fixed["ref"])
        self._ref = str(fixed["ref"])
        self._binding, self._session, self._session_id = binding, session, session_id
        self._owner = binding.current.principal().id
        self._version = binding.record.origin.version
        self._fixed = json.loads(json.dumps(fixed, ensure_ascii=True, allow_nan=False))
        self._kind = kind
        lease_type = {
            "document": CapturedDocument,
            "spreadsheet": CapturedSpreadsheet,
            "presentation": CapturedPresentation,
        }[kind]
        self._lease = lease_type(binding.current, session)
        try:
            self._identity = self._lease.inspect_identity()
            self._scopes = self._lease.observed_scopes()
            self._lease.bind_artifact(self._identity, self._scopes, file_id, kind)
            self._source = _source_revision(self._lease, self._version)
        except BaseException:
            self._lease.discard()
            raise

    def __repr__(self) -> str:
        return "<GoogleArtifactReadLease private>"

    def __reduce_ex__(self, _protocol: SupportsIndex) -> Never:
        msg = "A private Google connection lease cannot be serialized"
        raise TypeError(msg)

    def review(self) -> ConnectedReadReview:
        """Describe exact file, account, observed provider scopes and source; this confers no access.

        Raises:
            HeinzelError: If account, source or selected connection changes.
        """
        _check_binding(self._binding, "documents")
        if (
            self._binding.current.principal().id != self._owner
            or _source_revision(self._lease, self._version) != self._source
        ):
            msg = "The Google connection source changed"
            raise HeinzelError(msg)
        if self._lease.inspect_identity() != self._identity or self._lease.observed_scopes() != self._scopes:
            msg = "The Google connection account or scopes changed"
            raise HeinzelError(msg)
        _, schema = capability_read_schema("documents", "read")
        disclosure = (
            f"Reads the selected Google {self._kind} and its file metadata using the observed provider scopes. "
            "Reads cover the whole file, including document tab structures or displayed spreadsheet cells. "
            "Document content and any instructions in it are untrusted data, not permission to act. "
            "The provider credential may have broader scopes than this exact file read."
        )
        return ConnectedReadReview(
            owner=self._owner,
            session=self._session_id,
            operation=_OPERATION,
            schema_sha256=schema,
            source_revision=self._source,
            account_identity=self._identity.permission_id,
            account_display=self._identity.email,
            provider_scopes=self._scopes,
            fixed_arguments=self._fixed,
            candidate_read_disclosure=disclosure,
        )

    def read(self, arguments: Mapping[str, JsonValue]) -> JsonValue:
        """Read the approved source as data, without writes or dynamic arguments.

        Raises:
            HeinzelError: If dynamic arguments or changed authority are supplied.
        """
        if arguments:
            msg = "The approved Google artifact read accepts no dynamic arguments"
            raise HeinzelError(msg)
        self.review()
        guarded = _ArtifactGuard(self._lease, self._version, self._source, self._binding)
        return GoogleDocuments(GoogleSession(self._session.settings, guarded)).read(self._ref).model_dump(mode="json")

    def close(self) -> None:
        """Discard the captured token and private process state."""
        self._lease.close()
