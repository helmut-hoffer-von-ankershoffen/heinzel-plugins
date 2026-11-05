"""Offline provider transport behind the real installed Google adapter and trusted human confirmation path."""

import inspect
import json
from copy import deepcopy

from fastapi.testclient import TestClient
from heinzel import CurrentUser
from heinzel.heads import web
from heinzel.kernel import CapturedWriteService, OperationLet

from heinzel_google import _existing_lease as leases
from heinzel_google._existing_lease import CapturedGwsRead
from heinzel_google._gws import Process


class Workspace:
    """Model fixed Google revision CAS and tab selection; never talk to an external service."""

    def __init__(self):
        self.revision = "r1"
        self.tabs = {"t.first": "First tab\n", "t.selected": "Selected tab\n"}
        self.mutations = []
        self.credential = json.dumps(
            {
                "type": "authorized_user",
                "client_id": "fixture",
                "client_secret": "fixture-secret",
                "refresh_token": "fixture-refresh",
            }
        ).encode()

    def run(self, _lease, _executable, arguments, _timeout, context):
        args = list(arguments)
        if args == ["--version"]:
            return Process(0, b"gws 0.22.5")
        if args == ["auth", "export", "--unmasked"]:
            return Process(0, self.credential)
        assert context[0]["GOOGLE_WORKSPACE_CLI_TOKEN"] == "fixture-access"
        command = args[:3]
        params = json.loads(args[args.index("--params") + 1])
        if command == ["drive", "about", "get"]:
            assert params == {"fields": "user(permissionId,emailAddress,me)"}
            return Process(
                0, b'{"user":{"permissionId":"fixture-owner","emailAddress":"fiction@example.invalid","me":true}}'
            )
        assert params["documentId"] == "document_id_12345"
        if command == ["docs", "documents", "get"]:
            result = {"documentId": "document_id_12345", "revisionId": self.revision}
            if params["fields"] == "documentId,revisionId,tabs":
                assert params["includeTabsContent"] is True
                result["tabs"] = [
                    {
                        "tabProperties": {"tabId": identity},
                        "documentTab": {
                            "body": {"content": [{"paragraph": {"elements": [{"textRun": {"content": text}}]}}]}
                        },
                    }
                    for identity, text in self.tabs.items()
                ]
            else:
                assert params["fields"] == "documentId,revisionId"
            return Process(0, json.dumps(result).encode())
        assert command == ["docs", "documents", "batchUpdate"]
        body = json.loads(args[args.index("--json") + 1])
        assert body["writeControl"] == {"requiredRevisionId": self.revision}
        assert self.revision == "r1"
        request = body["requests"][0]["insertText"]
        assert request == {"endOfSegmentLocation": {"tabId": "t.selected"}, "text": "\nExact fictional draft\n"}
        self.mutations.append(deepcopy(body))
        self.tabs["t.selected"] += request["text"]
        self.revision = "r2"
        return Process(0, b"{}")


