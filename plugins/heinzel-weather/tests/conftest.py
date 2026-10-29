"""Shared fixtures: the fake OpenWeather at a fixed hour, and a service that asks it.

heinzel.testing (a pytest plugin, loaded automatically) brings the rest: every test is exactly one of unit,
integration or e2e and gets its level's timeout, and its own HZ_* directories without the developer's variables.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from heinzel import Config, Credentials, Kernel, ModuleRecord, Settings
from heinzel.kernel import Origin, discover
from heinzel.testing import MemoryBackend

from heinzel_weather import WeatherService, WeatherSettings, fake
from heinzel_weather._module import API_KEY

NOW = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)
"""A Friday morning: noon in Berlin."""


@pytest.fixture
def credentials() -> Credentials:
    """Credentials in memory, with an API key."""
    store = Credentials(MemoryBackend(), [("weather", API_KEY)])
    store.set(API_KEY, "test-key")
    return store


@pytest.fixture
def service(credentials, tmp_path):
    """A service with Berlin as its place, asking the fake OpenWeather at `NOW`."""

    def make(**settings: object) -> WeatherService:
        made = WeatherService(
            WeatherSettings(**{"provider": "openweather", "locations": ["Berlin, DE"], "units": "metric", **settings}),
            credentials,
            Settings(state_dir=tmp_path / "state"),
        )
        made.transport = fake.transport(NOW)
        made.clock = lambda: NOW
        return made

    return make


FIXTURES = Path(__file__).parent / "fixtures"


def recorded(name: str) -> dict:
    """A recorded Open-Meteo answer from `tests/fixtures`."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def meteo():
    """A factory of Open-Meteo transports serving the recorded Lisbon answers, optionally remembering the requests."""

    def make(requests: list[httpx.Request] | None = None, *, status: int = 200) -> httpx.MockTransport:
        def answer(request: httpx.Request) -> httpx.Response:
            if requests is not None:
                requests.append(request)
            if status != 200:
                return httpx.Response(status)
            geocoding = request.url.host == "geocoding-api.open-meteo.com"
            return httpx.Response(200, json=recorded("geocoding-lisbon.json" if geocoding else "forecast-lisbon.json"))

        return httpx.MockTransport(answer)

    return make


@pytest.fixture
def make_kernel():
    def make(*, builtins=False, settings_=None, config=None, **modules):
        config = config or Config.empty()
        records = discover(plugins=False)[0] if builtins else []
        records += [
            ModuleRecord(
                qualname=name.replace("__", "."),
                module=module,
                origin=Origin("heinzel-contract-fixture", "1.0.0", builtin=False),
            )
            for name, module in modules.items()
        ]
        return Kernel(settings_ or config.settings(Settings, "hz"), records, config=config)

    return make
