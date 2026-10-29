"""The plugin through hz's real heads with its default provider: Open-Meteo, no key, the recorded Lisbon answers."""

from datetime import UTC, datetime
from functools import wraps

import pytest

from heinzel_weather import WeatherService

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def open_meteo(monkeypatch, meteo):
    """No provider, no key, no OPENWEATHER_API_KEY: only the default, with the network replaced."""
    monkeypatch.setattr(WeatherService, "transport", meteo())
    monkeypatch.setenv("HZ_WEATHER__LOCATIONS", '["Lisbon, PT"]')
    monkeypatch.setenv("HZ_WEATHER__UNITS", "metric")
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    monkeypatch.delenv("HZ_CREDENTIAL_WEATHER_API_KEY", raising=False)
    initialize = WeatherService.__init__

    @wraps(initialize)
    def fixed_clock(self, *args, **kwargs):
        initialize(self, *args, **kwargs)
        self.clock = lambda: datetime(2026, 10, 26, 10, 0, tzinfo=UTC)

    monkeypatch.setattr(WeatherService, "__init__", fixed_clock)


def test_hz_weather_works_without_a_key(hz):
    now = hz("weather").json
    assert now["location"] == "Lisbon, PT"
    assert now["temperature"] == 12.4
    assert hz("weather", "forecast", "--days", "3").json["days"][2]["description"] == "partly cloudy"


def test_doctor_asks_for_no_key_with_the_default_provider(hz):
    checks = hz("system", "doctor").json["checks"]["weather"]
    assert [(check["name"], check["status"]) for check in checks] == [("locations", "up")]


def test_info_shows_the_attribution(hz):
    info = hz("weather", "info").json
    assert info["provider"] == "open-meteo"
    assert info["keyless"] is True
    assert "Open-Meteo.com (CC BY 4.0)" in info["attribution"]
    assert "Open-Meteo.com (CC BY 4.0)" in hz("weather", "conditions", json=False).output


def test_the_web_app_gets_a_status_item_and_widgets_as_data(hz):
    listed = {item["id"]: item for item in hz("system", "ui", "list").json}
    assert {"weather:weather-now", "weather:weather-today", "weather:forecast-today"} <= set(listed)
    item = hz("system", "ui", "status").json
    now = next(entry for entry in item if entry["id"] == "weather:weather-now")
    assert now["item"]["text"].startswith("12°C Lisbon, PT")
    assert now["item"]["detail"][0]["text"].startswith("Mainly clear · Lisbon, PT")
    assert any("Open-Meteo.com (CC BY 4.0)" in line["text"] for line in now["item"]["detail"])
    widgets = {entry["id"]: entry["widget"] for entry in hz("system", "ui", "widgets").json}
    graphic = widgets["weather:weather-today"]
    assert (graphic["kind"], graphic["value"]) == ("graphic", "12°C")
    assert graphic["caption"].startswith("mainly clear · Weather data by Open-Meteo.com (CC BY 4.0)")
    assert graphic["avatar"] == {"accessories": ["umbrella"]}
    assert widgets["weather:forecast-today"]["items"][-1]["text"].startswith("Weather data by Open-Meteo.com")


def test_a_place_to_set_instead_of_an_error(hz, monkeypatch):
    monkeypatch.delenv("HZ_WEATHER__LOCATIONS")
    assert hz("weather", "conditions").json["needs_location"] is True
    item = next(entry for entry in hz("system", "ui", "status").json if entry["id"] == "weather:weather-now")
    assert item["item"]["text"] == "Set a location"


@pytest.mark.parametrize("operation", [(), ("show",), ("forecast",), ("signals",)])
def test_weather_results_keep_the_source_with_the_data(hz, operation):
    result = hz("weather", *operation).json
    source = result["now"] if operation == ("show",) else result
    assert "Open-Meteo.com (CC BY 4.0)" in source["attribution"]


@pytest.mark.parametrize("operation", [(), ("show",), ("forecast",)])
def test_rendered_weather_credits_the_provider(hz, operation):
    assert "Open-Meteo.com (CC BY 4.0)" in hz("weather", *operation, json=False).output