def exercise_installed_write(kernel, monkeypatch):
    """Observe, draft, stage, reject forged execution, confirm once and reject replay through real host APIs."""
    workspace = Workspace()
    scopes = ("https://www.googleapis.com/auth/drive.metadata.readonly", "https://www.googleapis.com/auth/documents")

    def run(lease, executable, arguments, timeout, context):
        return workspace.run(lease, executable, arguments, timeout, context)

    class Exchange:
        pid = 123456789
        returncode = 0

        def communicate(self, data=None, timeout=None):
            assert timeout is not None
            if data is not None:
                assert data == workspace.credential
            return json.dumps(
                {"access_token": "fixture-access", "expires_in": 300, "token_type": "Bearer", "scope": " ".join(scopes)}
            ).encode(), None

    def launch(args, **_kwargs):
        assert args[1:4] == ["-I", "-S", "-c"]
        assert "OAuth token request failed" in args[4]
        assert args[-1] == "document-write"
        assert "fixture-refresh" not in repr(args)
        return Exchange()

    monkeypatch.setattr(CapturedGwsRead, "_run", run)
    monkeypatch.setattr(leases.subprocess, "Popen", launch)
    monkeypatch.setattr(leases, "signal_group", lambda *_args: None)
    record, registration = kernel.selected_capability_provider("documents")
    assert registration.modes == frozenset({"read"})
    source = kernel.source_discovery.binding(kernel, "documents", CapturedWriteService)
    registered = source.capture.service(kernel, record, CapturedWriteService)
    assert registered.supported_operations == frozenset({"insert-draft"})
    operation = next(
        let
        for owner, let in kernel.lets(OperationLet)
        if owner.qualname == "heinzel" and let.name == "propose-captured-write"
    )
    selected_contract = inspect.signature(operation.func, eval_str=True).parameters["selected"].annotation
    selected = kernel.resolve(selected_contract)
    current = kernel.resolve(CurrentUser)
    reference = "https://docs.google.com/document/d/document_id_12345/edit?tab=t.selected"
    with current.local("cli"):
        selected.check_available()
        target = selected.target(reference)
    assert workspace.mutations == []
    with TestClient(
        web.build(kernel, port=None, token="fixture-token", static=None), base_url="http://localhost"
    ) as client:
        _confirm_once(client, workspace, target, reference)
    assert workspace.tabs["t.first"] == "First tab\n"
    assert workspace.tabs["t.selected"] == "Selected tab\n\nExact fictional draft\n"


def _confirm_once(client, workspace, target, reference):
    headers = {"Authorization": "Bearer fixture-token"}
    response = client.post("/api/heinzel/new-chat", headers=headers, json={"request_id": "new"})
    assert response.status_code == 200, response.text
    session = response.json()["session_id"]
    proposal = {
        "session_id": session,
        "request_id": "draft-one",
        "account": target.account,
        "source": target.source,
        "reference": reference,
        "operation": "insert-draft",
        "section": "end",
        "base_revision": target.base_revision,
        "write_scope": target.write_scope,
        "content": "Exact fictional draft",
    }
    response = client.post("/api/heinzel/propose-captured-write", headers=headers, json={"proposal": proposal})
    assert response.status_code == 200, response.text
    assert workspace.mutations == []
    response = client.post(
        "/api/system/runner/chat/propose-captured-write",
        headers=headers,
        params={"durable_session": session, "request_id": "draft-one"},
    )
    assert response.status_code == 200, response.text
    staged = response.json()
    action = next(item for item in staged["actions"] if item["operation"] == "execute-captured-write")
    assert action["arguments"]["review"]["reference"] == reference
    assert action["arguments"]["review"]["content"] == "Exact fictional draft"
    assert workspace.mutations == []
    direct = client.post(
        "/api/heinzel/execute-captured-write",
        headers=headers,
        json={**action["arguments"], "approval_proof": "forged"},
    )
    assert direct.status_code == 400, direct.text
    decision = {"session": staged["id"], "action": action["id"]}
    assert client.post("/api/system/runner/chat/confirm", params=decision).status_code == 401
    assert workspace.mutations == []
    confirmed = client.post("/api/system/runner/chat/confirm", headers=headers, params=decision)
    assert confirmed.status_code == 200, confirmed.text
    found = next(item for item in confirmed.json()["actions"] if item["id"] == action["id"])
    assert found["status"] == "done", confirmed.text
    status = client.get(
        "/api/heinzel/captured-write-status",
        headers=headers,
        params={"session_id": session, "request_id": "draft-one"},
    )
    assert status.status_code == 200, status.text
    assert status.json()["status"] == "acknowledged", status.text
    assert status.json()["receipt"]["reference"] == reference
    assert len(workspace.mutations) == 1
    replay = client.post("/api/system/runner/chat/confirm", headers=headers, params=decision)
    assert replay.status_code == 400, replay.text
    assert len(workspace.mutations) == 1
