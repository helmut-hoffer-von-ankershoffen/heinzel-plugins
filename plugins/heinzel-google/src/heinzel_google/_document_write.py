"""Source-bound conditional writes into existing Docs and Slides through the owner's captured connection.

The host owns the exact draft and approval. Docs and Slides enforce `writeControl.requiredRevisionId`.
Sheets append and new-file helpers are retained, but cannot satisfy that host contract and are refused
before capture. Existing Slides sections are likewise refused: only an explicit end/new-slide insertion
is implemented. Document insertions preserve the selected URL tab in the request and subsequent readback.
"""

from __future__ import annotations

import hashlib
import json
import threading
from typing import TYPE_CHECKING, ClassVar, cast
from urllib.parse import parse_qsl, urlsplit

if TYPE_CHECKING:
    from collections.abc import Callable

    from heinzel_google._existing_lease import DriveIdentity

from heinzel import CurrentUser, HeinzelError, Kernel
from heinzel.kernel import (
    CapturedWriteAcknowledgement,
    CapturedWriteDraft,
    CapturedWriteLease,
    CapturedWriteReview,
    CapturedWriteService,
    CapturedWriteTarget,
)

from heinzel_google._captured_artifact import CapturedArtifact
from heinzel_google._connected_artifact import artifact_target as _target
from heinzel_google._connected_calendar import OwnerBinding as _OwnerBinding
from heinzel_google._connected_calendar import check_owner_binding as _check_binding
from heinzel_google._connected_calendar import connected_source_revision as _source_revision
from heinzel_google._existing_lease import exchange_captured_token as _exchange_token
from heinzel_google._existing_lease import invalid_json_constant as _invalid_constant
from heinzel_google._existing_lease import serialized_capture as _serialized
from heinzel_google._existing_lease import unique_json_pairs as _unique_pairs
from heinzel_google._gws import GoogleSession

_TIMEOUT = 60.0
_END = "end"
_NEW = "new:"
_NEW_REVISION = "new"
_SCOPE = {
    "document": "https://www.googleapis.com/auth/documents",
    "spreadsheet": "https://www.googleapis.com/auth/spreadsheets",
    "presentation": "https://www.googleapis.com/auth/presentations",
}
_COMMANDS = {
    "document": ("docs", "documents"),
    "spreadsheet": ("sheets", "spreadsheets"),
    "presentation": ("slides", "presentations"),
}
_EDITOR = {
    "document": "https://docs.google.com/document/d/{}/edit",
    "spreadsheet": "https://docs.google.com/spreadsheets/d/{}/edit",
    "presentation": "https://docs.google.com/presentation/d/{}/edit",
}


