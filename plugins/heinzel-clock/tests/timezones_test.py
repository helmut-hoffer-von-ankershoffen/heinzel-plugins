from datetime import UTC, datetime

import pytest
from heinzel import ListEntry, ListWidget, Navigate

from heinzel_clock import ZoneTime, common_hours, timezones, working_windows

pytestmark = pytest.mark.unit

PANEL = Navigate(path="/?panel=clock:world-clock")
TEAM = [
    ZoneTime(zone="Europe/Berlin", time="", hours=(9, 18), working=False, primary=True),
    ZoneTime(zone="America/New_York", time="", hours=(9, 18), working=False),
    ZoneTime(zone="America/Los_Angeles", time="", hours=(9, 18), working=False),
]


def at(text: str) -> datetime:
    return datetime.fromisoformat(text).astimezone(UTC)


def lines(widget: ListWidget) -> list[tuple[str, str | None]]:
    return [(item.text, item.detail) for item in widget.items]


def test_the_widget_is_titled_timezones_and_says_who_works_and_when_everyone_overlaps():
    widget = timezones(TEAM, at("2026-10-26T15:30:00Z"))
    assert widget.title == "Timezones"
    assert lines(widget) == [
        ("2 of 3 zones working", "Everyone overlaps 17:00\u201318:00 today"),
        ("Los Angeles 08:30 · \u22128 h · Off", "Works 09\u201318 · starts in 30 m"),
        ("New York 11:30 · \u22125 h · Working", "Works 09\u201318 · ends in 6 h 30 m"),
        ("Berlin 16:30 · you · Working", "Works 09\u201318 · ends in 1 h 30 m"),
    ]
    assert [item.tone for item in widget.items] == ["ok", "neutral", "ok", "ok"]
    assert all(item.effect == PANEL for item in widget.items)


def test_the_headline_says_until_when_everyone_works_while_they_overlap():
    widget = timezones(TEAM, at("2026-10-26T16:15:00Z"))
    assert lines(widget)[0] == ("3 of 3 zones working", "Everyone works until 18:00")


def test_the_overlap_follows_each_zones_daylight_saving_time():
    pair = TEAM[:2]
    summer = common_hours(pair, at("2026-10-27T06:00:00Z"))
    winter = common_hours(pair, at("2026-11-03T06:00:00Z"))
    assert summer == (at("2026-10-27T13:00:00Z"), at("2026-10-27T17:00:00Z"))
    assert winter == (at("2026-11-03T14:00:00Z"), at("2026-11-03T17:00:00Z"))
    assert lines(timezones(pair, at("2026-11-03T06:00:00Z")))[0] == (
        "0 of 2 zones working",
        "Everyone overlaps 15:00\u201318:00 today",
    )


def test_a_working_day_that_starts_in_a_skipped_hour_starts_after_the_gap():
    cairo = ZoneTime(zone="Africa/Cairo", time="", hours=(0, 6), working=False)
    windows = working_windows(cairo, at("2026-04-23T12:00:00Z"))
    assert (at("2026-04-23T22:00:00Z"), at("2026-04-24T03:00:00Z")) in windows


def test_the_weekend_is_off_and_the_next_overlap_names_its_day():
    widget = timezones(TEAM[:2], at("2026-10-31T12:00:00Z"))
    assert lines(widget) == [
        ("0 of 2 zones working", "No common hours today; next Mon 15:00\u201318:00"),
        ("New York 08:00 · \u22125 h · Off", "Works 09\u201318 · starts Mon 15:00"),
        ("Berlin 13:00 · you · Off", "Works 09\u201318 · starts Mon 09:00"),
    ]


def test_without_any_overlap_this_week_the_headline_names_the_next_start():
    widget = timezones(TEAM, at("2026-11-02T06:00:00Z"))
    assert common_hours(TEAM, at("2026-11-02T06:00:00Z")) is None
    assert lines(widget)[0] == ("0 of 3 zones working", "No common working hours; Berlin starts in 2 h")


def test_across_the_date_line_the_weekday_differs_and_the_weekend_comes_first():
    pair = [
        ZoneTime(zone="Pacific/Honolulu", time="", hours=(9, 18), working=False, primary=True),
        ZoneTime(zone="Pacific/Kiritimati", time="", hours=(9, 18), working=False),
    ]
    widget = timezones(pair, at("2026-10-30T10:00:00-10:00"))
    assert lines(widget) == [
        ("1 of 2 zones working", "No common hours today; next Mon 09:00\u201318:00"),
        ("Honolulu 10:00 · you · Working", "Works 09\u201318 · ends in 8 h"),
        ("Kiritimati Sat 10:00 · +24 h · Off", "Works 09\u201318 · starts Sun 09:00"),
    ]


def test_night_is_its_own_state_and_partial_hour_offsets_show_minutes():
    pair = [TEAM[0], ZoneTime(zone="Asia/Kolkata", time="", hours=(10, 19), working=False)]
    widget = timezones(pair, at("2026-10-26T19:00:00Z"))
    assert lines(widget)[1:] == [
        ("Berlin 20:00 · you · Off", "Works 09\u201318 · starts in 13 h"),
        ("Kolkata Tue 00:30 · +4:30 h · Night", "Works 10\u201319 · starts in 9 h 30 m"),
    ]


def test_one_zone_speaks_of_its_own_hours():
    widget = timezones(TEAM[:1], at("2026-10-26T07:00:00Z"))
    assert lines(widget)[0] == ("0 of 1 zone working", "Works 09:00\u201318:00 today")


def test_many_zones_fit_the_list_with_a_count_of_the_rest():
    names = ["UTC", "Asia/Tokyo", "Asia/Dubai", "Europe/Paris", "Europe/Lisbon", "America/Chicago", "Asia/Seoul"]
    team = [TEAM[0], *(ZoneTime(zone=name, time="", hours=(9, 18), working=False) for name in names)]
    widget = timezones(team, at("2026-10-26T10:00:00Z"))
    assert len(widget.items) == 8
    assert widget.items[-1] == ListEntry(text="+2 more zones in the World clock", effect=PANEL)


def test_a_zone_configured_twice_shows_once():
    assert len(timezones([TEAM[0], TEAM[0]], at("2026-10-26T10:00:00Z")).items) == 2


def test_without_zones_the_widget_says_how_to_add_them():
    widget = timezones([], at("2026-10-26T10:00:00Z"))
    assert widget.items == [
        ListEntry(text="No time zones yet", detail="Add your team's zones in the World clock", effect=PANEL)
    ]
