"""What a review asked for: the key never leaks, odd answers don't break anything, long alerts are noticed once."""

import logging
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from heinzel import HeinzelError
from rich.console import Console

import heinzel_weather
from heinzel_weather import Condition, Units, fake
from heinzel_weather._api import OpenWeather
from heinzel_weather._models import Change
from heinzel_weather._watch import fresh

pytestmark = pytest.mark.unit

KEY = "secret-key-5678"
NOW = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)


def test_the_key_never_reaches_the_logs(caplog):
    caplog.set_level(logging.DEBUG)
    with OpenWeather("https://api.example.org", KEY, fake.transport(NOW)) as weather:
        weather.one_call(1, 2, Units.METRIC)
    assert "appid=***" in caplog.text
    assert KEY not in caplog.text


def test_the_key_is_not_in_the_exception_chain():
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(str(request.url), request=request)

    with (
        OpenWeather("https://api.example.org", KEY, httpx.MockTransport(fail)) as weather,
        pytest.raises(HeinzelError) as raised,
    ):
        weather.one_call(1, 2, Units.METRIC)
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None


def polar(answer: dict) -> dict:
    del answer["current"]["sunrise"], answer["current"]["sunset"]
    for day in answer["daily"]:
        del day["sunrise"], day["sunset"]
    return answer


def test_polar_night_has_no_sunrise_and_still_works(service, monkeypatch):
    monkeypatch.setattr(fake, "one_call", lambda units="metric", now=None, real=fake.one_call: polar(real(units, now)))
    report = service().report()
    assert report.now.sunrise is None
    assert report.days[0].sunset is None
    assert service().signals().weather is Condition.CLEAR


def test_markup_in_a_description_is_shown_as_text(service, monkeypatch):
    def marked(units="metric", now=None, real=fake.one_call):
        answer = real(units, now)
        answer["hourly"][1]["weather"][0]["description"] = "[/x] [link=https://example.org]rain"
        return answer

    monkeypatch.setattr(fake, "one_call", marked)
    console = Console(record=True, width=120)
    console.print(heinzel_weather._render_report(service().report()))
    assert "[link=https://example.org]rain" in console.export_text()


def test_an_alert_lasting_a_week_is_noticed_once(service, monkeypatch):
    def week(units="metric", now=None, real=fake.one_call):
        answer = real(units, now)
        answer["alerts"][0]["end"] = int((NOW + timedelta(days=8)).timestamp())
        return answer

    monkeypatch.setattr(fake, "one_call", week)
    watcher = service()
    assert [change.kind for change in watcher.watch(None).changes].count("alert") == 1
    for day in range(1, 8):  # past KEEP (3 days): the alert is still in effect, so it is still remembered
        moment = NOW + timedelta(days=day)
        watcher.clock = lambda moment=moment: moment
        assert all(change.kind != "alert" for change in watcher.watch(None).changes), day


def test_a_swing_is_noticed_once_in_twelve_hours():
    swing = Change(kind="swing", key="swing:Berlin, DE:2026-10-23T1600Z:drops", title="", body="", urgent=False)
    later = swing.model_copy(update={"key": "swing:Berlin, DE:2026-10-23T1800Z:drops"})
    assert fresh([later], {swing.key: NOW}, NOW + timedelta(hours=2)) == []
    assert fresh([later], {swing.key: NOW}, NOW + timedelta(hours=13)) == [later]
