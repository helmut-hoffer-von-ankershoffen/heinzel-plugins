"""Real plugin operations and checked skill loading, with only provider HTTP replaced."""

from datetime import UTC, datetime

import anyio
import pytest
from fastapi.testclient import TestClient
from heinzel import HeinzelError, Skills
from heinzel.heads import api, mcp
from mcp import Client

from heinzel_weather import WeatherService, fake

pytestmark = pytest.mark.integration
NOW = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def offline_weather(monkeypatch):
    monkeypatch.setattr(WeatherService, "transport", fake.transport(NOW))
    monkeypatch.setenv("HZ_WEATHER__PROVIDER", "openweather")
    monkeypatch.setenv("HZ_WEATHER__LOCATIONS", '["Berlin, DE"]')
    monkeypatch.setenv("HZ_WEATHER__UNITS", "metric")
    monkeypatch.setenv("HZ_CREDENTIAL_WEATHER_API_KEY", "test-key")


def test_observation_is_the_same_typed_input_through_cli_and_http(hz, hz_kernel):
    hz_kernel.resolve(WeatherService).clock = lambda: NOW
    observed = hz("weather", "observe").json
    client = TestClient(api.build(hz_kernel), base_url="http://127.0.0.1")
    response = client.get("/weather/observe")
    assert response.status_code == 200, response.text
    assert response.json() == observed

    async def call_mcp():
        async with Client(mcp.build(hz_kernel)) as client:
            result = await client.call_tool("weather_observe", {})
            assert not result.is_error, result.content
            assert result.structured_content is not None
            return result.structured_content

    assert anyio.run(call_mcp) == observed
    assert observed["report"]["now"]["location"] == "Berlin, DE"
    assert [change["kind"] for change in observed["changes"]] == ["rain", "swing", "alert"]
    assert observed["stale"] is False


def test_reading_changes_does_not_consume_the_watch_jobs_delivery_state(hz_kernel):
    weather = hz_kernel.resolve(WeatherService)
    weather.clock = lambda: NOW
    first = weather.observation()
    assert weather.observation().changes == first.changes
    assert not weather._watch_file.exists()
    watched = weather.watch(None)
    assert watched.changes == first.changes
    saved = weather._watch_file.read_bytes()
    assert weather.observation().changes == first.changes
    assert weather._watch_file.read_bytes() == saved


def test_packaged_skill_uses_the_checked_loader_and_cannot_grant_itself_access(hz, hz_kernel):
    skills = hz_kernel.resolve(Skills)
    entry = next(entry for entry in skills.index() if entry.name == "weather-trend")
    assert (entry.source, entry.module) == ("plugin", "weather")
    loaded = skills.load("weather-trend", allowed=["weather-trend"])
    assert loaded.fingerprint == entry.fingerprint
    assert "weather.observe" in loaded.body
    assert "approval" in loaded.body
    assert not entry.hints
    with pytest.raises(HeinzelError):
        skills.load("weather-trend", allowed=[])
    shown = hz("system", "skill", "show", "weather-trend").json
    assert shown["body"] == loaded.body


def test_mcp_exposes_read_only_observation_and_the_actual_skill_prompt(hz_kernel):
    hz_kernel.resolve(WeatherService).clock = lambda: NOW

    async def read():
        async with Client(mcp.build(hz_kernel)) as client:
            tool = next(tool for tool in (await client.list_tools()).tools if tool.name == "weather_observe")
            assert tool.annotations.read_only_hint is True
            result = await client.call_tool("weather_observe", {})
            assert not result.is_error
            assert result.structured_content is not None
            prompt = await client.get_prompt("skill_weather_trend")
            return result.structured_content, prompt.messages[0].content.text

    observed, prompt = anyio.run(read)
    assert observed["provider"] == "openweather"
    assert [change["kind"] for change in observed["changes"]] == ["rain", "swing", "alert"]
    assert "Skill `weather-trend` from weather (plugin" in prompt
    assert "weather.observe" in prompt
