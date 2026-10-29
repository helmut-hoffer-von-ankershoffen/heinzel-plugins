"""Open-Meteo, keyless: the recorded Lisbon answers (tests/fixtures) behind an httpx.MockTransport, offline."""

from datetime import UTC, datetime

import httpx
import pytest
from heinzel import HeinzelError, Settings

from heinzel_weather import Conditions, Provider, Units, WeatherService, WeatherSettings
from heinzel_weather._conditions import accessories
from heinzel_weather._module import API_KEY
from heinzel_weather._openmeteo import ATTRIBUTION, FORECAST_URL, GEOCODING_URL, OpenMeteo

pytestmark = pytest.mark.unit

METEO_NOW = datetime(2026, 10, 24, 23, 30, tzinfo=UTC)  # 00:30 in Lisbon on the 25th, after the recorded answer


@pytest.fixture
def requests() -> list[httpx.Request]:
    return []


@pytest.fixture
def make(tmp_path, requests, meteo):
    def build(**settings: object) -> WeatherService:
        from heinzel import Credentials
        from heinzel.testing import MemoryBackend

        service = WeatherService(
            WeatherSettings(**{"locations": ["Lisbon, PT"], "units": "metric", **settings}),
            Credentials(MemoryBackend(), [("weather", API_KEY)]),
            Settings(state_dir=tmp_path / "state"),
        )
        service.transport = meteo(requests)
        service.clock = lambda: METEO_NOW
        return service

    return build


def test_open_meteo_is_the_default_and_needs_no_key(make, requests):
    service = make()
    assert service.provider is Provider.OPEN_METEO
    assert service.ready()
    assert not service.has_key()
    report = service.report()
    assert report.now.location == "Lisbon, PT"
    assert (report.now.latitude, report.now.longitude) == (38.72509, -9.1498)
    assert report.now.temperature == 12.4
    assert report.now.description == "mainly clear"
    assert report.now.icon == "☾"  # it is night there
    assert [r.url.host for r in requests] == ["geocoding-api.open-meteo.com", "api.open-meteo.com"]
    assert all("appid" not in str(r.url) and "key" not in r.url.params for r in requests)


def test_the_qualifier_picks_the_country_and_a_wrong_one_is_an_error(make):
    assert make(locations=["Lisbon, US"]).report().now.location == "Lisbon, US"
    with pytest.raises(HeinzelError, match="knows no place"):
        make(locations=["Lisbon, XX"]).report()


def test_days_hours_and_rain_come_from_the_forecast(make):
    report = make().report(days=3)
    assert len(report.days) == 3
    assert [round(day.rain_chance, 1) for day in report.days] == [0.0, 0.0, 0.8]
    assert report.days[2].description == "rain"
    assert report.days[0].sunrise is not None
    assert len(report.hours) == 12
    assert [hour.description for hour in report.hours[3:6]] == ["light rain"] * 3  # 03:00 to 05:00
    assert report.alerts == []


def test_conditions_say_what_the_heinzelmaennchen_wears(make):
    rainy = make().conditions()
    assert rainy.now is not None
    assert rainy.provider is Provider.OPEN_METEO
    assert rainy.attribution == ATTRIBUTION
    assert "CC BY 4.0" in rainy.attribution
    assert len(rainy.days) == 4
    assert rainy.accessories == []  # mainly clear at night, a dry day ahead, 12 degrees


def test_accessories_follow_rain_sun_and_cold(make):
    now = make().report().now
    wet = now.model_copy(update={"rain_chance": 0.9})
    assert accessories(wet, units=Units.METRIC, rain=0.5) == ["umbrella"]
    sunny = now.model_copy(update={"condition": "clear", "observed_at": now.sunrise.replace(hour=12)})
    assert accessories(sunny, units=Units.METRIC, rain=0.5) == ["sunglasses"]
    cold = now.model_copy(update={"temperature": 2.0})
    assert accessories(cold, units=Units.METRIC, rain=0.5) == ["scarf"]
    assert accessories(cold.model_copy(update={"temperature": 40.0}), units=Units.IMPERIAL, rain=0.5) == ["scarf"]
    both = wet.model_copy(update={"temperature": 2.0})
    assert accessories(both, units=Units.METRIC, rain=0.5) == ["umbrella", "scarf"]


