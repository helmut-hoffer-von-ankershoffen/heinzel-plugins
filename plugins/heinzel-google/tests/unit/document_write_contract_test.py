"""Offline checks of the candidate core's conditional-write contract."""

import hashlib
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from heinzel import HeinzelError
from heinzel.kernel import CapturedWriteAcknowledgement, CapturedWriteDraft
from pydantic import SecretStr

from heinzel_google import _document_write as writes

pytestmark = pytest.mark.unit


def presentation_terms(monkeypatch):
    owner = "u-" + "b" * 32
    binding = Mock()
    binding.current.principal.return_value.id = owner
    binding.record.qualname = "google"
    binding.record.origin.version = "0.9.2"
    draft = CapturedWriteDraft(
        owner=owner,
        session="fictional-session",
        request_id="draft-one",
        provider="google",
        binding_id="a" * 64,
        account="fiction@example.invalid",
        source="source-fixture",
        reference="https://docs.google.com/presentation/d/presentation_id_12345/edit",
        operation="insert-draft",
        section="end",
        base_revision="r1",
        write_scope="https://www.googleapis.com/auth/presentations",
        content=SecretStr("literal"),
    )
    writer = Mock()
    writer.inspect_identity.return_value = SimpleNamespace(email=draft.account)
    writer.observed_scopes.return_value = (draft.write_scope,)
    writer.call.return_value = {"revisionId": "r1"}
    monkeypatch.setattr(writes, "_Writer", Mock(return_value=writer))
    monkeypatch.setattr(writes, "_check_binding", Mock())
    monkeypatch.setattr(writes, "_source_revision", Mock(return_value="source-fixture"))
    return binding, draft, writer


def test_captured_presentation_review_binds_content_source_and_conditional_revision(monkeypatch):
    binding, draft, writer = presentation_terms(monkeypatch)
    value = writes._WriteLease(binding, Mock(), draft)
    writer.bind_artifact.assert_called_once_with(
        writer.inspect_identity.return_value,
        (draft.write_scope,),
        "presentation_id_12345",
        "presentation",
    )
    value._validate_source()
    review = value.review()
    assert review.model_dump() == {
        **draft.model_dump(exclude={"request_id", "content"}),
        "conditional_mutation": True,
        "content_sha256": hashlib.sha256(b"literal").hexdigest(),
    }
    writer.call.assert_called_once_with(
        ("slides", "presentations", "get"), {"presentationId": "presentation_id_12345", "fields": "revisionId"}
    )
    value.close()
    writer.close.assert_called_once()


@pytest.mark.parametrize("failure", [HeinzelError("identity refused"), KeyboardInterrupt()])
def test_partial_write_capture_discards_credentials_on_ordinary_or_interrupted_failure(monkeypatch, failure):
    binding, draft, writer = presentation_terms(monkeypatch)
    writer.inspect_identity.side_effect = failure
    with pytest.raises(type(failure)):
        writes._WriteLease(binding, Mock(), draft)
    writer.discard.assert_called_once()
    writer.bind_artifact.assert_not_called()
    writer.call.assert_not_called()


def lease(monkeypatch):
    value = object.__new__(writes._WriteLease)
    value._attempted = False
    value._write_lock = threading.Lock()
    value._kind = "document"
    value._file_id = "document_id_12345"
    value._draft = SimpleNamespace(
        account="fiction@example.invalid",
        source="source",
        base_revision="r1",
        content=SimpleNamespace(get_secret_value=lambda: "literal"),
        section="end",
        reference="ref",
    )
    value.review = Mock(
        return_value=SimpleNamespace(account="fiction@example.invalid", source="source", base_revision="r1")
    )
    value._lease = Mock()
    monkeypatch.setattr(writes, "_write_document", Mock())
    return value


