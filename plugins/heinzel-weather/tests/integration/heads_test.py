"""Heinzelmännchen's heads with this plugin discovered through its real entry point, against the fake OpenWeather."""

import tomllib

import pytest
from fastapi.testclient import TestClient
from heinzel.heads import api
from heinzel.kernel import user_config_dir

from heinzel_weather import WeatherService, fake
from heinzel_weather._module import API_KEY

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def openweather(monkeypatch):
    """Every service asks the fake OpenWeather, for Berlin, with a key from the environment."""
    monkeypatch.setattr(WeatherService, "transport", fake.transport())
    monkeypatch.setenv("HZ_WEATHER__PROVIDER", "openweather")
    monkeypatch.setenv("HZ_WEATHER__LOCATIONS", '["Berlin, DE"]')
    monkeypatch.setenv("HZ_WEATHER__UNITS", "metric")
    monkeypatch.setenv("HZ_CREDENTIAL_WEATHER_API_KEY", "test-key")


def test_hz_weather_is_the_weather_now(hz):
    now = hz("weather").json
    assert now["temperature"] == 21.5
    assert now["location"] == "Berlin, DE"
    assert (now["latitude"], now["longitude"]) == (52.52, 13.405)
    assert "21.5" not in hz("weather", json=False).output  # text rounds
    assert "22°C clear sky in Berlin, DE" in hz("weather", json=False).output


def test_show_and_forecast_take_a_location(hz):
    report = hz("weather", "show", "--location", "Lisbon, PT").json
    assert report["now"]["location"] == "Lisbon, DE"  # the fake finds every place at the same spot
    assert (report["now"]["latitude"], report["now"]["longitude"]) == (52.52, 13.405)
    assert len(report["hours"]) == 12
    assert report["alerts"][0]["event"] == "Thunderstorm warning"
    assert "Thunderstorm warning" in hz("weather", "show", json=False).output
    assert len(hz("weather", "forecast", "--days", "3").json["days"]) == 3
    assert hz("weather", "forecast", "--days", "9").exit_code != 0


def test_an_unknown_place_and_a_missing_key_are_errors_with_a_fix(hz, monkeypatch):
    assert hz("weather", "show", "--location", "Atlantis").exit_code == 1
    monkeypatch.delenv("HZ_CREDENTIAL_WEATHER_API_KEY")
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    result = hz("weather", json=False)
    assert result.exit_code == 1
    assert "hz system credential set weather.api-key" in result.output


def test_doctor_reports_where_the_weather_is_for(hz):
    checks = hz("system", "doctor").json["checks"]["weather"]
    assert [(check["name"], check["status"]) for check in checks] == [("locations", "up")]


def test_doctor_reports_what_is_missing(hz, monkeypatch):
    monkeypatch.delenv("HZ_WEATHER__LOCATIONS")
    monkeypatch.delenv("HZ_CREDENTIAL_WEATHER_API_KEY")
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    checks = hz("system", "doctor").json["checks"]["weather"]
    assert [check["status"] for check in checks] == ["degraded", "degraded"]


def test_the_rest_head_serves_the_weather(hz_kernel):
    client = TestClient(api.build(hz_kernel), base_url="http://127.0.0.1")
    response = client.get("/weather")
    assert response.status_code == 200, response.text
    assert response.json()["temperature"] == 21.5
    assert (response.json()["latitude"], response.json()["longitude"]) == (52.52, 13.405)
    shown = client.get("/weather/show", params={"location": "52.52,13.405"}).json()["now"]
    assert shown["location"] == "52.52,13.405"
    assert (shown["latitude"], shown["longitude"]) == (52.52, 13.405)
    assert client.get("/weather/signals").json()["weather"] == "clear"


def test_the_watch_job_is_advertised_to_the_daemon(hz):
    jobs = hz("system", "daemon", "jobs").json
    assert "weather:watch" in [job["job"] for job in jobs]


def test_app_weather_items_are_discoverable_with_readable_status_and_controls(hz):
    status = hz("system", "ui", "status", "--item", "weather:weather-now").json[0]
    widgets = hz("system", "ui", "widgets").json
    widget = next(item for item in widgets if item["id"] == "weather:weather-today")
    forecast = next(item for item in widgets if item["id"] == "weather:forecast-today")
    actions = hz("system", "ui", "actions").json
    navigation = hz("system", "ui", "navigation").json

    assert status["refresh"] == widget["refresh"] == forecast["refresh"] == 900
    assert status["item"]["icon"] == "sun"
    assert status["item"]["text"].startswith("22°C Berlin, DE")
    assert status["item"]["effect"] == {"kind": "command", "command": "hz weather show", "runs": True}
    assert widget["widget"]["label"] == "Weather in Berlin, DE"
    assert widget["widget"]["value"] == "22°C"
    assert "Weather data by OpenWeather" in widget["widget"]["caption"]
    assert widget["widget"]["avatar"]["accessories"] == ["umbrella"]
    assert forecast["widget"]["items"][-1]["text"].startswith("Weather data by OpenWeather")
    assert not any(action["id"] == "weather:weather-report" for action in actions)
    weather = next(entry for entry in navigation if entry["id"] == "weather:weather")
    assert weather["title"] == "Weather"
    assert weather["settings"]["sections"] == ["weather"]


def test_setup_saves_places_and_units_and_stores_the_key(hz, hz_prompter, hz_credentials, monkeypatch):
    monkeypatch.delenv("HZ_WEATHER__LOCATIONS")
    hz_prompter.answers += ["y", "Lisbon, PT; 52.52,13.405", "imperial", "openweather", "y", "a-new-key"]
    result = hz("setup", "weather", json=False)
    assert result.exit_code == 0, (result.output, hz_prompter.transcript)
    saved = tomllib.loads((user_config_dir() / "config.toml").read_text(encoding="utf-8"))
    assert saved == {"weather": {"locations": ["Lisbon, PT", "52.52,13.405"], "units": "imperial"}}
    assert "a-new-key" not in "\n".join(hz_prompter.transcript)
    assert hz_credentials.get(API_KEY) == "a-new-key"
