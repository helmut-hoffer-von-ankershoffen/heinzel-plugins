"""What in a report is news: rain within the hour, a big temperature swing, severe weather alerts. Pure functions.

`changes` finds them in one report; `fresh` drops what was noticed before, so a change is noticed once, and rain or
a swing that keeps being forecast hour after hour is noticed once in its `QUIET` time. Keys are in UTC, so a
repeated hour when daylight saving time ends is no new news.
"""

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta

from heinzel_weather._conditions import WET
from heinzel_weather._models import Change, Report

RAIN_AHEAD = timedelta(hours=1)
"""Rain that starts within this much time is news."""
SWING_AHEAD = timedelta(hours=12)
"""A temperature swing within this much time is news."""
QUIET = {"rain": timedelta(hours=3), "swing": timedelta(hours=12)}
"""After a rain or swing notice, no other one of its kind for the same place for this long."""
KEEP = timedelta(days=3)
"""How long a noticed change is remembered."""
BODY = 200
"""The longest body of a notice, in characters."""


def changes(report: Report, *, now: datetime, rain_chance: float, swing: float) -> list[Change]:
    """What in `report` is news at `now`: rain ahead while it is dry, a swing of `swing` degrees or more, alerts."""
    return [*_rain(report, now, rain_chance), *_swing(report, now, swing), *_alerts(report, now)]


def _rain(report: Report, now: datetime, chance: float) -> list[Change]:
    if report.now.condition in WET:
        return []
    place = report.now.location
    for hour in report.hours:
        ahead = now < hour.at + timedelta(hours=1) and hour.at <= now + RAIN_AHEAD
        if ahead and hour.condition in WET and hour.rain_chance >= chance:
            local = hour.at.strftime("%H:%M")
            return [
                Change(
                    kind="rain",
                    key=f"rain:{place}:{_utc(hour.at)}",
                    title=f"Rain in {place} from {local}",
                    body=f"{round(hour.rain_chance * 100)}% chance of {hour.description}.",
                    urgent=False,
                )
            ]
    return []


def _swing(report: Report, now: datetime, swing: float) -> list[Change]:
    start = report.now.temperature
    ahead = [hour for hour in report.hours if now < hour.at <= now + SWING_AHEAD]
    if not ahead:
        return []
    extreme = max(ahead, key=lambda hour: abs(hour.temperature - start))
    delta = extreme.temperature - start
    if abs(delta) < swing:
        return []
    place, unit = report.now.location, report.now.units.degree
    direction = "rises" if delta > 0 else "drops"
    return [
        Change(
            kind="swing",
            key=f"swing:{place}:{_utc(extreme.at)}:{direction}",
            title=f"{place}: the temperature {direction} {abs(delta):.0f}{unit} by {extreme.at:%H:%M}",
            body=f"From {start:.0f}{unit} now to {extreme.temperature:.0f}{unit}, {extreme.description}.",
            urgent=False,
        )
    ]


def _alerts(report: Report, now: datetime) -> list[Change]:
    place = report.now.location
    return [
        Change(
            kind="alert",
            key=f"alert:{place}:{alert.event}:{_utc(alert.start)}",
            title=f"{alert.event} for {place}",
            body=_shorten(
                f"{alert.start:%a %H:%M} to {alert.end:%a %H:%M}"
                + (f": {alert.description}" if alert.description else ".")
            ),
            urgent=True,
        )
        for alert in report.alerts
        if alert.end > now
    ]


def fresh(found: Iterable[Change], noticed: Mapping[str, datetime], now: datetime) -> list[Change]:
    """The changes not noticed before: a new key, and no rain or swing for the same place within its `QUIET`."""
    result: list[Change] = []
    for change in found:
        if change.key in noticed:
            continue
        if (quiet := QUIET.get(change.kind)) is not None:
            prefix = f"{change.kind}:{change.key.split(':')[1]}:"
            if any(key.startswith(prefix) and now - at < quiet for key, at in noticed.items()):
                continue
        result.append(change)
    return result


def prune(noticed: Mapping[str, datetime], now: datetime) -> dict[str, datetime]:
    """What is still remembered at `now`."""
    return {key: at for key, at in noticed.items() if now - at < KEEP}


def _utc(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H%MZ")


def _shorten(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= BODY else text[: BODY - 1].rstrip() + "…"
