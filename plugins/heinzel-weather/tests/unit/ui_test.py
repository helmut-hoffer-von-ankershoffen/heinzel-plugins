from datetime import timedelta
from pathlib import Path

import pytest
from heinzel import ActionLet, NavLet, StatusLet, WidgetLet

from heinzel_weather import _weather_card, _weather_status, module
from heinzel_weather._service import local_city

pytestmark = pytest.mark.unit


def test_weather_ui_placements_share_one_read_only_source_and_refresh_every_900_seconds():
    lets = module.lets
    statuses = [let for let in lets if isinstance(let, StatusLet)]
    widgets = [let for let in lets if isinstance(let, WidgetLet)]
    actions = [let for let in lets if isinstance(let, ActionLet)]
    navigation = [let for let in lets if isinstance(let, NavLet)]

    assert [(item.source, item.name, item.refresh, dict(item.slots)) for item in statuses] == [
        ("ui", "weather-now", timedelta(seconds=900), {"footer": True, "sidebar": True})
    ]
    assert [(item.source, item.name, item.refresh) for item in widgets] == [
        ("ui", "weather-today", timedelta(seconds=900)),
        ("ui", "forecast-today", timedelta(seconds=900)),
    ]
    assert not actions
    assert len(navigation) == 1
    assert navigation[0].settings.sections == ("weather",)
    assert navigation[0].sidebar.path == "/?settings=weather"  # the place is set in Settings, not typed in a terminal


def test_weather_status_and_today_card_expose_condition_and_accessible_forecast_actions(service):
    observed = service().ui_weather()
    status = _weather_status(observed)
    card = _weather_card(observed)

    assert status.icon == "sun"
    assert "☀" not in status.text
    assert status.detail[0].text == "Clear sky · Berlin, DE"
    assert status.effect is None
    assert [(action.label, action.effect.path) for action in status.actions] == [("Change place", "/?settings=weather")]
    assert card.label == "Weather in Berlin, DE"
    assert card.value == "22°C"
    assert card.avatar.accessories == ["umbrella"]
    assert card.caption.startswith("clear sky · Weather data by OpenWeather")


def test_without_a_place_the_status_opens_this_plugins_settings_never_a_terminal(service):
    status = _weather_status(service(locations=[]).ui_weather())
    assert status.text == "Set a location"
    assert status.effect.kind == "navigate"
    assert status.effect.path == "/?settings=weather"


def test_without_a_place_the_city_of_the_time_zone_is_used_and_said_so(service):
    made = service(locations=[])
    made.zone_city = lambda: "Berlin"
    assert (made.places, made.guessed) == (["Berlin"], True)
    assert made.conditions().guessed is True
    configured = service()
    configured.zone_city = lambda: "Lisbon"
    assert (configured.places, configured.guessed) == (["Berlin, DE"], False)


def test_a_time_zone_city_comes_from_the_machines_zone_link(monkeypatch):
    monkeypatch.setattr("pathlib.Path.readlink", lambda _self: Path("/var/db/timezone/zoneinfo/America/Sao_Paulo"))
    assert local_city() == "Sao Paulo"
    monkeypatch.setattr("pathlib.Path.readlink", lambda _self: Path("/usr/share/zoneinfo/UTC"))
    assert local_city() is None
    monkeypatch.setattr("pathlib.Path.readlink", lambda _self: (_ for _ in ()).throw(OSError()))
    assert local_city() is None
