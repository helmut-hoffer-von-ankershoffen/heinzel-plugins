"""Captured Google document and spreadsheet reads require exact owner, file, source and account."""

import json
import time

import pytest
from heinzel import Config, CurrentUser, HeinzelError, Kernel, Module, ModuleRecord, Settings
from heinzel.kernel import Origin

from heinzel_google import _connected_artifact as artifact
from heinzel_google._captured_artifact import CapturedDocument, CapturedSpreadsheet
from heinzel_google._connected_calendar import GoogleConnectedReadService
from heinzel_google._documents import DOCUMENT, SPREADSHEET, GoogleDocuments
from heinzel_google._gws import GoogleSession, Gws, Process
from heinzel_google._models import GoogleSettings

pytestmark = pytest.mark.unit


@pytest.fixture
def prepared(tmp_path, monkeypatch):  # noqa: C901 - explicit fake provider routes
    # Unit tests isolate adapter behavior; installed-wheel tests cover real host source admission.
    monkeypatch.setattr("heinzel_google._connected_calendar._captured_source_enabled", True)
    executable = tmp_path / "gws"
    executable.write_bytes(b"\xcf\xfa\xed\xfe" + b"fake")
    executable.chmod(0o700)
    config = Config(files=(), data={"google": {"gws_path": str(executable)}, "capabilities": {"documents": "google"}})
    current_config = {"value": config}
    monkeypatch.setattr(Config, "load", classmethod(lambda _cls, _cwd=None: current_config["value"]))
    credential = json.dumps(
        {"type": "authorized_user", "client_id": "client", "client_secret": "secret", "refresh_token": "refresh"}
    ).encode()
    state = {
        "account": "owner-one",
        "credential": credential,
        "commands": [],
        "exports": 0,
        "bad_id": False,
        "shortcut": False,
        "extra": False,
        "rotate": False,
    }

    def run(_self, _executable, arguments, _timeout, context):
        args = list(arguments)
        if args == ["--version"]:
            return Process(0, b"gws 0.22.5")
        if args == ["auth", "export", "--unmasked"]:
            state["exports"] += 1
            return Process(0, state["credential"])
        assert context[0]["GOOGLE_WORKSPACE_CLI_TOKEN"] == "private-token"
        if args[:3] == ["drive", "about", "get"]:
            return Process(0, json.dumps({"user": {"permissionId": state["account"], "me": True}}).encode())
        state["commands"].append(args)
        params = json.loads(args[4])
        file_id = params.get("fileId") or params.get("documentId") or params.get("spreadsheetId")
        if args[:3] == ["drive", "files", "get"]:
            mime = (
                "application/vnd.google-apps.shortcut"
                if state["shortcut"]
                else (SPREADSHEET if file_id.startswith("sheet") else DOCUMENT)
            )
            body = {
                "id": "other-file-id" if state["bad_id"] else file_id,
                "name": "Sample",
                "mimeType": mime,
                "version": "1",
            }
            if state["rotate"]:
                state["account"] = "owner-two"
        elif args[:3] == ["docs", "documents", "get"]:
            body = {
                "documentId": file_id,
                "title": "Sample",
                "revisionId": "1",
                "tabs": [
                    {
                        "documentTab": {
                            "body": {
                                "content": [
                                    {"paragraph": {"elements": [{"textRun": {"content": "Untrusted instructions"}}]}}
                                ]
                            }
                        }
                    }
                ],
            }
        elif args[:3] == ["sheets", "spreadsheets", "get"]:
            body = {
                "spreadsheetId": file_id,
                "properties": {"title": "Sample"},
                "sheets": [
                    {
                        "properties": {"title": "Sheet", "sheetType": "GRID"},
                        "data": [{"rowData": [{"values": [{"formattedValue": "Sample cell"}]}]}],
                    }
                ],
            }
        else:
            msg = "unexpected provider command"
            raise AssertionError(msg)
        if state["extra"]:
            body["unexpected"] = "private"
        return Process(0, json.dumps(body).encode())

    class FakeDocument(CapturedDocument):
        @staticmethod
        def _exchange(exported):
            assert exported == credential
            return "private-token", time.monotonic() + 300, ("drive", "documents")

        _run = run

    class FakeSpreadsheet(CapturedSpreadsheet):
        @staticmethod
        def _exchange(exported):
            assert exported == credential
            return "private-token", time.monotonic() + 300, ("drive", "spreadsheets")

        _run = run

    monkeypatch.setattr(artifact, "CapturedDocument", FakeDocument)
    monkeypatch.setattr(artifact, "CapturedSpreadsheet", FakeSpreadsheet)
    module = Module("google", "fixture")
    module.settings(GoogleSettings)
    module.service(GoogleSession)
    module.service(Gws)
    module.provides("documents", modes={"read"}, name="google", hosts=["fixture.invalid"])(GoogleDocuments)
    kernel = Kernel(
        Settings(),
        [
            ModuleRecord(
                qualname="google",
                module=module,
                origin=Origin(distribution="heinzel-google", version="0.9.1", builtin=False),
            )
        ],
        config=config,
    )
    current = CurrentUser(tmp_path / "identity")
    kernel.bind(CurrentUser, current)
    with current.local("cli"):
        yield GoogleConnectedReadService(kernel, current), state, current_config


