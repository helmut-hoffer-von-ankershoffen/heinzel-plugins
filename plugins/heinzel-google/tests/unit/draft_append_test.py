"""Marked rolling Docs keep exact account, tab, revision, append scope and edited bytes."""

from types import SimpleNamespace

import pytest
from heinzel import HeinzelError
from heinzel.kernel import DraftAppendAttempt
from pydantic import SecretStr

from heinzel_google import _draft_append as drafts

pytestmark = pytest.mark.unit
KEY = "a" * 64
OWNER = "u-" + "b" * 32
REFERENCE = "https://docs.google.com/document/d/file_123456789012345/edit?tab=t.second"
TEXT = (
    f"\nDRAFT — awaiting your review\nHelper: Lotte\nDraft: {KEY}\n"
    "Source: https://github.com/acme/demo/blob/main/CHANGELOG.md\n\nA poem.\n"
)


class Writer:
    def __init__(self):
        self.revision = "r1"
        self.text = "Existing rolling text.\n"
        self.calls = []
        self.ack = {"documentId": "file_123456789012345", "writeControl": {"requiredRevisionId": "r2"}}
        self.closed = False
        self.validate_source = None
        self.account = SimpleNamespace(email="lotte@example.invalid")

    def inspect_identity(self):
        return self.account

    def observed_scopes(self):
        return ("docs",)

    def bind_artifact(self, *args):
        pass

    def close(self):
        self.closed = True

    discard = close

    def call(self, command, params, body=None):
        self.calls.append((command, params, body))
        if command[-1] == "batchUpdate":
            self.text += body["requests"][0]["insertText"]["text"]
            self.revision = "r2"
            return self.ack
        return {
            "documentId": "file_123456789012345",
            "revisionId": self.revision,
            "tabs": [
                {
                    "tabProperties": {"tabId": "t.second"},
                    "documentTab": {
                        "body": {"content": [{"paragraph": {"elements": [{"textRun": {"content": self.text}}]}}]}
                    },
                }
            ],
        }


@pytest.fixture
def rig(monkeypatch):
    writer = Writer()
    service = object.__new__(drafts.GoogleDraftAppends)
    current = SimpleNamespace(principal=lambda: SimpleNamespace(id=OWNER))
    service._binding = SimpleNamespace(
        current=current, record=SimpleNamespace(origin=SimpleNamespace(version="candidate"))
    )
    service._session = object()
    monkeypatch.setattr(drafts, "_Writer", lambda *args: writer)
    monkeypatch.setattr(drafts, "_source_revision", lambda *args: "source")
    monkeypatch.setattr(drafts, "_check_binding", lambda *args: None)
    target = service.target(REFERENCE, "release-poems")
    attempt = DraftAppendAttempt(
        owner=OWNER,
        session="hz-session",
        grant_sha256="c" * 64,
        draft_key=KEY,
        release_sha256="d" * 64,
        target=target,
        text=SecretStr(TEXT),
    )
    return service, writer, attempt


def test_append_is_one_exact_end_insertion_at_the_selected_tab_and_provider_revision(rig):
    service, writer, attempt = rig
    value = service.open_lease(attempt)
    assert value.review().target == attempt.target
    before = writer.text
    receipt = value.append()
    assert receipt.revision == "r2"
    assert writer.text == before + TEXT
    mutation = [body for command, _, body in writer.calls if command[-1] == "batchUpdate"]
    assert mutation == [
        {
            "writeControl": {"requiredRevisionId": "r1"},
            "requests": [{"insertText": {"endOfSegmentLocation": {"tabId": "t.second"}, "text": TEXT}}],
        }
    ]
    with pytest.raises(HeinzelError, match="already attempted"):
        value.append()
    value.close()
    assert writer.closed


@pytest.mark.parametrize("field", ["account", "source", "reference", "resource_id", "revision", "write_scope"])
def test_every_exact_target_term_is_a_precondition_not_a_hint(rig, field):
    service, writer, attempt = rig
    changed = attempt.target.model_copy(update={field: "different"})
    if field == "reference":
        changed = attempt.target.model_copy(update={field: REFERENCE.replace("file_", "other_")})
    value = service.open_lease(attempt.model_copy(update={"target": changed}))
    with pytest.raises(HeinzelError, match=r"changed|attest"):
        value.append()
    assert all(command[-1] != "batchUpdate" for command, _, _ in writer.calls)


def test_snapshot_returns_exact_human_dot_and_current_revision_until_next_marked_draft(rig):
    service, writer, attempt = rig
    writer.text += TEXT.replace("A poem.", "A poem.\n.")
    writer.text += TEXT.replace(KEY, "f" * 64).replace("A poem.", "Later poem.")
    writer.revision = "human-r3"
    snapshot = service.capture(attempt.target, KEY)
    assert snapshot.target.revision == "human-r3"
    assert snapshot.text.get_secret_value() == TEXT.replace("A poem.", "A poem.\n.")
    assert all(command[-1] != "batchUpdate" for command, _, _ in writer.calls)


def test_uncertain_acknowledgement_is_not_reconstructed_by_readback_or_retried(rig):
    service, writer, attempt = rig
    value = service.open_lease(attempt)
    writer.ack = {"documentId": "another-file"}
    with pytest.raises(HeinzelError, match="do not retry"):
        value.append()
    with pytest.raises(HeinzelError, match="already attempted"):
        value.append()
    assert sum(command[-1] == "batchUpdate" for command, _, _ in writer.calls) == 1


def test_existing_marked_draft_and_ambiguous_edited_sections_refuse(rig):
    service, writer, attempt = rig
    writer.text += TEXT
    with pytest.raises(HeinzelError, match="already exists"):
        service.open_lease(attempt).append()
    writer.text += TEXT
    with pytest.raises(HeinzelError, match="ambiguous"):
        service.capture(attempt.target, KEY)


def test_only_rolling_docs_with_one_exact_marked_section_are_supported(rig):
    service, _writer, attempt = rig
    with pytest.raises(HeinzelError, match="exactly one"):
        service.open_lease(attempt.model_copy(update={"text": SecretStr(TEXT + TEXT)}))
    with pytest.raises(HeinzelError, match="existing Google Doc"):
        service.target(REFERENCE.replace("document", "spreadsheets"), "release-poems")
    with pytest.raises(HeinzelError, match="release-poems"):
        service.target(REFERENCE, "replace-heading")