class _Writer(CapturedArtifact):
    """Owner-bound requests for one kind of file; nothing else can be asked of it."""

    def __init__(self, current: CurrentUser, session: GoogleSession, kind: str) -> None:
        self.validate_source: Callable[[], None] | None = None
        self.write_kind = kind
        super().__init__(current, session)

    def _exchange(self, exported: bytes) -> tuple[str, float, tuple[str, ...]]:  # type: ignore[override]
        return _exchange_token(exported, artifact=f"{self.write_kind}-write")

    def _json(self, arguments: list[str]) -> dict[str, object]:
        result = self._read(arguments, _TIMEOUT)
        if result.exit_code != 0 or result.truncated:
            msg = "Google refused this request; check the file and your access"
            raise HeinzelError(msg)
        body = json.loads(result.stdout, object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
        if not isinstance(body, dict):
            msg = "Google returned an unexpected reply"
            raise HeinzelError(msg)
        return cast("dict[str, object]", body)

    @_serialized
    def call(
        self, command: tuple[str, ...], params: dict[str, object], body: object | None = None
    ) -> dict[str, object]:
        """One host-chosen request; the adapter below is the only caller."""
        if self.validate_source is not None:
            self.validate_source()
        args = [*command, "--params", json.dumps(params)]
        if body is not None:
            args += ["--json", json.dumps(body)]
        return self._json([*args, "--format", "json"])


def _revision(writer: _Writer, kind: str, file_id: str) -> tuple[str, dict[str, object]]:
    """Observe only file metadata; content is read separately during exact draft review."""
    if kind == "document":
        fields = "documentId,revisionId"
        data = writer.call(("docs", "documents", "get"), {"documentId": file_id, "fields": fields})
        return str(data.get("revisionId", "")), data
    if kind == "presentation":
        data = writer.call(("slides", "presentations", "get"), {"presentationId": file_id, "fields": "revisionId"})
        return str(data.get("revisionId", "")), data
    data = writer.call(("drive", "files", "get"), {"fileId": file_id, "fields": "version", "supportsAllDrives": True})
    return str(data.get("version", "")), data


def _paragraph_end(structure: dict[str, object], heading: str) -> int:
    """The index just after the first paragraph whose text is exactly `heading`.

    Raises:
        HeinzelError: If no paragraph has that text.
    """
    body = structure.get("body")
    content: object = cast("dict[str, object]", body).get("content", []) if isinstance(body, dict) else []
    for candidate in cast("list[object]", content) if isinstance(content, list) else []:
        if not isinstance(candidate, dict):
            continue
        element = cast("dict[str, object]", candidate)
        paragraph = element.get("paragraph")
        if not isinstance(paragraph, dict):
            continue
        runs = cast("dict[str, object]", paragraph).get("elements", [])
        text = _body_text(runs)
        end = element.get("endIndex")
        if text.strip() == heading.strip() and type(end) is int:
            return end
    msg = "The heading to insert after is not in the document"
    raise HeinzelError(msg)


def _requested_tab(reference: str) -> str | None:
    parts = urlsplit(reference)
    hints = dict(parse_qsl(parts.query) + parse_qsl(parts.fragment))
    return hints.get("tab")


def _document_context(
    writer: _Writer, file_id: str, selected: str | None, revision: str | None = None
) -> tuple[str, dict[str, object]]:
    """Resolve the exact selected tab, including nested tabs; never fall back for an absent selection.

    Raises:
        HeinzelError: If the tab is absent, malformed or no longer at the approved revision.
    """
    document = writer.call(
        ("docs", "documents", "get"),
        {"documentId": file_id, "includeTabsContent": True, "fields": "documentId,revisionId,tabs"},
    )
    if document.get("documentId") != file_id:
        msg = "Google did not return the exact selected document"
        raise HeinzelError(msg)
    if revision is not None and document.get("revisionId") != revision:
        msg = "The Google document changed since this draft"
        raise HeinzelError(msg)
    roots = document.get("tabs")
    pending: list[object] = list(cast("list[object]", roots)) if isinstance(roots, list) else []
    tabs: dict[str, dict[str, object]] = {}
    while pending:
        tab = pending.pop(0)
        if not isinstance(tab, dict):
            break
        tab = cast("dict[str, object]", tab)
        properties = tab.get("tabProperties")
        identity = cast("dict[str, object]", properties).get("tabId") if isinstance(properties, dict) else None
        content = tab.get("documentTab")
        children = tab.get("childTabs", [])
        if not isinstance(identity, str) or not identity or identity in tabs or not isinstance(content, dict):
            break
        if not isinstance(children, list):
            break
        tabs[identity] = cast("dict[str, object]", content)
        pending[0:0] = cast("list[object]", children)
    else:
        identity = selected if selected is not None else next(iter(tabs), None)
        if isinstance(identity, str) and identity in tabs:
            return identity, tabs[identity]
    msg = "The selected Google document tab is unavailable"
    raise HeinzelError(msg)


def _body_text(value: object) -> str:
    if isinstance(value, dict):
        value = cast("dict[str, object]", value)
        run = value.get("textRun")
        content = cast("dict[str, object]", run).get("content") if isinstance(run, dict) else None
        if isinstance(content, str):
            return content
        return "".join(_body_text(child) for child in value.values())
    if isinstance(value, list):
        return "".join(_body_text(child) for child in cast("list[object]", value))
    return ""


def _write_document(  # noqa: PLR0913 - exact mutation, revision and selected-tab authority
    writer: _Writer, file_id: str, section: str, text: str, revision: str | None, *, tab_id: str | None = None
) -> None:
    """Insert only in the selected tab using the approved revision, then inspect that same tab.

    Raises:
        HeinzelError: If the tab, revision, heading or subsequent readback does not match.
    """
    tab_id, structure = _document_context(writer, file_id, tab_id, revision)
    location: dict[str, object]
    if section == _END:
        location = {"endOfSegmentLocation": {"tabId": tab_id}}
        inserted = f"\n{text}\n"
    else:
        location = {"location": {"index": _paragraph_end(structure, section), "tabId": tab_id}}
        inserted = f"{text}\n"
    body: dict[str, object] = {"requests": [{"insertText": {**location, "text": inserted}}]}
    if revision is not None:
        body["writeControl"] = {"requiredRevisionId": revision}
    writer.call(("docs", "documents", "batchUpdate"), {"documentId": file_id}, body)
    _, observed = _document_context(writer, file_id, tab_id)
    if _body_text(observed.get("body")).count(inserted) <= _body_text(structure.get("body")).count(inserted):
        msg = "The Google document write could not be confirmed in its selected tab; inspect before drafting again"
        raise HeinzelError(msg)


def _write_rows(writer: _Writer, file_id: str, section: str, text: str) -> None:
    rows = [line.split("\t") for line in text.splitlines()]
    params: dict[str, object] = {
        "spreadsheetId": file_id,
        "range": "A1" if section == _END else f"'{section}'!A1",
        "valueInputOption": "RAW",
        "insertDataOption": "INSERT_ROWS",
    }
    writer.call(("sheets", "spreadsheets", "values", "append"), params, {"values": rows})


def _write_slide(writer: _Writer, file_id: str, text: str, revision: str | None) -> None:
    identity = "hz" + hashlib.sha256(text.encode()).hexdigest()[:24]
    box = identity + "b"
    size = {"magnitude": 8000000, "unit": "EMU"}
    body: dict[str, object] = {
        "requests": [
            {"createSlide": {"objectId": identity}},
            {
                "createShape": {
                    "objectId": box,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": identity,
                        "size": {"width": size, "height": {"magnitude": 4000000, "unit": "EMU"}},
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": 500000,
                            "translateY": 500000,
                            "unit": "EMU",
                        },
                    },
                }
            },
            {"insertText": {"objectId": box, "text": text}},
        ]
    }
    if revision is not None:
        body["writeControl"] = {"requiredRevisionId": revision}
    writer.call(("slides", "presentations", "batchUpdate"), {"presentationId": file_id}, body)


