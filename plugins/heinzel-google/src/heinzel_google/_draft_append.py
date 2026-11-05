"""Conditional marked draft appends through the captured owner-selected Google connection.

The section is a logical rolling feed at the end of the selected document tab. Each draft starts with the
host's visible review marker. No text replacement, file creation or sharing request is admitted here.
"""

from __future__ import annotations

import hashlib
import re
import threading
from typing import TYPE_CHECKING, ClassVar, cast

from heinzel import CurrentUser, HeinzelError, Kernel
from heinzel.kernel import (
    DraftAppendAttempt,
    DraftAppendLease,
    DraftAppendReceipt,
    DraftAppendReview,
    DraftAppendService,
    DraftAppendTarget,
    DraftSectionSnapshot,
)
from pydantic import SecretStr

from heinzel_google._connected_artifact import artifact_target as _target
from heinzel_google._connected_calendar import (
    OwnerBinding as _OwnerBinding,
)
from heinzel_google._connected_calendar import (
    check_owner_binding as _check_binding,
)
from heinzel_google._connected_calendar import (
    connected_source_revision as _source_revision,
)
from heinzel_google._document_write import (
    DOCUMENT_WRITE_SCOPE,
)
from heinzel_google._document_write import (
    DocumentWriter as _Writer,
)
from heinzel_google._document_write import (
    document_body_text as _body_text,
)
from heinzel_google._document_write import (
    document_context as _document_context,
)
from heinzel_google._document_write import (
    observe_document_revision as _revision,
)
from heinzel_google._document_write import (
    requested_document_tab as _requested_tab,
)
from heinzel_google._document_write import (
    write_account as _write_account,
)

if TYPE_CHECKING:
    from heinzel_google._gws import GoogleSession

_MARKER = "\nDRAFT — awaiting your review\n"
_SECTION = "release-poems"


def _document(reference: str, section: str) -> str:
    kind, file_id = _target(reference)
    if kind != "document" or section != _SECTION:
        msg = "Marked drafts require an existing Google Doc and section release-poems"
        raise HeinzelError(msg)
    return file_id


class _AppendLease(DraftAppendLease):
    def __init__(
        self,
        binding: _OwnerBinding,
        session: GoogleSession,
        reference: str,
        section: str,
        attempt: DraftAppendAttempt | None = None,
    ) -> None:
        self._reference, self._section = reference, section
        self._file_id = _document(reference, section)
        self._lock, self._attempted = threading.RLock(), False
        self._attempt = attempt
        self._binding = binding
        _check_binding(self._binding, "documents")
        self._owner = self._binding.current.principal().id
        self._version = self._binding.record.origin.version
        self._writer = _Writer(self._binding.current, session, "document")
        try:
            self._identity = self._writer.inspect_identity()
            self._scopes = self._writer.observed_scopes()
            self._writer.bind_artifact(self._identity, self._scopes, self._file_id, "document")
            self._source = _source_revision(self._writer, self._version)
            self._writer.validate_source = self._validate
        except BaseException:
            self._writer.discard()
            raise

    def _validate(self) -> None:
        _check_binding(self._binding, "documents")
        if (
            self._binding.current.principal().id != self._owner
            or self._binding.record.origin.version != self._version
            or self._writer.inspect_identity() != self._identity
            or self._writer.observed_scopes() != self._scopes
            or _source_revision(self._writer, self._version) != self._source
        ):
            msg = "The captured Google draft connection changed"
            raise HeinzelError(msg)

    def observe(self) -> tuple[DraftAppendTarget, str, str]:
        self._validate()
        revision, metadata = _revision(self._writer, "document", self._file_id)
        if not revision or metadata.get("documentId") != self._file_id:
            msg = "Google did not attest the exact document and revision"
            raise HeinzelError(msg)
        tab, structure = _document_context(self._writer, self._file_id, _requested_tab(self._reference), revision)
        return (
            DraftAppendTarget(
                account=_write_account(self._identity),
                source=self._source,
                reference=self._reference,
                resource_id=self._file_id,
                section=self._section,
                revision=revision,
                write_scope=DOCUMENT_WRITE_SCOPE,
                conditional_append=True,
            ),
            tab,
            _body_text(structure.get("body")),
        )

    def review(self) -> DraftAppendReview:
        """Observe the exact current account, tab and provider revision without writing."""
        with self._lock:
            attempt = self._require_attempt()
            target, _, _ = self.observe()
            return DraftAppendReview(
                draft_key=attempt.draft_key,
                target=target,
                text_sha256=hashlib.sha256(attempt.text.get_secret_value().encode()).hexdigest(),
                append_only=True,
            )

    def _require_attempt(self) -> DraftAppendAttempt:
        if self._attempt is None:
            msg = "No marked append was captured"
            raise HeinzelError(msg)
        return self._attempt

    def append(self) -> DraftAppendReceipt:
        """Insert exactly once at the tab end, with Google's requiredRevisionId precondition.

        Raises:
            HeinzelError: If terms changed, the acknowledgement is uncertain or a retry is attempted.
        """
        with self._lock:
            if self._attempted:
                msg = "This append was already attempted; inspect the document before any new draft"
                raise HeinzelError(msg)
            attempt = self._require_attempt()
            target, tab, prior = self.observe()
            if target != attempt.target or attempt.owner != self._owner:
                msg = "The exact Google append owner, account, source, target or revision changed"
                raise HeinzelError(msg)
            marker = f"\nDraft: {attempt.draft_key}\n"
            if marker in prior:
                msg = "This marked draft already exists; refusing another append"
                raise HeinzelError(msg)
            self._attempted = True
            # Only this acknowledgement can establish delivery; no readback upgrades an uncertain result.
            reply = self._writer.call(
                ("docs", "documents", "batchUpdate"),
                {"documentId": self._file_id},
                {
                    "writeControl": {"requiredRevisionId": target.revision},
                    "requests": [
                        {
                            "insertText": {
                                "endOfSegmentLocation": {"tabId": tab},
                                "text": attempt.text.get_secret_value(),
                            }
                        }
                    ],
                },
            )
            control = reply.get("writeControl")
            revision = (
                cast("dict[str, object]", control).get("requiredRevisionId") if isinstance(control, dict) else None
            )
            if reply.get("documentId") != self._file_id or not isinstance(revision, str) or not revision:
                msg = "Google did not acknowledge the exact append; do not retry"
                raise HeinzelError(msg)
            return DraftAppendReceipt(draft_key=attempt.draft_key, reference=target.reference, revision=revision)

    def close(self) -> None:
        """Wait for the synchronous request and release captured credentials."""
        with self._lock:
            self._writer.close()


