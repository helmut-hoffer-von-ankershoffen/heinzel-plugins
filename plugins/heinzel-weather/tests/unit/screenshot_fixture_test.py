"""The server, owning service and browser share an explicit fictional weather date."""

import json
import runpy
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.unit


def test_gallery_public_clock_keeps_real_forecast_and_preserves_shutdown(monkeypatch, service):
    project = Path(__file__).parents[2]
    expected = datetime.fromisoformat(
        json.loads((project / "docs/screenshot-definition.json").read_text())["browser_time"]
    )
    fixture = runpy.run_path(str(project / "docs/screenshot_fixture.py"))
    globals_ = fixture["main"].__globals__
    received = []
    closed = []
    weather = service()
    # The real provider conversion and date filtering must keep the full fictional outlook.
    from heinzel_weather import WeatherService, fake

    weather.transport = fake.transport(expected)

    def serve(port, *, now):
        assert port == 0
        received.append(now())
        return SimpleNamespace(
            server_address=("127.0.0.1", 12345),
            shutdown=lambda: closed.append("shutdown"),
            server_close=lambda: closed.append("close"),
        )

    def resolve(kind):
        assert kind is WeatherService
        return weather

    config = SimpleNamespace(settings=lambda *_: object())
    kernel = SimpleNamespace(resolve=resolve)
    monkeypatch.setitem(globals_, "serve", serve)
    monkeypatch.setitem(globals_, "Config", SimpleNamespace(load=lambda: config))
    monkeypatch.setitem(globals_, "discover", lambda: ([], {}))
    monkeypatch.setitem(globals_, "Kernel", lambda *_: kernel)
    monkeypatch.setitem(
        globals_, "build", lambda actual: lambda: received.append(actual.resolve(WeatherService).clock())
    )
    for key in (
        "HZ_WEATHER__PROVIDER",
        "HZ_WEATHER__BASE_URL",
        "HZ_WEATHER__LOCATIONS",
        "HZ_WEATHER__UNITS",
        "OPENWEATHER_API_KEY",
    ):
        monkeypatch.setenv(key, "initial-fixture-value")
    monkeypatch.setattr(sys, "argv", ["fixture", "weather", "forecast", "--days", "3"])
    fixture["main"]()
    assert received == [expected, expected]
    assert closed == ["shutdown", "close"]
    report = weather.report(days=8, hours=24)
    assert len(report.hours) == 24
    assert len(report.days) == 8
    assert [day.day.isoformat() for day in weather.forecast(days=3).days] == ["2026-11-01", "2026-11-02", "2026-11-03"]