def test_exact_revision_is_used_and_no_later_read_is_claimed_as_acknowledgement(monkeypatch):
    value = lease(monkeypatch)
    assert value.write() == CapturedWriteAcknowledgement(reference="ref")
    writes._write_document.assert_called_once_with(value._lease, value._file_id, "end", "literal", "r1", tab_id=None)
    with pytest.raises(HeinzelError, match="already attempted"):
        value.write()
    writes._write_document.assert_called_once()


def test_unknown_provider_outcome_cannot_be_replayed(monkeypatch):
    value = lease(monkeypatch)
    writes._write_document.side_effect = HeinzelError("unknown outcome")
    with pytest.raises(HeinzelError, match="unknown outcome"):
        value.write()
    with pytest.raises(HeinzelError, match="already attempted"):
        value.write()
    writes._write_document.assert_called_once()


@pytest.mark.parametrize("field", ["account", "source", "base_revision"])
def test_changed_exact_terms_prevent_mutation(monkeypatch, field):
    value = lease(monkeypatch)
    setattr(value.review.return_value, field, "changed")
    with pytest.raises(HeinzelError, match="changed"):
        value.write()
    writes._write_document.assert_not_called()


def test_target_revision_observation_does_not_read_document_body():
    writer = Mock()
    writer.call.return_value = {"revisionId": "r1"}
    assert writes._revision(writer, "document", "file")[0] == "r1"
    assert writer.call.call_args.args[1]["fields"] == "documentId,revisionId"


@pytest.mark.parametrize(
    "ref",
    [
        "new:document",
        "new:spreadsheet",
        "new:presentation",
        "https://docs.google.com/spreadsheets/d/sheet_id_123456/edit",
    ],
)
def test_targets_without_provider_conditional_mutation_are_rejected_before_capture(monkeypatch, ref):
    service = object.__new__(writes.GoogleDocumentWrites)
    service._binding = Mock()
    monkeypatch.setattr(writes, "_check_binding", Mock())
    monkeypatch.setattr(writes, "_Writer", Mock())
    with pytest.raises(HeinzelError, match="precondition"):
        service.target(ref)
    writes._Writer.assert_not_called()


@pytest.mark.parametrize("changed", ["owner", "version", "source", "account", "scopes", "selection"])
def test_each_provider_command_requires_same_owner_source_version_and_scopes(monkeypatch, changed):
    value = object.__new__(writes._WriteLease)
    value._owner, value._version, value._source = "owner", "version", "source"
    value._identity, value._scopes = "account", ("scope",)
    value._binding = Mock()
    value._binding.current.principal.return_value.id = "owner"
    value._binding.record.origin.version = "version"
    value._lease = Mock()
    value._lease.inspect_identity.return_value = "account"
    value._lease.observed_scopes.return_value = ("scope",)
    monkeypatch.setattr(writes, "_source_revision", Mock(return_value="source"))
    monkeypatch.setattr(writes, "_check_binding", Mock())
    if changed == "owner":
        value._binding.current.principal.return_value.id = "other"
    elif changed == "version":
        value._binding.record.origin.version = "other"
    elif changed == "source":
        writes._source_revision.return_value = "other"
    elif changed == "account":
        value._lease.inspect_identity.return_value = "other"
    elif changed == "scopes":
        value._lease.observed_scopes.return_value = ("other",)
    else:
        writes._check_binding.side_effect = HeinzelError("selection changed")
    with pytest.raises(HeinzelError, match="changed"):
        value._validate_source()