@pytest.mark.parametrize(
    ("kind", "file_id", "expected"),
    [("document", "document_id_12345", "Untrusted instructions"), ("spreadsheets", "sheet_id_12345678", "Sample cell")],
)
def test_exact_approved_artifact_read_uses_pinned_account_and_scoped_commands(prepared, kind, file_id, expected):
    service, state, _ = prepared
    ref = f"https://docs.google.com/{kind}/d/{file_id}/edit"
    lease = service.open_lease("hz-test", "capability-method:documents.read", {"ref": ref})
    review = lease.review()
    assert review.fixed_arguments == {"ref": ref}
    assert "untrusted data" in review.candidate_read_disclosure
    assert expected in lease.read({})["text"]
    commands = state["commands"]
    assert len(commands) == 2
    assert all(
        json.loads(item[4]).get(
            "fileId", json.loads(item[4]).get("documentId", json.loads(item[4]).get("spreadsheetId"))
        )
        == file_id
        for item in commands
    )
    assert "fields" in json.loads(commands[-1][4])
    with pytest.raises(HeinzelError):
        lease.read({"ref": "other"})
    lease.close()


@pytest.mark.parametrize(
    "ref",
    [
        "document_id_12345",
        "https://drive.google.com/file/d/document_id_12345",
        "https://evil.invalid/document/d/document_id_12345/edit",
        "https://docs.google.com/document/d/document_id_12345/edit?secret=x",
    ],
)
def test_unreviewable_reference_rejected_before_capture(prepared, ref):
    service, state, _ = prepared
    with pytest.raises(HeinzelError):
        service.open_lease("hz-test", "capability-method:documents.read", {"ref": ref})
    assert state["exports"] == 0


@pytest.mark.parametrize("change", ["bad_id", "shortcut", "extra", "rotate"])
def test_foreign_mismatched_or_unexpected_provider_data_never_returns_content(prepared, change):
    service, state, _ = prepared
    lease = service.open_lease(
        "hz-test",
        "capability-method:documents.read",
        {"ref": "https://docs.google.com/document/d/document_id_12345/edit"},
    )
    state[change] = True
    with pytest.raises(HeinzelError):
        lease.read({})
    lease.close()


def test_rotation_selection_and_unreviewed_command_fenced(prepared):
    service, state, current_config = prepared
    ref = "https://docs.google.com/document/d/document_id_12345/edit"
    lease = service.open_lease("hz-test", "capability-method:documents.read", {"ref": ref})
    source = lease._lease
    args = [
        "drive",
        "files",
        "get",
        "--params",
        json.dumps(
            {
                "fileId": "other_file_12345",
                "fields": "id,name,mimeType,version,shortcutDetails",
                "supportsAllDrives": True,
            }
        ),
        "--format",
        "json",
    ]
    before = len(state["commands"])
    with pytest.raises(HeinzelError):
        source.run(str(source.selection.command), args, 3)
    assert len(state["commands"]) == before
    source.discard()
    lease = service.open_lease("hz-test", "capability-method:documents.read", {"ref": ref})
    state["credential"] = state["credential"].replace(b"refresh", b"changed")
    with pytest.raises(HeinzelError):
        lease.read({})
    state["credential"] = state["credential"].replace(b"changed", b"refresh")
    lease._lease.discard()
    lease = service.open_lease("hz-test", "capability-method:documents.read", {"ref": ref})
    current_config["value"] = Config(files=(), data={"capabilities": {"documents": "other"}})
    with pytest.raises(HeinzelError):
        lease.read({})
    lease._lease.discard()


