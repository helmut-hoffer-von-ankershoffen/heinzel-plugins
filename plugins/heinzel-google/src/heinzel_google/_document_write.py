"""One reviewed write through the owner's own connection: into a Doc, Sheet or Slides file, or a new file.

The draft and the approval live in the host. This adapter observes the target and performs that exact write. Docs and
Slides use `writeControl.requiredRevisionId`, so Google refuses a write if the file changed after the owner reviewed it.
Sheets have no such control: the host rechecks the file's version just before, and a row is only ever appended. Text is
literal: nothing in it is interpreted, and it cannot reach any other file.
"""

import hashlib
import json

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
from heinzel_google._connected_artifact import _target
from heinzel_google._connected_calendar import _check_binding, _OwnerBinding, _source_revision
from heinzel_google._existing_lease import _exchange_token, _invalid_constant, _serialized, _unique_pairs
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
        return body

    @_serialized
    def call(
        self, command: tuple[str, ...], params: dict[str, object], body: object | None = None
    ) -> dict[str, object]:
        """One host-chosen request; the adapter below is the only caller."""
        args = [*command, "--params", json.dumps(params)]
        if body is not None:
            args += ["--json", json.dumps(body)]
        return self._json([*args, "--format", "json"])


def _revision(writer: _Writer, kind: str, file_id: str) -> tuple[str, dict[str, object]]:
    """The revision Google reports for this file, and its structure where the write needs it."""
    if kind == "document":
        fields = "documentId,revisionId,body(content(endIndex,paragraph(elements(textRun(content)))))"
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
    content = body.get("content", []) if isinstance(body, dict) else []
    for element in content if isinstance(content, list) else []:
        paragraph = element.get("paragraph") if isinstance(element, dict) else None
        if not isinstance(paragraph, dict):
            continue
        runs = paragraph.get("elements", [])
        text = "".join(str(run.get("textRun", {}).get("content", "")) for run in runs if isinstance(run, dict))
        end = element.get("endIndex")
        if text.strip() == heading.strip() and type(end) is int:
            return end
    msg = "The heading to insert after is not in the document"
    raise HeinzelError(msg)


def _write_document(writer: _Writer, file_id: str, section: str, text: str, revision: str | None) -> None:
    location: dict[str, object]
    if section == _END:
        location, inserted = {"endOfSegmentLocation": {}}, f"\n{text}\n"
    else:
        _rev, structure = _revision(writer, "document", file_id)
        location, inserted = {"location": {"index": _paragraph_end(structure, section)}}, f"{text}\n"
    body: dict[str, object] = {"requests": [{"insertText": {**location, "text": inserted}}]}
    if revision is not None:
        body["writeControl"] = {"requiredRevisionId": revision}
    writer.call(("docs", "documents", "batchUpdate"), {"documentId": file_id}, body)


def _write_rows(writer: _Writer, file_id: str, section: str, text: str) -> None:
    rows = [line.split("\t") for line in text.splitlines()]
    params = {
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


class _WriteLease(CapturedWriteLease):
    def __init__(self, binding: _OwnerBinding, session: GoogleSession, draft: CapturedWriteDraft) -> None:
        self._binding, self._draft = binding, draft
        self._created: str | None = None
        new = _new_kind(draft.reference)
        if new is None:
            self._kind, self._file_id = _target(draft.reference)
        else:
            self._kind, self._file_id = new, ""
        self._version = binding.record.origin.version
        self._lease = _Writer(binding.current, session, self._kind)
        try:
            self._identity = self._lease.inspect_identity()
            if new is None:
                self._lease.bind_artifact(self._identity, self._lease.observed_scopes(), self._file_id, self._kind)
            self._source = _source_revision(self._lease, self._version)
        except BaseException:
            self._lease.discard()
            raise

    def review(self) -> CapturedWriteReview:
        """Observe the file's current revision and the account again; this writes nothing.

        Raises:
            HeinzelError: If the connection changed.
        """
        _check_binding(self._binding, "documents")
        if (
            self._lease.inspect_identity() != self._identity
            or _source_revision(self._lease, self._version) != self._source
        ):
            msg = "The Google connection changed"
            raise HeinzelError(msg)
        if self._file_id:
            revision = _revision(self._lease, self._kind, self._file_id)[0]
        else:
            revision = self._created or _NEW_REVISION
        draft = self._draft
        return CapturedWriteReview(
            owner=draft.owner,
            session=draft.session,
            provider=draft.provider,
            binding_id=draft.binding_id,
            account=self._identity.email,
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
        draft = self._draft
        text = draft.content.get_secret_value()
        if not self._file_id:
            self._created = self._create(draft.section, text)
            return CapturedWriteAcknowledgement(reference=draft.reference, revision=self._created)
        if self._kind == "document":
            _write_document(self._lease, self._file_id, draft.section, text, draft.base_revision)
        elif self._kind == "presentation":
            _write_slide(self._lease, self._file_id, text, draft.base_revision)
        else:
            if _revision(self._lease, self._kind, self._file_id)[0] != draft.base_revision:
                msg = "The spreadsheet changed since this draft"
                raise HeinzelError(msg)
            _write_rows(self._lease, self._file_id, draft.section, text)
        revision = _revision(self._lease, self._kind, self._file_id)[0]
        return CapturedWriteAcknowledgement(reference=draft.reference, revision=revision or None)

    def close(self) -> None:
        self._lease.close()


class GoogleDocumentWrites(CapturedWriteService):
    """Drafts into Google Docs, Sheets and Slides; a target observation and a lease are not approval."""

    def __init__(self, kernel: Kernel, current: CurrentUser) -> None:
        self._kernel, self._current = kernel, current
        record = kernel.module("google")
        self._binding = _OwnerBinding(kernel, record, current)
        self._session = kernel.resolve_registered_service(GoogleSession, record)

    def target(self, reference: str) -> CapturedWriteTarget:
        """Observe the account and current revision, without writing; a new file has no revision yet."""
        new = _new_kind(reference)
        kind, file_id = (new, "") if new is not None else _target(reference)
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
            account=identity.email,
            source=source,
            reference=reference,
            base_revision=revision,
            write_scope=_SCOPE[kind],
        )

    def open_lease(self, draft: CapturedWriteDraft) -> CapturedWriteLease:
        """Capture exact reviewed terms without writing."""
        return _WriteLease(self._binding, self._session, draft)
