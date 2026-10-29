"""Read-only workflow evidence shares the app observation and leaves delivery to its caller."""

from datetime import UTC, datetime, timedelta

import pytest
from heinzel import HeinzelError

pytestmark = pytest.mark.unit
NOW = datetime(2026, 10, 23, 10, 0, tzinfo=UTC)


def test_workflow_and_app_share_one_fetch_through_the_fifteen_minute_boundary(service, monkeypatch):
    weather = service()
    report = weather.report()
    elapsed = [0.0]
    weather.monotonic = lambda: elapsed[0]
    calls = []
    monkeypatch.setattr(weather, "report", lambda: calls.append(True) or report)
    observed = weather.observation()
    shown = weather.ui_weather()
    assert observed.report == report
    assert observed.provider.value == "openweather"
    assert observed.fetched_at == shown.fetched_at == NOW
    assert shown.conditions.now == report.now
    assert [change.kind for change in observed.changes] == ["rain", "swing", "alert"]
    weather.clock = lambda: NOW + timedelta(seconds=899)
    elapsed[0] = 899
    assert weather.observation() == observed
    assert len(calls) == 1
    weather.clock = lambda: NOW + timedelta(minutes=15)
    elapsed[0] = 900
    assert weather.observation().fetched_at == NOW + timedelta(minutes=15)
    assert len(calls) == 2


def test_stale_evidence_retains_lineage_but_cannot_offer_actionable_changes(service, monkeypatch):
    weather = service()
    elapsed = [0.0]
    weather.monotonic = lambda: elapsed[0]
    fresh = weather.observation()
    weather.clock = lambda: NOW + timedelta(minutes=15)
    elapsed[0] = 900
    attempts = []

    def unavailable():
        attempts.append(True)
        msg = "Provider unavailable"
        raise HeinzelError(msg)

    monkeypatch.setattr(weather, "report", unavailable)
    stale = weather.observation()
    assert stale.report == fresh.report
    assert stale.fetched_at == fresh.fetched_at
    assert stale.stale is True
    assert stale.changes == []
    assert weather.ui_weather().stale is True
    assert weather.observation() == stale
    assert len(attempts) == 1


def test_wall_clock_rollback_does_not_extend_freshness_or_unblock_stale_changes(service, monkeypatch):
    weather = service()
    elapsed = [0.0]
    wall = [NOW]
    weather.monotonic = lambda: elapsed[0]
    weather.clock = lambda: wall[0]
    report = weather.report()
    attempts = []

    def provider():
        attempts.append(True)
        if len(attempts) == 1:
            return report
        msg = "Provider unavailable"
        raise HeinzelError(msg)

    monkeypatch.setattr(weather, "report", provider)
    first = weather.observation()
    assert first.fetched_at == NOW

    # NTP/manual correction moves wall time backwards after the real 15-minute cache interval elapsed.
    elapsed[0] = 901
    wall[0] = NOW - timedelta(hours=2)
    stale = weather.observation()
    assert stale.stale is True
    assert stale.report == first.report
    assert stale.changes == []
    assert len(attempts) == 2

    # A second backwards wall-clock jump cannot make the stale report fresh or retry early.
    elapsed[0] += 60
    wall[0] = NOW - timedelta(days=1)
    assert weather.observation() == stale
    assert weather.observation().changes == []
    assert len(attempts) == 2


def test_missing_location_is_explicit_and_does_not_fetch(service, monkeypatch):
    weather = service(locations=[])
    monkeypatch.setattr(weather, "report", lambda: pytest.fail("must not fetch without a location"))
    observed = weather.observation()
    assert observed.needs_location is True
    assert observed.report is None
    assert observed.changes == []
    assert observed.stale is False
    assert weather.ui_weather().conditions.needs_location is True


def test_first_provider_failure_is_not_a_successful_empty_observation(service, monkeypatch):
    weather = service()
    attempts = []

    def unavailable():
        attempts.append(True)
        msg = "Provider unavailable"
        raise HeinzelError(msg)

    monkeypatch.setattr(weather, "report", unavailable)
    for _ in range(2):
        with pytest.raises(HeinzelError, match="Provider unavailable"):
            weather.observation()
    assert len(attempts) == 1


def test_cached_alert_rain_and_swing_expire_at_their_exact_clock_boundary(service, monkeypatch):
    weather = service()
    report = weather.report()
    boundary = NOW + timedelta(minutes=1)
    rain = report.hours[1].model_copy(update={"at": NOW - timedelta(minutes=59)})
    swing = report.hours[6].model_copy(update={"at": boundary})
    alert = report.alerts[0].model_copy(update={"start": NOW - timedelta(hours=1), "end": boundary})
    report = report.model_copy(update={"hours": [rain, swing], "alerts": [alert]})
    calls = []
    monkeypatch.setattr(weather, "report", lambda: calls.append(True) or report)
    original = weather.observation()
    assert [item.kind for item in original.changes] == ["rain", "swing", "alert"]
    weather.clock = lambda: boundary - timedelta(seconds=1)
    assert [item.kind for item in weather.observation().changes] == ["rain", "swing", "alert"]
    weather.clock = lambda: boundary
    expired = weather.observation()
    assert expired.changes == []
    assert expired.report == original.report
    assert expired.fetched_at == original.fetched_at == NOW
    assert not expired.stale
    assert len(calls) == 1
    assert [item.kind for item in original.changes] == ["rain", "swing", "alert"]


def test_cached_forecast_signal_enters_the_approved_window_without_another_provider_call(service, monkeypatch):
    weather = service()
    report = weather.report()
    rain = report.hours[1].model_copy(update={"at": NOW + timedelta(minutes=65), "temperature": report.now.temperature})
    report = report.model_copy(update={"hours": [rain], "alerts": []})
    calls = []
    monkeypatch.setattr(weather, "report", lambda: calls.append(True) or report)
    original = weather.observation()
    assert original.changes == []
    weather.clock = lambda: NOW + timedelta(minutes=5) - timedelta(seconds=1)
    assert weather.observation().changes == []
    weather.clock = lambda: NOW + timedelta(minutes=5)
    entered = weather.observation()
    assert [item.kind for item in entered.changes] == ["rain"]
    assert entered.fetched_at == NOW
    assert entered.report == original.report
    assert weather.ui_weather().fetched_at == NOW
    assert len(calls) == 1
