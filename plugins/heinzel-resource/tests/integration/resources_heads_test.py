"""The resource meters consume one typed cached sample through CLI, MCP and the API."""

import json
from types import SimpleNamespace

import anyio
import pytest
from fastapi.testclient import TestClient
from heinzel.heads import api, mcp, web
from heinzel.heads.cli import build
from mcp import Client
from typer.testing import CliRunner

pytestmark = pytest.mark.integration


def test_resource_sample_is_shared_by_all_heads(make_kernel, monkeypatch):
    # Exercise several transports and a real MCP session without racing the production one-second cache window.
    monkeypatch.setattr("heinzel_resource.CACHE_SECONDS", 60.0)
    monkeypatch.setattr("heinzel_resource.psutil.cpu_percent", lambda **_: 12.5)
    monkeypatch.setattr("heinzel_resource.psutil.virtual_memory", lambda: SimpleNamespace(percent=40))
    monkeypatch.setattr("heinzel_resource.psutil.getloadavg", lambda: (21.0, 19.0, 18.0))
    monkeypatch.setattr("heinzel_resource.psutil.cpu_count", lambda: 10)
    monkeypatch.setattr("heinzel_resource.gethostname", lambda: "workshop")
    kernel = make_kernel(builtins=True, resource=__import__("heinzel_resource").module)
    result = CliRunner().invoke(build(kernel), ["resource", "--json"])
    assert result.exit_code == 0, result.output
    expected = json.loads(result.stdout)
    assert expected["hostname"] == "workshop"
    client = TestClient(api.build(kernel), base_url="http://localhost")
    assert client.get("/resource").json() == expected
    token = "t" * 43
    ui = TestClient(web.build(kernel, port=8000, token=token, static=None), base_url="http://127.0.0.1:8000")
    assert ui.get("/api/resource").status_code == 401
    result = ui.get("/api/resource", headers={"Authorization": f"Bearer {token}"})
    assert result.headers["Cache-Control"] == "no-store"
    assert result.json() == expected

    async def read():
        async with Client(mcp.build(kernel)) as connected:
            result = await connected.call_tool("resource")
            assert not result.is_error
            return json.loads(result.content[0].text)

    assert anyio.run(read) == expected
    assert expected["load_1m"] > 2 * expected["logical_cores"]


def test_doctor_reports_the_server_hostname_in_json_and_text(make_kernel, monkeypatch):
    monkeypatch.setattr("heinzel.modules.system.doctor.gethostname", lambda: "workshop")
    kernel = make_kernel(builtins=True, resource=__import__("heinzel_resource").module)
    app = build(kernel)
    report = CliRunner().invoke(app, ["system", "doctor", "--json"])
    checks = json.loads(report.stdout)["checks"]["system.doctor"]
    assert {"name": "hostname", "status": "up", "detail": "workshop", "fix": ""} in checks
    report = CliRunner().invoke(app, ["system", "doctor"])
    assert "workshop" in report.stdout