class MultitabProvider:
    """Model Google defaults: an omitted tabId mutates the first tab, even for a selected-tab URL."""

    def __init__(self, *, ignore_tab=False, race=False):
        self.text = {"t.first": "First\n", "t.second": "Section\n", "t.child": "Section\n"}
        self.mutations = []
        self.ignore_tab, self.race = ignore_tab, race
        self.gets = []

    def call(self, command, params, body=None):
        if command == ("docs", "documents", "get"):
            self.gets.append(params)
            assert params["includeTabsContent"] is True

            def tab(identity):
                return {
                    "tabProperties": {"tabId": identity},
                    "documentTab": {
                        "body": {
                            "content": [
                                {
                                    "endIndex": 9,
                                    "paragraph": {"elements": [{"textRun": {"content": self.text[identity]}}]},
                                }
                            ]
                        }
                    },
                }

            first, second = tab("t.first"), tab("t.second")
            second["childTabs"] = [tab("t.child")]
            return {"documentId": params["documentId"], "revisionId": "r1", "tabs": [first, second]}
        assert command == ("docs", "documents", "batchUpdate")
        assert body["writeControl"] == {"requiredRevisionId": "r1"}
        if self.race:
            msg = "provider revision conflict"
            raise HeinzelError(msg)
        request = body["requests"][0]["insertText"]
        location = request.get("location", request.get("endOfSegmentLocation", {}))
        identity = "t.first" if self.ignore_tab else location.get("tabId", "t.first")
        self.text[identity] += request["text"]
        self.mutations.append((identity, request))
        return {}


@pytest.mark.parametrize("navigation", ["?tab=t.second", "#tab=t.second", "?tab=t.child"])
@pytest.mark.parametrize("section", ["end", "Section"])
def test_selected_tab_url_reaches_actual_request_cas_and_readback(monkeypatch, navigation, section):
    actual_write = writes._write_document
    value = lease(monkeypatch)
    monkeypatch.setattr(writes, "_write_document", actual_write)
    value._draft.reference = "https://docs.google.com/document/d/document_id_12345/edit" + navigation
    value._draft.section = section
    provider = MultitabProvider()
    value._lease = provider
    result = value.write()
    selected = "t.child" if "child" in navigation else "t.second"
    assert result.reference == value._draft.reference
    assert result.revision is None
    assert provider.text["t.first"] == "First\n"
    assert "literal" in provider.text[selected]
    assert provider.mutations[0][0] == selected
    location = provider.mutations[0][1].get("location", provider.mutations[0][1].get("endOfSegmentLocation"))
    assert location["tabId"] == selected
    assert len(provider.gets) == 2  # exact tab before mutation and the same tab afterwards


def test_selected_tab_that_disappeared_is_refused_before_mutation(monkeypatch):
    actual_write = writes._write_document
    value = lease(monkeypatch)
    monkeypatch.setattr(writes, "_write_document", actual_write)
    value._draft.reference = "https://docs.google.com/document/d/document_id_12345/edit#tab=t.absent"
    provider = MultitabProvider()
    value._lease = provider
    with pytest.raises(HeinzelError, match="tab is unavailable"):
        value.write()
    assert provider.mutations == []


def test_provider_defaulting_to_wrong_tab_fails_readback_without_acknowledgement():
    provider = MultitabProvider(ignore_tab=True)
    with pytest.raises(HeinzelError, match="could not be confirmed in its selected tab"):
        writes._write_document(provider, "file", "end", "literal", "r1", tab_id="t.second")
    assert provider.text["t.second"] == "Section\n"


def test_revision_race_is_refused_by_provider_without_touching_any_tab():
    provider = MultitabProvider(race=True)
    with pytest.raises(HeinzelError, match="revision conflict"):
        writes._write_document(provider, "file", "end", "literal", "r1", tab_id="t.second")
    assert provider.mutations == []
    assert provider.text == {"t.first": "First\n", "t.second": "Section\n", "t.child": "Section\n"}


@pytest.mark.parametrize("section", ["existing-slide", "shape-id", "title"])
def test_existing_slides_section_is_refused_before_approval_or_credential_capture(monkeypatch, section):
    binding = Mock()
    binding.current.principal.return_value.id = "owner"
    binding.record.qualname = "google"
    draft = SimpleNamespace(
        reference="https://docs.google.com/presentation/d/presentation_id_12345/edit",
        owner="owner",
        provider="google",
        write_scope=writes._SCOPE["presentation"],
        section=section,
        operation="insert-draft",
    )
    monkeypatch.setattr(writes, "_Writer", Mock())
    with pytest.raises(HeinzelError, match="not an existing slide or shape"):
        writes._WriteLease(binding, Mock(), draft)
    writes._Writer.assert_not_called()