def test_no_location_is_a_conditions_answer_not_an_error(make):
    result = make(locations=[]).conditions()
    assert result.needs_location
    assert result.now is None
    assert result.accessories == []


def test_imperial_asks_open_meteo_for_fahrenheit_and_mph(make, requests):
    make(units="imperial").report()
    params = requests[-1].url.params
    assert (params["temperature_unit"], params["wind_speed_unit"]) == ("fahrenheit", "mph")


def test_a_failing_open_meteo_is_an_error_that_names_the_host_not_the_url(meteo):
    with OpenMeteo(meteo(status=429)) as client, pytest.raises(HeinzelError) as raised:
        client.geocode("Lisbon, PT")
    assert str(raised.value).startswith("Open-Meteo (geocoding-api.open-meteo.com) answered 429")
    assert "Lisbon" not in str(raised.value)
    assert GEOCODING_URL.startswith("https://")
    assert FORECAST_URL.startswith("https://")


def test_a_shape_it_does_not_know_is_an_error(tmp_path):
    odd = httpx.MockTransport(lambda _request: httpx.Response(200, json={"results": [{"name": 1}]}))
    with OpenMeteo(odd) as client, pytest.raises(HeinzelError, match="shape"):
        client.geocode("Lisbon")


def test_the_openweather_path_still_needs_its_key(make):
    service = make(provider="openweather")
    assert not service.ready()
    with pytest.raises(HeinzelError, match="API key is missing"):
        service.report()


def test_info_names_the_provider_and_its_licence(make):
    info = make().info("0.1.0", "0.7.0")
    assert info.keyless
    assert info.attribution == ATTRIBUTION
    assert info.license_url == "https://creativecommons.org/licenses/by/4.0/"
    assert Conditions.model_fields["attribution"]


def test_location_queries_are_redacted_from_request_logs(make, requests, caplog):
    import logging

    caplog.set_level(logging.INFO, logger="httpx")
    make().report()
    assert len(requests) == 2
    assert "location-redacted" in caplog.text
    assert "Lisbon" not in caplog.text
    assert "latitude=" not in caplog.text
    assert "longitude=" not in caplog.text


def test_an_oversized_stream_stops_before_the_rest_is_downloaded(monkeypatch):
    import heinzel_weather._openmeteo as meteo

    monkeypatch.setattr(meteo, "MAX_BYTES", 8)
    consumed = []
    closed = []

    class Body(httpx.SyncByteStream):
        def __iter__(self):
            for chunk in [b"1234", b"56789", b"never read"]:
                consumed.append(chunk)
                yield chunk

        def close(self):
            closed.append(True)

    transport = httpx.MockTransport(lambda _request: httpx.Response(200, stream=Body()))
    with OpenMeteo(transport) as client, pytest.raises(HeinzelError, match="more than 8 bytes"):
        client.geocode("Lisbon")
    assert consumed == [b"1234", b"56789"]
    assert closed == [True]


def test_a_stream_failure_has_no_location_in_its_exception_chain():
    class BrokenBody(httpx.SyncByteStream):
        def __iter__(self):
            yield b'{"results":'
            msg = "latitude=38.7223&longitude=-9.1393"
            raise httpx.ReadError(msg)

    transport = httpx.MockTransport(lambda _request: httpx.Response(200, stream=BrokenBody()))
    with OpenMeteo(transport) as client, pytest.raises(HeinzelError) as raised:
        client.geocode("Lisbon")
    assert "ReadError" in str(raised.value)
    assert "38.7223" not in str(raised.value)
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