def _new_kind(reference: str) -> str | None:
    if not reference.startswith(_NEW):
        return None
    kind = reference.removeprefix(_NEW).split(":", maxsplit=1)[0]
    if kind not in _SCOPE:
        msg = "This kind of file can't be created"
        raise HeinzelError(msg)
    return kind


def _write_account(identity: DriveIdentity) -> str:
    if not identity.email:
        msg = "Google did not report the write account"
        raise HeinzelError(msg)
    return identity.email


class _WriteLease(CapturedWriteLease):
    def __init__(self, binding: _OwnerBinding, session: GoogleSession, draft: CapturedWriteDraft) -> None:
        self._binding, self._draft = binding, draft
        self._write_lock = threading.Lock()
        self._attempted = False
        self._owner = binding.current.principal().id
        self._created: str | None = None
        new = _new_kind(draft.reference)
        if new is None:
            self._kind, self._file_id = _target(draft.reference)
        else:
            self._kind, self._file_id = new, ""
        if new is not None or self._kind == "spreadsheet":
            msg = "Google captured writes require an existing Doc or Slides file with a provider revision precondition"
            raise HeinzelError(msg)
        if (
            draft.owner != self._owner
            or draft.provider != binding.record.qualname
            or draft.write_scope != _SCOPE[self._kind]
        ):
            msg = "The Google write owner, provider or scope does not match"
            raise HeinzelError(msg)
        if self._kind == "presentation" and draft.section != _END:
            msg = "Google Slides captured writes support section end (a new slide), not an existing slide or shape"
            raise HeinzelError(msg)
        if draft.operation != "insert-draft":
            msg = "Google captured writes support only the insert-draft operation"
            raise HeinzelError(msg)
        self._version = binding.record.origin.version
        self._lease = _Writer(binding.current, session, self._kind)
        try:
            self._identity = self._lease.inspect_identity()
            self._scopes = self._lease.observed_scopes()
            if new is None:
                self._lease.bind_artifact(self._identity, self._lease.observed_scopes(), self._file_id, self._kind)
            self._source = _source_revision(self._lease, self._version)
            self._lease.validate_source = self._validate_source
        except BaseException:
            self._lease.discard()
            raise

    def _validate_source(self) -> None:
        _check_binding(self._binding, "documents")
        if (
            self._binding.current.principal().id != self._owner
            or self._binding.record.origin.version != self._version
            or _source_revision(self._lease, self._version) != self._source
            or self._lease.inspect_identity() != self._identity
            or self._lease.observed_scopes() != self._scopes
        ):
            msg = "The Google write connection changed"
            raise HeinzelError(msg)

    def review(self) -> CapturedWriteReview:
        """Observe the file's current revision and the account again; this writes nothing.

        Raises:
            HeinzelError: If the connection changed.
        """
        _check_binding(self._binding, "documents")
        if (
            self._binding.current.principal().id != self._owner
            or self._binding.record.origin.version != self._version
            or self._lease.observed_scopes() != self._scopes
            or self._lease.inspect_identity() != self._identity
            or _source_revision(self._lease, self._version) != self._source
        ):
            msg = "The Google connection changed"
            raise HeinzelError(msg)
        if self._file_id:
            revision = _revision(self._lease, self._kind, self._file_id)[0]
        else:
            revision = self._created or _NEW_REVISION
        if not revision:
            msg = "Google did not report a conditional revision"
            raise HeinzelError(msg)
        draft = self._draft
        if self._kind == "document":
            _, structure = _document_context(self._lease, self._file_id, _requested_tab(draft.reference), revision)
            if draft.section != _END:
                _paragraph_end(structure, draft.section)
        elif self._kind == "presentation" and draft.section != _END:
            msg = "Google Slides captured writes support section end (a new slide), not an existing slide or shape"
            raise HeinzelError(msg)
        return CapturedWriteReview(
            owner=draft.owner,
            session=draft.session,
            provider=draft.provider,
            binding_id=draft.binding_id,
            account=_write_account(self._identity),
            source=self._source,
            reference=draft.reference,
            operation=draft.operation,
            section=draft.section,
            base_revision=revision,
            content_sha256=hashlib.sha256(draft.content.get_secret_value().encode()).hexdigest(),
            write_scope=_SCOPE[self._kind],
            conditional_mutation=True,
        )

    def _create(self, title: str, text: str) -> str:
        command = (*_COMMANDS[self._kind], "create")
        if self._kind == "spreadsheet":
            data = self._lease.call(command, {}, {"properties": {"title": title}})
            file_id = str(data.get("spreadsheetId", ""))
            _write_rows(self._lease, file_id, _END, text)
        elif self._kind == "presentation":
            data = self._lease.call(command, {}, {"title": title})
            file_id = str(data.get("presentationId", ""))
            _write_slide(self._lease, file_id, text, None)
        else:
            data = self._lease.call(command, {}, {"title": title})
            file_id = str(data.get("documentId", ""))
            _write_document(self._lease, file_id, _END, text, None)
        if not file_id:
            msg = "Google did not report the new file"
            raise HeinzelError(msg)
        return _EDITOR[self._kind].format(file_id)

    def write(self) -> CapturedWriteAcknowledgement:
        """Perform the one reviewed write; Docs and Slides refuse it if the file moved on.

        Raises:
            HeinzelError: If the file changed or Google refused.
        """
        with self._write_lock:
            return self._write_once()

    def _write_once(self) -> CapturedWriteAcknowledgement:
        if self._attempted:
            msg = "The Google write was already attempted; inspect the provider before drafting again"
            raise HeinzelError(msg)
        review = self.review()
        draft = self._draft
        if (review.account, review.source, review.base_revision) != (draft.account, draft.source, draft.base_revision):
            msg = "The Google write account, source or revision changed"
            raise HeinzelError(msg)
        self._attempted = True
        text = draft.content.get_secret_value()
        if not self._file_id:
            self._created = self._create(draft.section, text)
            return CapturedWriteAcknowledgement(reference=draft.reference, revision=self._created)
        if self._kind == "document":
            _write_document(
                self._lease,
                self._file_id,
                draft.section,
                text,
                draft.base_revision,
                tab_id=_requested_tab(draft.reference),
            )
        elif self._kind == "presentation":
            _write_slide(self._lease, self._file_id, text, draft.base_revision)
        else:
            if _revision(self._lease, self._kind, self._file_id)[0] != draft.base_revision:
                msg = "The spreadsheet changed since this draft"
                raise HeinzelError(msg)
            _write_rows(self._lease, self._file_id, draft.section, text)
        # A spreadsheet's Drive version keeps moving after a write, so it can't identify this one.
        return CapturedWriteAcknowledgement(reference=draft.reference)

    def close(self) -> None:
        self._lease.close()


