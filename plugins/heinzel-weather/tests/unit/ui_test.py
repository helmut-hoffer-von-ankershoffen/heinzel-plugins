from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from heinzel import ActionLet, NavLet, StatusLet, WidgetLet

from heinzel_weather import _temperature_chart, _weather_card, _weather_status, module
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
        ("ui", "temperature-today", timedelta(seconds=900)),
    ]
    assert {item.name: item.replaces for item in widgets} == {
        "weather-today": ("forecast-today",),  # a hidden or shown forecast card carries over to the one card
        "temperature-today": (),
    }
    assert not actions
    assert len(navigation) == 1
    assert navigation[0].settings.sections == ("weather",)
    assert navigation[0].sidebar.path == "/plugins/weather/forecast"  # the page; Settings stay behind its place button


def test_weather_status_and_today_card_expose_condition_and_accessible_forecast_actions(service):
    observed = service().ui_weather()
    status = _weather_status(observed)
    card = _weather_card(observed)

    assert status.icon == "sun"
    assert "☀" not in status.text
    assert status.detail[0].text == "Clear sky · Berlin, DE"
    assert status.effect.path == "/plugins/weather/forecast"
    assert [(action.label, action.effect.path) for action in status.actions] == [("Change place", "/?settings=weather")]
    assert card.label == "Weather in Berlin, DE"
    assert card.value == "22°C"
    assert card.avatar.accessories == ["umbrella"]
    assert card.caption == "clear sky"  # the attribution lives behind the info button of the Weather page
    assert not any("Weather data by" in line.text for line in status.detail)


def _scene(observed, **now):
    conditions = observed.conditions
    changed = conditions.model_copy(update={"now": conditions.now.model_copy(update=now)})
    return observed.model_copy(update={"conditions": changed})


def test_one_today_card_holds_the_figure_the_temperature_what_it_wears_and_the_next_three_days(service):
    observed = service().ui_weather()
    card = _weather_card(_scene(observed, temperature=-2.2, feels_like=-7.4))
    days = observed.conditions.days[1:4]

    assert card.kind == "graphic"
    assert card.size == "wide"
    assert (card.label, card.value) == ("Weather in Berlin, DE", "-2°C")
    assert card.avatar.accessories == observed.conditions.accessories == ["umbrella"]
    assert card.detail == "Feels like -7°C · wearing umbrella"
    assert [row.label for row in card.rows] == [f"{day.day:%a}" for day in days]
    assert len(card.rows) == 3
    for row, day in zip(card.rows, days, strict=True):
        assert row.value == f"{round(day.low) + 0} to {round(day.high) + 0}°C"
        assert row.detail == f"{round(day.rain_chance * 100)}% rain"
        assert row.icon is not None
        assert row.icon_label == day.description.capitalize()  # the icon in words, for a screen reader
        assert row.hint == f"{day.description.capitalize()}, {round(day.rain_chance * 100)}% rain"


def test_the_card_says_nothing_worn_when_nothing_is_and_never_shows_minus_zero(service):
    observed = service().ui_weather()
    conditions = observed.conditions.model_copy(update={"accessories": []})
    bare = _scene(observed.model_copy(update={"conditions": conditions}), temperature=-0.3, feels_like=-0.4)
    card = _weather_card(bare)
    assert (card.value, card.detail) == ("0°C", "Feels like 0°C")
    assert card.avatar.accessories == []


def test_fewer_days_give_fewer_rows_and_a_stale_reading_says_so(service):
    observed = service().ui_weather()
    conditions = observed.conditions.model_copy(update={"days": observed.conditions.days[:2]})
    card = _weather_card(observed.model_copy(update={"conditions": conditions, "stale": True}))
    assert len(card.rows) == 1
    assert card.caption == "clear sky · last observation"
    none = observed.model_copy(update={"conditions": conditions.model_copy(update={"days": []})})
    assert _weather_card(none).rows == []


def test_without_a_place_there_is_no_card(service):
    observed = service().ui_weather()
    empty = observed.model_copy(update={"conditions": observed.conditions.model_copy(update={"now": None})})
    assert _weather_card(empty) is None


def test_imperial_cards_use_fahrenheit_in_every_row(service):
    card = _weather_card(service(units="imperial").ui_weather())
    assert card.value.endswith("°F")
    assert all(row.value.endswith("°F") for row in card.rows)


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


def test_the_today_chart_shows_the_next_hours_with_rain_bars_range_and_a_now_marker(service):
    observed = service().ui_weather()
    chart = _temperature_chart(observed)
    hours = observed.conditions.hours
    assert chart is not None
    assert len(chart.series) == len(chart.bars) == min(24, len(hours)) >= 2
    assert chart.now == chart.series[0].at
    assert (chart.range.low, chart.range.high) == (observed.conditions.now.low, observed.conditions.now.high)
    assert chart.unit == observed.conditions.now.units.degree
    assert "Berlin, DE" in chart.summary
    assert len({point.at for point in chart.series}) == len(chart.series)


def test_the_today_chart_never_carries_the_data_credit(service):
    chart = _temperature_chart(service().ui_weather())
    assert chart is not None
    assert "Open-Meteo" not in chart.model_dump_json()
    assert "Weather data by" not in chart.model_dump_json()


def test_without_a_place_there_is_no_chart(service):
    observed = service().ui_weather()
    conditions = observed.conditions.model_copy(update={"now": None, "hours": []})
    empty = observed.model_copy(update={"conditions": conditions})
    assert _temperature_chart(empty) is None


def test_a_repeated_hour_from_a_clock_change_is_drawn_once(service):
    observed = service().ui_weather()
    zone = ZoneInfo("Europe/Berlin")
    first = datetime(2026, 10, 25, 2, 0, tzinfo=zone, fold=0)  # 02:00 happens twice when the clocks go back
    second = datetime(2026, 10, 25, 2, 0, tzinfo=zone, fold=1)
    template = observed.conditions.hours[0]
    hours = [
        template.model_copy(update={"at": first}),
        template.model_copy(update={"at": second}),
        template.model_copy(update={"at": datetime(2026, 10, 25, 3, 0, tzinfo=zone)}),
    ]
    conditions = observed.conditions.model_copy(update={"hours": hours})
    chart = _temperature_chart(observed.model_copy(update={"conditions": conditions}))
    assert chart is not None
    assert [point.at for point in chart.series] == ["2026-10-25T02:00", "2026-10-25T03:00"]
    assert "next 2 hours" in chart.title
    assert len(chart.bars) == 2


def test_no_pane_widget_or_cli_text_carries_the_data_credit(service):
    observed = service().ui_weather()
    shown = [
        _weather_status(observed).model_dump_json(),
        _weather_card(observed).model_dump_json(),
        _temperature_chart(observed).model_dump_json(),
    ]
    for text in shown:
        assert "Open-Meteo" not in text
        assert "CC BY" not in text
        assert "open-meteo.com" not in text
