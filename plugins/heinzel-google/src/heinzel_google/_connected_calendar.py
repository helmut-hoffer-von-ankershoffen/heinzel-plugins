"""Unregistered Google Calendar connected-read service for a reviewed host capability grant.

The host must resolve this concrete service from the selected installed module, validate the owning personal
session and consume a separate exact human approval. This module never registers or issues a grant.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Never, SupportsIndex

from heinzel import (
    Config,
    ConnectedReadLease,
    ConnectedReadMethod,
    ConnectedReadReview,
    ConnectedReadService,
    CurrentUser,
    HeinzelError,
    Kernel,
    ModuleRecord,
    Window,
    capability_read_schema,
)
from heinzel.kernel import CapabilitySettings
from pydantic import JsonValue

from heinzel_google import _captured_source_enabled
from heinzel_google._calendar import GoogleCalendar
from heinzel_google._existing_lease import ReadWindow
from heinzel_google._gws import GoogleSession, Gws, Process
from heinzel_google._selected_gws import SelectedCapturedGwsRead, source_digest

_OPERATION = "capability-method:calendar.events"
_SOURCE_FILES = (
    "__init__.py",
    "_calendar.py",
    "_captured_mail.py",
    "_captured_artifact.py",
    "_connected_calendar.py",
    "_connected_mail.py",
    "_connected_artifact.py",
    "_documents.py",
    "_docs.py",
    "_sheets.py",
    "_existing_lease.py",
    "_gws.py",
    "_models.py",
    "_mail.py",
    "_module.py",
    "_selected_gws.py",
    "_token_exchange.py",
)


def _source_revision(lease: SelectedCapturedGwsRead, version: str) -> str:
    selection = lease.selection
    root = Path(__file__).parent
    source = {
        "selected": str(selection.command),
        "binary": str(selection.binary),
        "binary_sha256": selection.binary_sha256,
        "wrapper": selection.wrapper,
        "plugin_version": version,
        "files": {name: source_digest(root / name) for name in _SOURCE_FILES},
    }
    encoded = json.dumps(source, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class _OwnerBinding:
    kernel: Kernel
    record: ModuleRecord
    current: CurrentUser


def _check_binding(binding: _OwnerBinding, capability: str = "calendar") -> None:
    kernel, record, current = binding.kernel, binding.record, binding.current
    config = Config.load(Path.home()).settings(CapabilitySettings, "capabilities")
    original = kernel.capability_settings
    selected, _provider = kernel.selected_capability_provider(capability)
    if (
        selected is not record
        or kernel.resolve(CurrentUser) is not current
        or config.bound(capability) != original.bound(capability)
        or config.configured(capability) != original.configured(capability)
    ):
        msg = "The selected Google calendar connection changed"
        raise HeinzelError(msg)


class _CalendarSourceGuard(Gws):
    """Recheck the reviewed implementation source before each provider page."""

    def __init__(self, lease: SelectedCapturedGwsRead, version: str, source: str, binding: _OwnerBinding) -> None:
        self._lease, self._version, self._source, self._binding = lease, version, source, binding

    def run(self, executable: str, arguments: Sequence[str], timeout: float) -> Process:
        """Run a single page only with the same source snapshot.

        Raises:
            HeinzelError: If source continuity cannot be confirmed.
        """
        _check_binding(self._binding)
        if _source_revision(self._lease, self._version) != self._source:
            msg = "The Google read implementation changed"
            raise HeinzelError(msg)
        return self._lease.run(executable, arguments, timeout)


class _CalendarReadLease(ConnectedReadLease):
    """One bound source/account/window; constructing and inspecting it is not approval."""

    def __init__(
        self, binding: _OwnerBinding, session: GoogleSession, session_id: str, fixed: dict[str, JsonValue]
    ) -> None:
        current, record = binding.current, binding.record
        self._binding = binding
        self._current, self._session_id, self._version = current, session_id, record.origin.version
        self._fixed = json.loads(json.dumps(fixed, ensure_ascii=True, allow_nan=False))
        self._owner = current.principal().id
        self._session = session
        self._window = self._parse_window(fixed)
        self._lease = SelectedCapturedGwsRead(current, session)
        try:
            identity = self._lease.inspect_identity()
            scopes = self._lease.observed_scopes()
            self._lease.bind_review(identity, self._window, scopes)
            self._identity = identity
            self._scopes = scopes
            self._source = _source_revision(self._lease, self._version)
        except BaseException:
            self._lease.discard()
            raise

    def __repr__(self) -> str:
        return "<GoogleCalendarReadLease private>"

    def __reduce_ex__(self, _protocol: SupportsIndex) -> Never:
        msg = "A private Google connection lease cannot be serialized"
        raise TypeError(msg)

    @staticmethod
    def _parse_window(fixed: dict[str, JsonValue]) -> ReadWindow:
        try:
            if (
                set(fixed) != {"window"}
                or not isinstance(fixed["window"], dict)
                or set(fixed["window"]) != {"since", "until"}
            ):
                raise ValueError  # noqa: TRY301
            window = Window.model_validate(fixed["window"])
            if window.model_dump(mode="json") != fixed["window"]:
                raise ValueError  # noqa: TRY301
            return ReadWindow(window.since, window.until)
        except (ValueError, TypeError):
            msg = "The Google calendar window is invalid"
            raise HeinzelError(msg) from None

    def review(self) -> ConnectedReadReview:
        """Observe the same source and account; the host compares this with its exact approved review.

        Raises:
            HeinzelError: If the owner, source, identity or observed scopes changed.
        """
        _check_binding(self._binding)
        if self._current.principal().id != self._owner or _source_revision(self._lease, self._version) != self._source:
            msg = "The Google connection source changed"
            raise HeinzelError(msg)
        identity = self._lease.inspect_identity()
        scopes = self._lease.observed_scopes()
        if identity != self._identity or scopes != self._scopes:
            msg = "The Google connection account or scopes changed"
            raise HeinzelError(msg)
        _, schema_sha256 = capability_read_schema("calendar", "events")
        return ConnectedReadReview(
            owner=self._owner,
            session=self._session_id,
            operation=_OPERATION,
            schema_sha256=schema_sha256,
            source_revision=self._source,
            account_identity=identity.permission_id,
            account_display=identity.email,
            provider_scopes=scopes,
            fixed_arguments=self._fixed,
        )

    def read(self, arguments: Mapping[str, JsonValue]) -> JsonValue:
        """Read only the fixed reviewed primary-calendar window; no dynamic arguments or writes.

        Raises:
            HeinzelError: If arguments, source or account differ.
        """
        if arguments:
            msg = "The approved Google calendar read accepts no dynamic arguments"
            raise HeinzelError(msg)
        self.review()
        guarded = _CalendarSourceGuard(self._lease, self._version, self._source, self._binding)
        session = GoogleSession(self._session.settings, guarded)
        events = GoogleCalendar(session).events(Window(since=self._window.since, until=self._window.until))
        return [event.model_dump(mode="json") for event in events]

    def close(self) -> None:
        """Close the private lease; ordinary deletion is not secure erasure."""
        self._lease.close()


class GoogleConnectedReadService(ConnectedReadService):
    """Concrete owner-bound service, intentionally not registered until independent review."""

    def __init__(self, kernel: Kernel, current: CurrentUser) -> None:
        if not _captured_source_enabled:
            msg = "The Google captured read requires host-verified source loading"
            raise HeinzelError(msg)
        self._kernel, self._current = kernel, current
        try:
            record = kernel.module("google")
        except KeyError:
            msg = "The selected Google module is unavailable"
            raise HeinzelError(msg) from None
        if record.origin.distribution != "heinzel-google" or kernel.resolve(CurrentUser) is not current:
            msg = "The selected Google service source is unavailable"
            raise HeinzelError(msg)
        self._record = record
        self._binding = _OwnerBinding(kernel, record, current)
        self._session = kernel.resolve_registered_service(GoogleSession, record)

    def supported_reads(self) -> tuple[ConnectedReadMethod, ...]:
        """Declare captured calendar events and mail metadata reads; this grants no access."""
        return (
            ConnectedReadMethod(capability="calendar", method="events"),
            ConnectedReadMethod(capability="mail", method="messages"),
            ConnectedReadMethod(capability="documents", method="read"),
        )

    def open_lease(self, session: str, operation: str, fixed_arguments: Mapping[str, JsonValue]) -> ConnectedReadLease:
        """Capture an owner connection for the exact fixed read, never granting access itself.

        Raises:
            HeinzelError: If the operation, source or request is unsupported.
        """
        if operation == "capability-method:documents.read":
            from heinzel_google._connected_artifact import ArtifactReadLease  # noqa: PLC0415 - avoids circular source binding

            _check_binding(self._binding, "documents")
            if self._kernel.resolve_registered_service(GoogleSession, self._record) is not self._session:
                msg = "The selected Google read is unavailable"
                raise HeinzelError(msg)
            return ArtifactReadLease(self._binding, self._session, session, dict(fixed_arguments))
        if operation == "capability-method:mail.messages":
            from heinzel_google._connected_mail import MailReadLease  # noqa: PLC0415 - avoids circular source binding

            _check_binding(self._binding, "mail")
            if self._kernel.resolve_registered_service(GoogleSession, self._record) is not self._session:
                msg = "The selected Google read is unavailable"
                raise HeinzelError(msg)
            return MailReadLease(self._binding, self._session, session, dict(fixed_arguments))
        _check_binding(self._binding)
        if (
            operation != _OPERATION
            or self._kernel.resolve_registered_service(GoogleSession, self._record) is not self._session
        ):
            msg = "The selected Google read is unavailable"
            raise HeinzelError(msg)
        return _CalendarReadLease(self._binding, self._session, session, dict(fixed_arguments))