class GoogleDraftAppends(DraftAppendService):
    """Source-captured rolling Google Doc append and exact human-edited marked section capture."""

    supported_operations: ClassVar[frozenset[str]] = frozenset({"append-marked-draft"})

    def __init__(self, kernel: Kernel, current: CurrentUser) -> None:
        from heinzel_google import captured_source_enabled  # noqa: PLC0415
        from heinzel_google._gws import GoogleSession  # noqa: PLC0415

        record = kernel.module("google")
        if (
            not captured_source_enabled
            or record.origin.distribution != "heinzel-google"
            or kernel.resolve(CurrentUser) is not current
        ):
            msg = "Marked Google appends require the host-verified owner source"
            raise HeinzelError(msg)
        self._binding = _OwnerBinding(kernel, record, current)
        self._session = kernel.resolve_registered_service(GoogleSession, record)

    def target(self, reference: str, section: str) -> DraftAppendTarget:
        """Observe the supplied existing rolling document without creating it or a section."""
        lease = _AppendLease(self._binding, self._session, reference, section)
        try:
            return lease.observe()[0]
        finally:
            lease.close()

    def open_lease(self, attempt: DraftAppendAttempt) -> DraftAppendLease:
        """Capture only one host-marked section; no write is performed.

        Raises:
            HeinzelError: If the supplied text does not carry one exact host draft marker.
        """
        text = attempt.text.get_secret_value()
        if (
            not text.startswith(_MARKER)
            or text.count(_MARKER) != 1
            or text.count(f"\nDraft: {attempt.draft_key}\n") != 1
            or len(re.findall(r"^Draft: [0-9a-f]{64}$", text, re.MULTILINE)) != 1
        ):
            msg = "The append must contain exactly one host-marked draft section"
            raise HeinzelError(msg)
        return _AppendLease(self._binding, self._session, attempt.target.reference, attempt.target.section, attempt)

    def capture(self, target: DraftAppendTarget, draft_key: str) -> DraftSectionSnapshot:
        """Read the complete marked draft, including human edits, at a newly observed exact revision.

        Raises:
            HeinzelError: If the identity changed, the marker is missing or ambiguous, or a section was corrupted.
        """
        if re.fullmatch(r"[0-9a-f]{64}", draft_key) is None:
            msg = "The draft key is invalid"
            raise HeinzelError(msg)
        lease = _AppendLease(self._binding, self._session, target.reference, target.section)
        try:
            observed, _, text = lease.observe()
            if observed.model_copy(update={"revision": target.revision}) != target:
                msg = "The exact Google draft capture account, source or target changed"
                raise HeinzelError(msg)
            sections = [(_MARKER + part) for part in text.split(_MARKER)[1:]]
            matches = [part for part in sections if f"\nDraft: {draft_key}\n" in part]
            if len(matches) != 1 or matches[0].count(f"\nDraft: {draft_key}\n") != 1:
                msg = "The edited marked draft section is missing or ambiguous"
                raise HeinzelError(msg)
            return DraftSectionSnapshot(draft_key=draft_key, target=observed, text=SecretStr(matches[0]))
        finally:
            lease.close()
