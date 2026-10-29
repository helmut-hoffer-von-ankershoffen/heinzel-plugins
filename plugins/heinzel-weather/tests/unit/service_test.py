from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event

import pytest
from heinzel import HeinzelError, Notice, NoticeKind, Notifications

from heinzel_weather import Condition, Units
from heinzel_weather._module import API_KEY
from heinzel_weather._service import NOTICE_KIND
from heinzel_weather._watch import fresh, prune

pytestmark = pytest.mark.unit

NOW = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)  # the fixtures' clock, conftest.NOW


class Recorder(Notifications):
    def __init__(self) -> None:
        self.emitted: list[dict] = []

    def emit(self, kind, title, body="", *, route, command, key, urgent=False) -> Notice | None:  # noqa: PLR0913
        self.emitted.append({"kind": kind, "title": title, "body": body, "key": key, "urgent": urgent, "route": route})
        return Notice(
            id=str(len(self.emitted)),
            kind=kind,
            title=title,
            body=body,
            route=route,
            command=command,
            key=key,
            urgent=urgent,
            at=NOW,
            due=NOW,
            popup=True,
        )


def test_the_report_is_shaped_in_the_places_time_zone(service):
    report = service().report()
    assert report.now.location == "Berlin, DE"
    assert (report.now.latitude, report.now.longitude) == (52.52, 13.405)
    assert report.now.temperature == 21.5
    assert report.now.condition is Condition.CLEAR
    assert (report.now.high, report.now.low, report.now.rain_chance) == (24.0, 11.5, 0.8)
    assert report.now.observed_at.utcoffset() == timedelta(hours=2)
    assert len(report.hours) == 12
    assert report.hours[0].at == NOW
    assert report.hours[1].condition is Condition.RAIN
    assert [day.day.isoformat() for day in report.days][:2] == ["2026-10-23", "2026-10-24"]
    assert len(report.days) == 5
    assert report.alerts[0].event == "Thunderstorm warning"


def test_the_report_keeps_the_geocoded_place_coordinates_when_forecast_grid_differs(service, monkeypatch):
    weather = service()
    place = weather._place

    def geocode(client, query):
        found = place(client, query)
        return found.model_copy(update={"lat": 52.51, "lon": 13.40})

    monkeypatch.setattr(weather, "_place", geocode)
    report = weather.report()
    assert (report.now.latitude, report.now.longitude) == (52.51, 13.40)


def test_imperial_units_and_coordinates(service):
    now = service(units="imperial").report("38.72,-9.14").now
    assert now.units is Units.IMPERIAL
    assert now.temperature == 70.7
    assert now.location == "38.72,-9.14"
    assert (now.latitude, now.longitude) == (38.72, -9.14)


def test_forecast_and_signals(service):
    assert len(service().forecast(days=8).days) == 8
    signals = service().signals()
    assert signals.weather is Condition.CLEAR
    assert signals.sunrise < signals.sunset


def test_app_weather_uses_one_observation_until_the_900_second_boundary(service, monkeypatch):
    weather = service()
    report = weather.report()
    calls = 0

    def counted_report(*args, **kwargs):
        nonlocal calls
        calls += 1
        return report

    monkeypatch.setattr(weather, "report", counted_report)
    assert weather.ui_weather().conditions.now == report.now
    weather.clock = lambda: NOW + timedelta(seconds=899)
    assert weather.ui_weather().conditions.now == report.now
    assert calls == 1
    weather.clock = lambda: NOW + timedelta(seconds=900)
    assert weather.ui_weather().conditions.now == report.now
    assert calls == 2


def test_simultaneous_app_placements_share_the_initial_provider_request(service, monkeypatch):
    weather = service()
    report = weather.report()
    entered, release = Event(), Event()
    calls = 0

    def counted_report(*args, **kwargs):
        nonlocal calls
        calls += 1
        entered.set()
        assert release.wait(timeout=2)
        return report

    monkeypatch.setattr(weather, "report", counted_report)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(weather.ui_weather)
        assert entered.wait(timeout=2)
        second = pool.submit(weather.ui_weather)
        release.set()
        assert first.result(timeout=2) == second.result(timeout=2)
    assert calls == 1


