"""Exact-file Docs/Sheets reads using one privately captured existing Google connection."""

import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from heinzel import HeinzelError

from heinzel_google._documents import KINDS
from heinzel_google._existing_lease import (
    _MAX_CREDENTIAL_BYTES,
    _MAX_TIMEOUT,
    DriveIdentity,
    _exchange_token,
    _invalid_constant,
    _serialized,
    _unique_pairs,
)
from heinzel_google._gws import Process
from heinzel_google._selected_gws import SelectedCapturedGwsRead

_COMMAND_LENGTH = 7
_DOC_FIELDS = "documentId,title,revisionId,tabs"
_SLIDE_FIELDS = "presentationId,title,revisionId,slides(pageElements(shape(text(textElements(textRun(content))))))"
_SHEET_FIELDS = (
    "spreadsheetId,properties(title),sheets(properties(title,sheetType),data(rowData(values(formattedValue))))"
)


class CapturedArtifact(SelectedCapturedGwsRead):
    """Fixed file identity and type, with only metadata and one content read admitted."""

    @_serialized
    def bind_artifact(self, identity: DriveIdentity, scopes: tuple[str, ...], file_id: str, kind: str) -> None:
        """Bind observed account and exact host-reviewed target; this is not authorization.

        Raises:
            HeinzelError: If the source or identity changed.
        """
        self._check_owner()
        if type(identity) is not DriveIdentity or self.inspect_identity() != identity or scopes != self._scopes:
            msg = "The reviewed Google connection does not match"
            raise HeinzelError(msg)
        self._identity = identity
        self._file_id = file_id
        self._kind = kind
        self._metadata_ok = False

    @_serialized
    def run(self, executable: str, arguments: Sequence[str], timeout: float) -> Process:
        """Admit only the exact file, selected content type and fixed response projections.

        Raises:
            HeinzelError: If owner, source, command or provider output cannot be verified.
            ValueError: Invalid input is mapped to a safe error.
        """
        self._check_owner()
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= _MAX_TIMEOUT:
            msg = "The Google read timeout is invalid"
            raise HeinzelError(msg)
        if Path(executable).resolve() != self.selection.command or self._identity is None:
            msg = "The reviewed Google artifact connection is unavailable"
            raise HeinzelError(msg)
        args = list(arguments)
        if args == ["--version"]:
            self._check_current()
            if self._temporary is None:
                msg = "The Google connection lease is closed"
                raise HeinzelError(msg)
            return self._run(
                str(self._executable), args, timeout, (self._source_env, self._temporary.name, _MAX_CREDENTIAL_BYTES)
            )
        try:
            if len(args) != _COMMAND_LENGTH or args[3] != "--params" or args[5:] != ["--format", "json"]:
                raise ValueError  # noqa: TRY301
            parsed = json.loads(args[4], object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
            if not isinstance(parsed, dict) or self.inspect_identity() != self._identity:
                raise ValueError  # noqa: TRY301
            params = cast("dict[str, object]", parsed)
            return self._dispatch(args, params, timeout)
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            self.discard()
            msg = "The Google artifact read did not match its reviewed terms"
            raise HeinzelError(msg) from None

    def _dispatch(self, args: list[str], params: dict[str, object], timeout: float) -> Process:
        if args[:3] == ["drive", "files", "get"]:
            return self._metadata(args, params, timeout)
        if not self._metadata_ok:
            raise ValueError
        if (
            (self._kind == "document" and args[:3] == ["docs", "documents", "get"])
            or (self._kind == "spreadsheet" and args[:3] == ["sheets", "spreadsheets", "get"])
            or (self._kind == "presentation" and args[:3] == ["slides", "presentations", "get"])
        ):
            return self._content(args, params, timeout)
        raise ValueError

    def _metadata(self, args: list[str], params: dict[str, object], timeout: float) -> Process:
        expected = {
            "fileId": self._file_id,
            "fields": "id,name,mimeType,version,shortcutDetails",
            "supportsAllDrives": True,
        }
        if not _same_params(params, expected):
            raise ValueError
        self._metadata_ok = False
        projected = [*args]
        projected[4] = json.dumps({**params, "fields": "id,name,mimeType,version"}, separators=(",", ":"))
        result = self._read(projected, timeout)
        if result.exit_code == 0 and not result.truncated:
            body = json.loads(result.stdout, object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
            mime = next(key for key, kind in KINDS.items() if kind == self._kind)
            if (
                not isinstance(body, dict)
                or set(body) - {"id", "name", "mimeType", "version"}
                or body.get("id") != self._file_id
                or body.get("mimeType") != mime
            ):
                raise ValueError
            self._metadata_ok = True
        return result

    def _content(self, args: list[str], params: dict[str, object], timeout: float) -> Process:
        expected: dict[str, object]
        if self._kind == "presentation":
            expected = {"presentationId": self._file_id}
            fields, id_field = _SLIDE_FIELDS, "presentationId"
        elif self._kind == "document":
            expected = {"documentId": self._file_id, "includeTabsContent": True}
            fields, id_field = _DOC_FIELDS, "documentId"
        else:
            expected = {
                "spreadsheetId": self._file_id,
                "includeGridData": True,
                "fields": "properties.title,sheets(properties(title,sheetType),data(rowData(values(formattedValue))))",
            }
            fields, id_field = _SHEET_FIELDS, "spreadsheetId"
        if not _same_params(params, expected):
            raise ValueError
        projected = [*args]
        projected[4] = json.dumps({**params, "fields": fields}, separators=(",", ":"))
        result = self._read(projected, timeout)
        if result.exit_code == 0 and not result.truncated:
            body = json.loads(result.stdout, object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
            allowed = {
                "document": {"documentId", "title", "revisionId", "tabs"},
                "presentation": {"presentationId", "title", "revisionId", "slides"},
                "spreadsheet": {"spreadsheetId", "properties", "sheets"},
            }[self._kind]
            if not isinstance(body, dict) or set(body) - allowed or body.get(id_field) != self._file_id:
                raise ValueError
            if self._kind == "spreadsheet":
                _validate_sheet(body)
        return result


class CapturedDocument(CapturedArtifact):
    @staticmethod
    def _exchange(exported: bytes) -> tuple[str, float, tuple[str, ...]]:
        return _exchange_token(exported, artifact="document")


class CapturedPresentation(CapturedArtifact):
    @staticmethod
    def _exchange(exported: bytes) -> tuple[str, float, tuple[str, ...]]:
        return _exchange_token(exported, artifact="presentation")


class CapturedSpreadsheet(CapturedArtifact):
    @staticmethod
    def _exchange(exported: bytes) -> tuple[str, float, tuple[str, ...]]:
        return _exchange_token(exported, artifact="spreadsheet")


def _object(value: object, allowed: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError
    return cast("dict[str, object]", value)


def _array(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError
    return cast("list[object]", value)


def _validate_sheet(value: dict[str, object]) -> None:
    _object(value.get("properties", {}), {"title"})
    for sheet in _array(value.get("sheets", [])):
        item = _object(sheet, {"properties", "data"})
        _object(item.get("properties", {}), {"title", "sheetType"})
        for grid in _array(item.get("data", [])):
            grid_data = _object(grid, {"rowData"})
            for row in _array(grid_data.get("rowData", [])):
                row_data = _object(row, {"values"})
                for cell in _array(row_data.get("values", [])):
                    cell_data = _object(cell, {"formattedValue"})
                    if "formattedValue" in cell_data and not isinstance(cell_data["formattedValue"], str):
                        raise ValueError


def _same_params(actual: dict[str, object], expected: dict[str, object]) -> bool:
    return json.dumps(actual, sort_keys=True, separators=(",", ":"), allow_nan=False) == json.dumps(
        expected, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
