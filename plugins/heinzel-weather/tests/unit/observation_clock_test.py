from datetime import UTC, datetime, timedelta

import pytest
from heinzel import HeinzelError

pytestmark = pytest.mark.unit
NOW = datetime(2026, 10, 23, 10, tzinfo=UTC)


def test_suspend_gap_expires_old_observation_when_monotonic_has_not_advanced(service, monkeypatch):
    weather = service()
    weather.monotonic = lambda: 10.0
    report = weather.report()
    calls = []
    monkeypatch.setattr(weather, "report", lambda: calls.append(True) or report)
    first = weather.observation()
    weather.clock = lambda: NOW + timedelta(hours=2)
    after_suspend = weather.observation()
    assert len(calls) == 2
    assert after_suspend.fetched_at > first.fetched_at


def test_failed_refresh_after_suspend_keeps_lineage_and_throttles_from_attempt_time(service, monkeypatch):
    weather = service()
    wall = [NOW]
    elapsed = [0.0]
    weather.clock = lambda: wall[0]
    weather.monotonic = lambda: elapsed[0]
    fresh = weather.observation()
    attempts = []

    def unavailable():
        attempts.append(True)
        msg = "Provider unavailable"
        raise HeinzelError(msg)

    monkeypatch.setattr(weather, "report", unavailable)
    wall[0] = NOW + timedelta(hours=2)
    stale = weather.observation()
    assert stale.stale
    assert stale.changes == []
    assert stale.fetched_at == fresh.fetched_at
    assert stale.report == fresh.report
    assert len(attempts) == 1
    # Every surface shares the same failed attempt, not the much older report's timestamp.
    assert weather.ui_weather().stale
    assert weather.observation() == stale
    wall[0] += timedelta(seconds=899)
    assert weather.observation() == stale
    assert len(attempts) == 1
    wall[0] += timedelta(seconds=1)
    assert weather.observation() == stale
    assert len(attempts) == 2
    # A later rollback cannot prolong that attempt once elapsed time reaches the refresh boundary.
    wall[0] = NOW - timedelta(days=1)
    elapsed[0] = 899
    assert weather.observation() == stale
    assert len(attempts) == 2
    elapsed[0] = 900
    assert weather.observation() == stale
    assert len(attempts) == 3


def test_initial_provider_failure_retries_once_after_suspend_gap_and_then_throttles(service, monkeypatch):
    weather = service()
    wall = [NOW]
    weather.clock = lambda: wall[0]
    weather.monotonic = lambda: 0.0
    attempts = []

    def unavailable():
        attempts.append(True)
        msg = "Provider unavailable"
        raise HeinzelError(msg)

    monkeypatch.setattr(weather, "report", unavailable)
    with pytest.raises(HeinzelError, match="Provider unavailable"):
        weather.observation()
    wall[0] += timedelta(hours=2)
    for _ in range(2):
        with pytest.raises(HeinzelError, match="Provider unavailable"):
            weather.observation()
    assert len(attempts) == 2
