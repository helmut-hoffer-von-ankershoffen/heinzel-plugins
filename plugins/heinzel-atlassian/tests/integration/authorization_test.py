"""Released public head contracts keep Jira content private and writes under explicit CLI intent."""

import json
from datetime import UTC, datetime, timedelta

import anyio
import pytest
from fastapi.testclient import TestClient
from heinzel import Config, HeinzelError
from heinzel.heads import api, mcp
from heinzel.heads.api import ApiBearer
from heinzel.kernel import CallIdentity, CurrentUser, OperationLet, Principal
from mcp import Client

from tests.conftest import live
from tests.integration.work_test import hz

pytestmark = pytest.mark.integration
BOUND = Config(files=(), data={"atlassian": {"site_url": "https://acme.atlassian.net"}})
READS = {"assigned", "epics", "watch", "draft-create-issue", "draft-update-issue", "draft-comment-issue"}
WRITES = {"create-issue", "update-issue", "comment-issue"}


@pytest.fixture
def jira(acli_on_path, atlassian_kernel):
    acli_on_path.answer("jira workitem view KAN-8", live("view_task.json"))
    return acli_on_path, atlassian_kernel(BOUND)


def operations(kernel):
    return {op.name: op for rec, op in kernel.lets(OperationLet) if rec.qualname == "atlassian"}


@pytest.mark.parametrize(
    ("name", "permissions"),
    [
        (name, permissions)
        for name in sorted(READS | WRITES)
        for permissions in (None, frozenset(), frozenset({"private:read"}))
        if permissions != frozenset({"private:read"}) or name in WRITES
    ],
)
def test_private_scope_is_checked_before_any_vendor_call(jira, name, permissions):
    fake, kernel = jira
    user = kernel.resolve(CurrentUser)
    identity = (
        None
        if permissions is None
        else CallIdentity(Principal("u-" + "a" * 32), "api-bearer", "test", "test-server", permissions)
    )
    with user.using(identity), pytest.raises(HeinzelError, match=r"authenticated|permit"):
        kernel.invoke(operations(kernel)[name])
    assert not fake.calls


def test_scoped_authenticated_read_and_explicit_cli_write_work(jira):
    fake, kernel = jira
    identity = CallIdentity(Principal("u-" + "a" * 32), "api-bearer", "reader", "server", {"private:read"})
    with kernel.resolve(CurrentUser).using(identity):
        draft = kernel.invoke(operations(kernel)["draft-comment-issue"], key="KAN-8", text="Looks good.")
    assert draft.ready
    fake.answer("jira workitem comment create", {"id": "123"})
    code, out = hz(kernel, "atlassian", "comment-issue", "KAN-8", "Looks good.", draft.seen.isoformat())
    assert code == 0, out
    assert out["action"] == "comment-issue"
    assert len([c for c in fake.calls if c.args[:4] == ["jira", "workitem", "comment", "create"]]) == 1


def test_unauthenticated_api_has_no_jira_work_routes(jira):
    fake, kernel = jira
    with TestClient(api.build(kernel), base_url="http://localhost") as rest:
        for name in READS | WRITES:
            response = rest.request("POST" if name in WRITES else "GET", f"/atlassian/{name}")
            assert response.status_code == 404
    assert not fake.calls


def test_mcp_and_chat_never_expose_write_tools(jira):
    fake, kernel = jira

    code, session = hz(kernel, "chat", "open")
    assert code == 0, session

    async def scenario():
        for options in ({"transport": "stdio"}, {"transport": "http"}, {"chat": session["id"]}):
            async with Client(mcp.build(kernel, **options)) as agent:
                names = {tool.name for tool in (await agent.list_tools()).tools}
                assert not {"atlassian_" + name.replace("-", "_") for name in WRITES} & names
                if options != {"transport": "stdio"}:
                    assert not {"atlassian_" + name.replace("-", "_") for name in READS} & names
                else:
                    result = await agent.call_tool("atlassian_draft_comment_issue", {"key": "KAN-8", "text": "Hi."})
                    assert not result.is_error
                    assert json.loads(result.content[0].text)["ready"]

    anyio.run(scenario)
    assert not [c for c in fake.calls if c.args[:3] == ["jira", "workitem", "comment"]]


@pytest.mark.parametrize("head", ["api-private", "web"])
def test_authenticated_network_heads_can_read_but_cannot_apply(jira, head):
    fake, kernel = jira
    if head == "api-private":
        credential = ApiBearer(
            Principal("u-" + "a" * 32),
            "jira-test-server",
            "test",
            "fixture-secret",
            datetime.now(UTC) + timedelta(hours=1),
            frozenset({"private:read", "private:write"}),
        )
        app = api.build(kernel, credentials=credential, audience="jira-test-server")
    else:
        app = api.build(kernel, head="web", token="fixture-secret")
    with TestClient(app, base_url="http://localhost", headers={"Authorization": "Bearer fixture-secret"}) as rest:
        draft = rest.get("/atlassian/draft-comment-issue", params={"key": "KAN-8", "text": "Hello."})
        assert draft.status_code == 200, draft.text
        assert draft.json()["ready"]
        for name in WRITES:
            assert rest.post(f"/atlassian/{name}", json={}).status_code == 404
    assert not [c for c in fake.calls if c.args[:3] == ["jira", "workitem", "comment"]]
