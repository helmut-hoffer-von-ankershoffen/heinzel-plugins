from datetime import timedelta

import pytest
from heinzel import ActionLet, NavLet, StatusLet, WidgetLet

from heinzel_weather import _weather_card, _weather_status, module

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
    assert navigation[0].sidebar.command == "hz weather show"


def test_weather_status_and_today_card_expose_condition_and_accessible_forecast_actions(service):
    observed = service().ui_weather()
    status = _weather_status(observed)
    card = _weather_card(observed)

    assert status.icon == "sun"
    assert "☀" not in status.text
    assert status.detail[0].text == "Clear sky · Berlin, DE"
    assert status.effect.command == "hz weather show"
    assert card.label == "Weather in Berlin, DE"
    assert card.value == "22°C"
    assert card.avatar.accessories == ["umbrella"]
    assert card.caption.startswith("clear sky · Weather data by OpenWeather")