def test_app_keeps_the_last_observation_and_marks_it_stale_on_refresh_failure(service, monkeypatch):
    weather = service()
    fresh = weather.ui_weather()
    weather.clock = lambda: NOW + timedelta(minutes=16)
    attempts = 0

    def unavailable(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        msg = "OpenWeather is unavailable"
        raise HeinzelError(msg)

    monkeypatch.setattr(weather, "report", unavailable)
    stale = weather.ui_weather()
    assert stale.conditions.now == fresh.conditions.now
    assert stale.stale is True
    assert weather.ui_weather() == stale
    assert attempts == 1
    weather.clock = lambda: NOW + timedelta(minutes=31)
    assert weather.ui_weather().stale is True
    assert attempts == 2


def test_app_throttles_repeated_failures_before_the_first_observation(service, monkeypatch):
    weather = service()
    attempts = 0

    def unavailable(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        msg = "OpenWeather is unavailable"
        raise HeinzelError(msg)

    monkeypatch.setattr(weather, "report", unavailable)
    with pytest.raises(HeinzelError, match="OpenWeather is unavailable"):
        weather.ui_weather()
    weather.clock = lambda: NOW + timedelta(minutes=14, seconds=59)
    with pytest.raises(HeinzelError, match="OpenWeather is unavailable"):
        weather.ui_weather()
    assert attempts == 1
    weather.clock = lambda: NOW + timedelta(minutes=15)
    with pytest.raises(HeinzelError, match="OpenWeather is unavailable"):
        weather.ui_weather()
    assert attempts == 2


def test_without_a_location_or_key_it_says_how_to_set_them(service, credentials, monkeypatch):
    with pytest.raises(HeinzelError, match="No location is set"):
        service(locations=[]).now()
    credentials.delete(API_KEY)
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    with pytest.raises(HeinzelError, match="API key is missing"):
        service().now()
    monkeypatch.setenv("OPENWEATHER_API_KEY", "from-the-environment")
    assert service().now().temperature == 21.5


def test_the_watch_notices_rain_the_swing_and_the_alert_once(service):
    watcher, notices = service(), Recorder()
    watched = watcher.watch(notices)
    assert watched.checked
    assert [change.kind for change in watched.changes] == ["rain", "swing", "alert"]
    assert watched.noticed == 3
    assert notices.emitted[0]["title"] == "Rain in Berlin, DE from 13:00"
    assert notices.emitted[1]["title"] == "Berlin, DE: the temperature drops 10°C by 18:00"
    assert notices.emitted[2]["urgent"] is True
    assert {item["kind"] for item in notices.emitted} == {NOTICE_KIND}
    assert all(item["key"].startswith("weather:") and item["route"] == "/" for item in notices.emitted)
    assert all("Weather data by OpenWeather" in item["body"] for item in notices.emitted)
    assert not watcher.watch(notices).checked  # within refresh_minutes: nothing asked
    later = NOW + timedelta(minutes=31)
    watcher.clock = lambda: later
    assert watcher.watch(notices).changes == []  # the same news is not news again


def test_the_watch_stays_quiet_without_a_location_or_key(service):
    assert service(locations=[]).watch(None).checked is False


def test_the_watch_works_without_notifications(service):
    watched = service().watch(None)
    assert watched.checked
    assert watched.noticed == 0


def test_rain_is_noticed_at_most_once_in_three_hours_per_place(service):
    rain = service().watch(None).changes[0]
    later = rain.model_copy(update={"key": "rain:Berlin, DE:2026-10-23T14"})
    assert fresh([later], {rain.key: NOW}, NOW + timedelta(hours=1)) == []
    assert fresh([later], {rain.key: NOW}, NOW + timedelta(hours=4)) == [later]


def test_noticed_changes_are_forgotten_after_three_days():
    assert prune({"a": NOW, "b": NOW - timedelta(days=4)}, NOW) == {"a": NOW}


def test_notice_kind_is_a_known_kind():
    assert isinstance(NOTICE_KIND, NoticeKind)