class GoogleDocumentWrites(CapturedWriteService):
    """Conditional insertions into existing Docs and Slides; observation and capture are not approval."""

    supported_operations: ClassVar[frozenset[str]] = frozenset({"insert-draft"})

    def __init__(self, kernel: Kernel, current: CurrentUser) -> None:
        from heinzel_google import captured_source_enabled as _captured_source_enabled  # noqa: PLC0415

        if not _captured_source_enabled:
            msg = "The Google captured write requires host-verified source loading"
            raise HeinzelError(msg)
        self._kernel, self._current = kernel, current
        record = kernel.module("google")
        if record.origin.distribution != "heinzel-google" or kernel.resolve(CurrentUser) is not current:
            msg = "The selected Google write source is unavailable"
            raise HeinzelError(msg)
        self._binding = _OwnerBinding(kernel, record, current)
        self._session = kernel.resolve_registered_service(GoogleSession, record)

    def target(self, reference: str) -> CapturedWriteTarget:
        """Observe metadata for an existing conditional-write target.

        Raises:
            HeinzelError: If the target cannot enforce the reviewed revision.
        """
        _check_binding(self._binding, "documents")
        new = _new_kind(reference)
        if new is not None:
            msg = "Google file creation has no provider revision precondition"
            raise HeinzelError(msg)
        kind, file_id = (new, "") if new is not None else _target(reference)
        if kind == "spreadsheet":
            msg = "Google Sheets append has no provider revision precondition"
            raise HeinzelError(msg)
        lease = _Writer(self._current, self._session, kind)
        try:
            identity = lease.inspect_identity()
            if file_id:
                lease.bind_artifact(identity, lease.observed_scopes(), file_id, kind)
                revision = _revision(lease, kind, file_id)[0]
            else:
                revision = _NEW_REVISION
            source = _source_revision(lease, self._binding.record.origin.version)
        finally:
            lease.discard()
        return CapturedWriteTarget(
            account=_write_account(identity),
            source=source,
            reference=reference,
            base_revision=revision,
            write_scope=_SCOPE[kind],
        )

    def open_lease(self, draft: CapturedWriteDraft) -> CapturedWriteLease:
        """Capture exact reviewed terms without writing."""
        return _WriteLease(self._binding, self._session, draft)


# Shared provider-local primitives; the draft companion retains the same captured connection and validation.
DocumentWriter = _Writer
document_body_text = _body_text
document_context = _document_context
requested_document_tab = _requested_tab
observe_document_revision = _revision
write_account = _write_account
DOCUMENT_WRITE_SCOPE = _SCOPE["document"]
