"""The weather page: one answer with now, 24 hours, 7 days and alerts, or in words why there is none."""

from datetime import timedelta

import pytest
from heinzel import HeinzelError, Navigate, ViewLet

from heinzel_weather import PageState, WeatherPage, module
from heinzel_weather._service import PAGE_DAYS, PAGE_HOURS

pytestmark = pytest.mark.unit


def test_the_sidebar_item_opens_the_page_and_the_page_is_a_view_of_the_page_operation():
    (nav,) = [let for let in module.lets if let.__class__.__name__ == "NavLet"]
    assert nav.sidebar == Navigate(path="/plugins/weather/forecast")
    assert nav.settings.sections == ("weather",)  # Settings stay reachable in Settings
    (view,) = [let for let in module.lets if isinstance(let, ViewLet)]
    assert (view.name, view.source, view.title) == ("forecast", "page", "Weather")
    assert (view.slot, view.route) == ("page", nav.sidebar.path)  # the main area, never a side panel


def test_a_ready_page_has_the_next_24_hours_and_7_days_from_the_shared_report(service):
    page = service().page()
    assert page.state is PageState.READY
    assert page.report is not None
    assert (len(page.report.hours), len(page.report.days)) == (PAGE_HOURS, PAGE_DAYS) == (24, 7)
    assert page.report.now.location == "Berlin, DE"
    assert (page.stale, page.guessed, page.message) == (False, False, "")


def test_the_text_report_keeps_its_twelve_hours_and_five_days(service):
    report = service().report()
    assert (len(report.hours), len(report.days)) == (12, 5)


def test_the_page_and_the_status_share_one_fetch(service, monkeypatch):
    weather = service()
    calls = []
    original = weather.report
    monkeypatch.setattr(weather, "report", lambda **kw: calls.append(kw) or original(**kw))
    weather.page()
    weather.ui_weather()
    assert calls == [{"days": PAGE_DAYS, "hours": PAGE_HOURS}]


def test_without_a_place_the_page_asks_for_one(service):
    page = service(locations=[]).page()
    assert (page.state, page.report) == (PageState.NEEDS_LOCATION, None)


def test_a_failing_first_fetch_is_an_unavailable_page_with_the_reason_never_an_error(service, monkeypatch):
    weather = service()

    def fail(**_):
        msg = "Open-Meteo can't be reached."
        raise HeinzelError(msg)

    monkeypatch.setattr(weather, "report", fail)
    page = weather.page()
    assert (page.state, page.report, page.message) == (PageState.UNAVAILABLE, None, "Open-Meteo can't be reached.")
    assert isinstance(page, WeatherPage)


def test_a_failed_refresh_keeps_the_last_report_and_says_stale(service, monkeypatch):
    weather = service()
    elapsed = [0.0]
    weather.monotonic = lambda: elapsed[0]
    fresh = weather.page()
    first = weather.clock()
    weather.clock = lambda: first + timedelta(minutes=15)
    elapsed[0] = 900

    def fail(**_):
        msg = "down"
        raise HeinzelError(msg)

    monkeypatch.setattr(weather, "report", fail)
    stale = weather.page()
    assert (stale.state, stale.stale, stale.report) == (PageState.READY, True, fresh.report)
    assert stale.fetched_at == first


def test_the_page_json_is_what_the_view_reads(service):
    data = service().page().model_dump(mode="json")
    assert data["state"] == "ready"
    assert data["report"]["now"]["units"] == "metric"
    assert data["report"]["hours"][0]["at"][10] == "T"  # ISO with the place's own offset
    assert data["report"]["now"]["wind_speed"] > 0