def test_spreadsheet_rejects_unprojected_nested_cell_data(prepared):
    service, state, _ = prepared
    lease = service.open_lease(
        "hz-test",
        "capability-method:documents.read",
        {"ref": "https://docs.google.com/spreadsheets/d/sheet_id_12345678/edit"},
    )
    original = lease._lease._run

    def with_unexpected(executable, args, timeout, context):
        result = original(executable, args, timeout, context)
        if list(args)[:3] == ["sheets", "spreadsheets", "get"]:
            data = json.loads(result.stdout)
            data["sheets"][0]["data"][0]["rowData"][0]["values"][0]["note"] = "unexpected"
            return Process(0, json.dumps(data).encode())
        return result

    lease._lease._run = with_unexpected
    with pytest.raises(HeinzelError):
        lease.read({})
    assert len(state["commands"]) == 2
    lease._lease.discard()


def test_source_implementation_change_refuses_before_content(prepared, monkeypatch):
    from heinzel_google import _connected_calendar

    service, state, _ = prepared
    lease = service.open_lease(
        "hz-test",
        "capability-method:documents.read",
        {"ref": "https://docs.google.com/document/d/document_id_12345/edit"},
    )
    original = _connected_calendar.source_digest
    monkeypatch.setattr(
        _connected_calendar, "source_digest", lambda path: "changed" if path.name == "_docs.py" else original(path)
    )
    with pytest.raises(HeinzelError):
        lease.read({})
    assert state["commands"] == []
    lease._lease.discard()


def test_type_coercion_in_provider_command_is_not_allowed(prepared):
    service, state, _ = prepared
    lease = service.open_lease(
        "hz-test",
        "capability-method:documents.read",
        {"ref": "https://docs.google.com/document/d/document_id_12345/edit"},
    )
    inner = lease._lease
    params = {
        "fileId": "document_id_12345",
        "fields": "id,name,mimeType,version,shortcutDetails",
        "supportsAllDrives": 1,
    }
    args = ["drive", "files", "get", "--params", json.dumps(params), "--format", "json"]
    with pytest.raises(HeinzelError):
        inner.run(str(inner.selection.command), args, 3)
    assert state["commands"] == []
    inner.discard()


@pytest.mark.parametrize("suffix", ["?usp=sharing", "?tab=t.0", "?usp=drive_link#heading=h.abc", "#gid=123"])
def test_known_navigation_hints_preserve_exact_review_and_whole_file_disclosure(prepared, suffix):
    service, _state, _ = prepared
    ref = "https://docs.google.com/document/d/document_id_12345/edit" + suffix
    lease = service.open_lease("hz-test", "capability-method:documents.read", {"ref": ref})
    assert lease.review().fixed_arguments == {"ref": ref}
    assert "whole file" in lease.review().candidate_read_disclosure
    assert "Untrusted instructions" in lease.read({})["text"]
    lease.close()


@pytest.mark.parametrize(
    "suffix",
    ["?token=secret", "?usp=sharing&usp=sharing", "#gid=../../other", "?tab=other", "?bad", "#access_token=secret"],
)
def test_unsupported_or_sensitive_navigation_is_rejected_before_capture(prepared, suffix):
    service, state, _ = prepared
    ref = "https://docs.google.com/document/d/document_id_12345/edit" + suffix
    with pytest.raises(HeinzelError):
        service.open_lease("hz-test", "capability-method:documents.read", {"ref": ref})
    assert state["exports"] == 0