def test_owned_process_group_cleanup_fences_writer_and_credential_release(monkeypatch):
    import io

    from heinzel_google import _gws

    group_pending, group_stopped, returned, cleaned = (threading.Event() for _ in range(4))

    class Child:
        pid = 1234
        stdout = io.BytesIO(b"{}")
        stderr = io.BytesIO(b"")
        reaped = False

        def wait(self, _timeout):
            self.reaped = True
            return 0

        def kill(self):
            pass

    child = Child()
    monkeypatch.setattr(_gws.subprocess, "Popen", lambda *args, **kwargs: child)
    monkeypatch.setattr(_gws, "signal_group", lambda *_args: None)

    def group_exists(_pid):
        group_pending.set()
        return not group_stopped.is_set()

    monkeypatch.setattr(_gws, "_group_exists", group_exists)
    writer = object.__new__(writes._Writer)
    writer.lease_lock = threading.RLock()
    writer.validate_source = None
    writer._check_owner = Mock()
    writer._check_current = Mock()
    writer._temporary = SimpleNamespace(name="/")
    writer._token, writer._executable = "fake", "fake"
    writer._run = _gws.Gws()._run
    writer._cleanup = cleaned.set
    errors = []

    def call():
        try:
            writer.call(("docs", "documents", "batchUpdate"), {"documentId": "file"}, {})
        except BaseException as exc:  # noqa: BLE001 - test must observe every premature exit
            errors.append(exc)
        finally:
            returned.set()

    worker = threading.Thread(target=call, daemon=True)
    closer = threading.Thread(target=writer.close, daemon=True)
    worker.start()
    try:
        assert group_pending.wait(1)
        assert child.reaped
        closer.start()
        assert not returned.wait(0.05), "writer escaped before its process group was confirmed stopped"
        assert not cleaned.is_set(), "credential lease was released while provider work could still be alive"
    finally:
        group_stopped.set()
        worker.join(2)
        if closer.ident is not None:
            closer.join(2)
    assert returned.is_set()
    assert cleaned.is_set()
    assert errors == []


def test_slides_end_means_new_slide_and_uses_exact_provider_revision(monkeypatch):
    value = lease(monkeypatch)
    value._kind = "presentation"
    value._draft.reference = "https://docs.google.com/presentation/d/presentation_id_12345/edit"
    value.write()
    command, params, body = value._lease.call.call_args.args
    assert command == ("slides", "presentations", "batchUpdate")
    assert params == {"presentationId": value._file_id}
    assert body["writeControl"] == {"requiredRevisionId": "r1"}
    assert "createSlide" in body["requests"][0]
    assert body["requests"][-1]["insertText"]["text"] == "literal"


@pytest.mark.parametrize("operation", ["replace", "delete", "append-other-file"])
def test_unimplemented_mutation_meanings_are_refused_before_credential_capture(monkeypatch, operation):
    binding = Mock()
    binding.current.principal.return_value.id = "owner"
    binding.record.qualname = "google"
    draft = SimpleNamespace(
        reference="https://docs.google.com/document/d/document_id_12345/edit",
        owner="owner",
        provider="google",
        write_scope=writes._SCOPE["document"],
        section="end",
        operation=operation,
    )
    monkeypatch.setattr(writes, "_Writer", Mock())
    with pytest.raises(HeinzelError, match="only the insert-draft operation"):
        writes._WriteLease(binding, Mock(), draft)
    writes._Writer.assert_not_called()


def test_provider_reply_cannot_redirect_selected_document_identity():
    provider = MultitabProvider()
    call = provider.call

    def redirect(command, params, body=None):
        reply = call(command, params, body)
        reply["documentId"] = "a-different-document"
        return reply

    provider.call = redirect
    with pytest.raises(HeinzelError, match="exact selected document"):
        writes._document_context(provider, "document_id_12345", "t.second", "r1")
    assert provider.mutations == []
