"""The plugin as a user gets it: Heinzelmännchen and heinzel-weather in a `uv tool` environment, against the fake.

Needs network for the install only; the weather comes from `heinzel_weather.fake` on 127.0.0.1. Each head is
exercised the way its client uses it: the CLI, the MCP head over stdio (an MCP client starts `hz`), the web head
(`hz ui`, with its session token) and an agent turn that calls the MCP tool.

Run with `make acceptance NAME=weather CORE=<compatible-built-core-wheel>`; both installed artifacts are explicit.
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from heinzel_weather import fake

pytestmark = [pytest.mark.e2e, pytest.mark.timeout(900), pytest.mark.long_running]

PLUGIN = Path(__file__).resolve().parents[2]
CORE_SPEC = os.environ.get(
    "PLUGIN_TEST_CORE", "heinzel==" + json.loads((PLUGIN / "plugin-lock.json").read_text())["core"]["version"]
)
OWN_WHEEL = Path(os.environ.get("PLUGIN_TEST_WHEEL", "."))
TEMPERATURE = fake.TEMPERATURE
SESSION = re.compile(r"http://127\.0\.0\.1:(\d+)/#token=([A-Za-z0-9_-]+)")


@pytest.fixture(scope="module")
def installed(tmp_path_factory):
    """`hz` and its environment: Heinzelmännchen with heinzel-weather, pointed at a running fake OpenWeather."""
    root = tmp_path_factory.mktemp("uv-tools")
    server = fake.serve()
    env = {
        **{key: value for key, value in os.environ.items() if not key.startswith("HZ_")},
        "HZ_PLUGINS_ENABLED": "true",
        "UV_TOOL_DIR": str(root / "tools"),
        "UV_TOOL_BIN_DIR": str(root / "bin"),
        "HZ_WEATHER__BASE_URL": f"http://{fake.HOST}:{server.server_address[1]}",
        "HZ_WEATHER__PROVIDER": "openweather",
        "HZ_WEATHER__LOCATIONS": '["Berlin, DE"]',
        "HZ_WEATHER__UNITS": "metric",
        "OPENWEATHER_API_KEY": "fake-key",
    }
    for key in ("CONFIG_HOME", "DATA_DIR", "CACHE_DIR", "STATE_DIR", "LOG_DIR"):
        env[f"HZ_{key}"] = str(root / key.lower())
    env["HZ_SYSTEM_CREDENTIAL__BACKEND"] = "environment"
    env["HZ_SYSTEM_DAEMON__UNIT_DIR"] = str(root / "units")
    env.pop("VIRTUAL_ENV", None)
    uv = shutil.which("uv")
    assert uv, "uv is not on PATH: https://docs.astral.sh/uv/"
    subprocess.run([uv, "tool", "install", CORE_SPEC, "--with", str(OWN_WHEEL)], check=True, env=env, timeout=600)
    hz = root / "bin" / "hz"
    yield hz, env
    server.shutdown()
    server.server_close()


def run(installed, *args: str) -> str:
    hz, env = installed
    result = subprocess.run([str(hz), *args], capture_output=True, text=True, check=False, env=env, timeout=120)
    assert result.returncode == 0, f"hz {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}"
    return result.stdout


def test_1_cli_hz_weather_json(installed):
    now = json.loads(run(installed, "weather", "--json"))
    assert now["temperature"] == TEMPERATURE
    assert now["location"] == "Berlin, DE"
    report = json.loads(run(installed, "weather", "show", "--json"))
    assert report["alerts"][0]["event"] == "Thunderstorm warning"


def test_2_mcp_tool_weather_over_stdio(installed):
    hz, env = installed

    async def call() -> dict:
        parameters = StdioServerParameters(command=str(hz), args=["system", "serve", "mcp"], env=env)
        async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            tools = {tool.name for tool in (await session.list_tools()).tools}
            assert {"weather", "weather_show", "weather_forecast"} <= tools, tools
            result = await session.call_tool("weather", {})
            assert not result.is_error, result.content
            if result.structured_content is not None:
                return dict(result.structured_content)
            return json.loads(result.content[0].text)  # type: ignore[union-attr]

    content = asyncio.run(call())
    now = content.get("result", content)
    assert now["temperature"] == TEMPERATURE


def test_3_web_head_endpoint(installed):
    hz, env = installed
    with subprocess.Popen(
        [str(hz), "ui", "--no-browser", "--port", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    ) as ui:
        try:
            assert ui.stdout is not None
            found = None
            for line in ui.stdout:
                if found := SESSION.search(line):
                    break
            assert found, "hz ui printed no session URL"
            port, token = found[1], found[2]
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/weather", headers={"Authorization": f"Bearer {token}"}
            )
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - see above
                now = json.loads(response.read())
            assert now["temperature"] == TEMPERATURE
            refused = urllib.request.Request(f"http://127.0.0.1:{port}/api/weather")
            with pytest.raises(urllib.error.HTTPError, match="401") as raised:
                urllib.request.urlopen(refused, timeout=30)  # noqa: S310 - see above
            raised.value.close()
        finally:
            ui.terminate()


def test_4_an_agent_turn_uses_the_weather_tool_over_hz_mcp(installed):
    """A Pydantic AI turn on a fake model: it calls hz's MCP tool `weather`, then answers with what it got back."""
    from pydantic_ai import Agent, Tool
    from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
    from pydantic_ai.models.function import AgentInfo, FunctionModel

    hz, env = installed

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        assert [tool.name for tool in info.function_tools] == ["weather"]
        returned = [part for message in messages for part in message.parts if isinstance(part, ToolReturnPart)]
        if not returned:
            return ModelResponse(parts=[ToolCallPart(tool_name="weather", args={})])
        now = json.loads(str(returned[-1].content))
        return ModelResponse(parts=[TextPart(f"It is {now['temperature']} degrees in {now['location']}.")])

    async def turn() -> str:
        parameters = StdioServerParameters(command=str(hz), args=["system", "serve", "mcp"], env=env)
        async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            listed = next(tool for tool in (await session.list_tools()).tools if tool.name == "weather")

            async def weather() -> str:
                result = await session.call_tool("weather", {})
                assert not result.is_error, result.content
                content = result.structured_content
                return json.dumps(content.get("result", content)) if content else result.content[0].text  # type: ignore[union-attr]

            # The bridge forwards the MCP tool's name and description, not its input schema: `weather` takes none.
            tool = Tool(weather, name="weather", description=listed.description)
            agent = Agent(FunctionModel(model), tools=[tool])
            return (await agent.run("What is the weather like?")).output

    answer = asyncio.run(turn())
    assert f"{TEMPERATURE} degrees in Berlin, DE" in answer
