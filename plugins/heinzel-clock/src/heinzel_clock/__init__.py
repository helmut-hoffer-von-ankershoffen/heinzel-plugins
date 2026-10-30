"""What time it is for everyone on the team.

The whole plugin: one module, its settings, one operation, a health check, a setup step, and three views of the
operation for the web app: a status item, a header action and a Today widget (ADR 0056). Heinzelmännchen provides the
CLI command, MCP tool, REST endpoint, configuration, validation, health reporting, the setup wizard and the web app.
"""

import warnings
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Self, cast
from zoneinfo import ZoneInfo, available_timezones

from heinzel import (
    Check,
    ConfigEditor,
    DetailLine,
    HeinzelError,
    LiveClock,
    MetricWidget,
    Module,
    ModuleSettings,
    Navigate,
    NavSettings,
    Prompter,
    Status,
    StatusItem,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator
from rich.table import Table

module = Module("clock", "World clock: what time it is for everyone on the team.")

module.nav(
    title="World clock",
    icon="clock",
    settings=NavSettings(sections=("clock",), group="preferences"),
    sidebar=Navigate(path="/?panel=clock:world-clock"),
)

DEFAULT_HOURS = (9, 18)
SLEEP_HOURS = (22, 6)
DEFAULT_ZONES = ("Europe/Berlin", "America/New_York", "America/Los_Angeles")
SATURDAY = 5
"""`datetime.weekday()` of Saturday: working days are Monday to Friday."""
MAX_MATCHES = 15
"""More matches than this, and setup asks for more of the name instead of listing them."""
EXAMPLE = "hz system config set clock.zones '[{ name = \"Europe/Berlin\", hours = [9, 18] }]'"
Hour = Annotated[int, Field(ge=0, le=24)]
"""An hour of the day; 24 ends a working day at midnight."""


class Zone(BaseModel):
    """A time zone the team works in and the working hours there; a plain name gets the default hours."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(
        title="Time zone",
        description="The time zone, such as Europe/Berlin.",
        json_schema_extra={"format": "iana-timezone"},
    )
    hours: tuple[Hour, Hour] = Field(
        default=DEFAULT_HOURS,
        title="Working hours",
        description="When a working day starts and ends there.",
        json_schema_extra={"x-unit": "hour-of-day"},
    )

    @model_validator(mode="before")
    @classmethod
    def _from_name(cls, data: Any) -> Any:  # noqa: ANN401 - whatever the configuration holds
        return {"name": data} if isinstance(data, str) else data

    @model_validator(mode="after")
    def _check_hours(self) -> Self:
        start, end = self.hours
        if not 0 <= start < end <= 24:  # noqa: PLR2004 - hours of a day
            msg = f"hours of {self.name} must be [start, end] with 0 <= start < end <= 24, not [{start}, {end}]"
            raise ValueError(msg)
        return self


@module.settings
class ClockSettings(ModuleSettings):
    """Where the team is, and when it works there."""

    zones: list[Zone] = Field(
        max_length=64,
        default=[Zone(name=name) for name in DEFAULT_ZONES],
        title="Time zones",
        description="The time zones your team works in, with the working hours in each. The first one is primary.",
        examples=[[{"name": "Asia/Tokyo", "hours": [10, 19]}]],
    )
    working_hours: tuple[int, int] | None = Field(
        default=None,
        description="Deprecated: the hours of every zone given by name only. Give each zone its hours instead.",
        json_schema_extra={"deprecated": True},  # the web app's Settings leave it out; doctor reports it when set
    )

    @model_validator(mode="before")
    @classmethod
    def _migrate(cls, data: Any) -> Any:  # noqa: ANN401 - whatever the configuration holds
        """Read the old shape: one `working_hours` for every zone, and zones as names only."""
        if not isinstance(data, dict):
            return data
        data = cast("dict[str, Any]", data)
        if data.get("working_hours") is None:
            return data
        warnings.warn(
            f"clock.working_hours is deprecated: give each zone its hours, with `hz setup clock` or `{EXAMPLE}`",
            DeprecationWarning,
            stacklevel=2,
        )
        hours = data["working_hours"]
        zones = data.get("zones", DEFAULT_ZONES)
        return {**data, "zones": [{"name": z, "hours": hours} if isinstance(z, str) else z for z in zones]}


class ZoneTime(BaseModel):
    """The time in one zone."""

    zone: str = Field(description="IANA time zone name, e.g. Europe/Berlin.")
    time: str = Field(description="Local weekday and time there, e.g. Mon 14:05.")
    hours: tuple[int, int] = Field(description="Start and end hour of a working day there.")
    working: bool = Field(description="Whether it is within the working hours there, Monday to Friday.")
    primary: bool = Field(default=False, description="Whether this is the primary zone: the first one configured.")


def _render(times: list[ZoneTime]) -> Table:
    table = Table()
    for column in ("Zone", "Time", "Working hours", "Working"):
        table.add_column(column)
    for item in times:
        zone = f"{item.zone} (Primary)" if item.primary else item.zone
        table.add_row(zone, item.time, f"{item.hours[0]:02d}-{item.hours[1]:02d}", "yes" if item.working else "no")
    return table


@module.operation(render=_render, audience="everyday")
def clock(
    settings: ClockSettings,
    at: Annotated[datetime | None, Field(description="Moment to show instead of now (ISO 8601).")] = None,
) -> list[ZoneTime]:
    """Show the time in each of the team's time zones.

    Raises:
        HeinzelError: If a configured zone is unknown.
    """
    if unknown := _unknown(settings):
        msg = f"Unknown time zones: {', '.join(unknown)}. Run `hz system doctor` for the fix."
        raise HeinzelError(msg)
    moment = at.astimezone(UTC) if at else datetime.now(UTC)
    return [
        ZoneTime(
            zone=zone.name,
            time=local.strftime("%a %H:%M"),
            hours=zone.hours,
            working=local.weekday() < SATURDAY and zone.hours[0] <= local.hour < zone.hours[1],
            primary=index == 0,
        )
        for index, zone in enumerate(settings.zones)
        for local in [moment.astimezone(ZoneInfo(zone.name))]
    ]


def city(zone: str) -> str:
    """`America/Los_Angeles` as people say it: `Los Angeles`."""
    return zone.rsplit("/", 1)[-1].replace("_", " ")


def _work_status(zone: ZoneTime, moment: datetime) -> str:
    """Keep the workday countdown in this plugin, including the next weekday after Friday."""
    local = moment.astimezone(ZoneInfo(zone.zone))
    if local.weekday() >= SATURDAY:
        return "Weekend"
    current = local.hour * 60 + local.minute
    start, end = (hour * 60 for hour in zone.hours)
    if current < start:
        label, minutes = "Starts", start - current
    elif current < end:
        label, minutes = "Ends", end - current
    else:
        days = 1
        while (local.weekday() + days) % 7 >= SATURDAY:
            days += 1
        label, minutes = "Starts", days * 24 * 60 + start - current
    hours, minutes = divmod(minutes, 60)
    duration = f"{hours}h {minutes}m" if hours else f"{minutes}m"
    return f"{label} in {duration}"


def _detail(zone: ZoneTime, *, primary: bool = False) -> DetailLine:
    moment = datetime.now(UTC)
    local = moment.astimezone(ZoneInfo(zone.zone))
    working_now = local.weekday() < SATURDAY and zone.hours[0] <= local.hour < zone.hours[1]
    icon = (
        "briefcase-business"
        if working_now
        else "moon"
        if local.hour < SLEEP_HOURS[1] or local.hour >= SLEEP_HOURS[0]
        else "party-popper"
    )
    if "badge" not in DetailLine.model_fields:
        return DetailLine(
            text=f"{city(zone.zone)} (Primary)" if primary else city(zone.zone),
            live=LiveClock(zone=zone.zone),
            secondary=_work_status(zone, moment),
            tone="ok" if working_now else "neutral",
        )
    return DetailLine.model_validate(
        {
            "text": city(zone.zone),
            "live": LiveClock(zone=zone.zone),
            "secondary": _work_status(zone, moment),
            "badge": "Primary" if primary else None,
            "icon": icon,
            "tooltip": "Working" if working_now else "Sleeping" if icon == "moon" else "Off duty",
            "tone": "ok" if working_now else "neutral",
        }
    )


@module.status(source="clock", name="primary-zone", order=900, slots={"footer": True})
def primary_zone(times: list[ZoneTime]) -> StatusItem | None:
    """The primary zone with every configured zone in its live detail."""
    if not times:
        return None
    first = times[0]
    return StatusItem(
        text=city(first.zone),
        icon="globe",
        live=LiveClock(zone=first.zone),
        presentation="value",
        detail=[_detail(zone, primary=index == 0) for index, zone in enumerate(times)],
        effect=Navigate(path="/?panel=clock:world-clock"),
    )


@module.status(source="clock", name="zones-ticker", order=900, slots={"sidebar": True})
def zones_ticker(times: list[ZoneTime]) -> StatusItem | None:
    """All zones on a continuous live line with an accessible static alternative."""
    if not times:
        return None
    return StatusItem(
        text="World clock",
        icon="globe",
        presentation="ticker",
        segments=[_detail(zone) for zone in times],
        effect=Navigate(path="/?panel=clock:world-clock"),
    )


def working(times: list[ZoneTime]) -> int:
    """How many of the team's zones are within working hours now."""
    return sum(zone.working for zone in times)


module.action(
    "team-clock",
    label="World clock",
    icon="globe",
    effect=Navigate(path="/?panel=clock:world-clock"),
    source="clock",
    badge=working,
)


@module.widget(source="clock")
def at_work(times: list[ZoneTime]) -> MetricWidget | None:
    """How many of the team's zones are at work now, out of all of them."""
    if not times:
        return None
    count = working(times)
    return MetricWidget(label="Zones at work now", value=f"{count}/{len(times)}", tone="ok" if count else "neutral")


@module.health
def zones(settings: ClockSettings) -> list[Check]:
    """Every configured zone must be a known IANA time zone; the old settings shape is deprecated."""
    checks: list[Check] = []
    if unknown := _unknown(settings):
        checks.append(Check(name="zones", status=Status.DOWN, detail=f"unknown: {', '.join(unknown)}", fix=EXAMPLE))
    else:
        checks.append(Check(name="zones", status=Status.UP, detail=", ".join(map(_describe, settings.zones))))
    if settings.working_hours is not None:
        checks.append(
            Check(
                name="working_hours",
                status=Status.DEGRADED,
                detail="clock.working_hours is deprecated; each zone has its own hours now",
                fix="Run `hz setup clock`, or give clock.zones hours and `hz system config unset clock.working_hours`",
            )
        )
    return checks


@module.setup
def setup(settings: ClockSettings, prompter: Prompter, editor: ConfigEditor) -> None:
    """Pick the team's time zones and the working hours in each."""
    zones = list(settings.zones)
    if zones:
        names = [zone.name for zone in zones]
        keep = prompter.choices("Time zones to keep", names, default=names)
        zones = [zone for zone in zones if zone.name in keep]
    zones += _add_zones(prompter, [zone.name for zone in zones])
    chosen = [_hours(prompter, zone) for zone in zones]
    prompter.say("The team's time zones:")
    for zone in chosen:
        prompter.say(f"  {_describe(zone)}")
    if not prompter.confirm("Save these time zones?"):
        prompter.say("Nothing was saved.")
        return
    path = editor.write("clock.zones", [zone.model_dump(mode="json") for zone in chosen])
    prompter.say(f"Saved to {path}.")
    if settings.working_hours is not None:
        # The zones now carry their hours. It may be set where setup doesn't write (a project file, HZ_* variables).
        with suppress(HeinzelError):
            editor.unset("clock.working_hours")


def search(query: str) -> list[str]:
    """IANA time zone names containing `query`, ignoring case; spaces match underscores (`new york`)."""
    needle = query.strip().lower().replace(" ", "_")
    return sorted(name for name in available_timezones() if needle in name.lower())


def _add_zones(prompter: Prompter, taken: list[str]) -> list[Zone]:
    added: list[Zone] = []
    while True:
        query = prompter.text("Add a time zone: part of a city or region, empty when done", default="")
        if not query:
            if taken or added:
                return added
            prompter.say("The team needs at least one time zone.")
            continue
        matches = search(query)
        if not matches:
            prompter.say(f"No time zone matches {query!r}; try a city such as Tokyo or a region such as America.")
            continue
        if len(matches) > MAX_MATCHES:
            prompter.say(f"{len(matches)} time zones match {query!r}; type more of the name.")
            continue
        name = matches[0] if len(matches) == 1 else prompter.choice("Which one?", matches)
        if name in taken or name in {zone.name for zone in added}:
            prompter.say(f"{name} is already in the list.")
            continue
        added.append(Zone(name=name))
        prompter.say(f"Added {name}.")


def _hours(prompter: Prompter, zone: Zone) -> Zone:
    start = prompter.number(f"{zone.name}: working day starts at", default=zone.hours[0], minimum=0, maximum=23)
    end = prompter.number(
        f"{zone.name}: working day ends at", default=max(zone.hours[1], start + 1), minimum=start + 1, maximum=24
    )
    return Zone(name=zone.name, hours=(start, end))


def _describe(zone: Zone) -> str:
    return f"{zone.name} {zone.hours[0]:02d}-{zone.hours[1]:02d}"


def _unknown(settings: ClockSettings) -> list[str]:
    return [zone.name for zone in settings.zones if zone.name not in available_timezones()]


module.view(
    Path(__file__).parent / "views",
    abi=1,
    name="world-clock",
    source="clock",
    title="World clock",
    fallback="World clock is unavailable; run hz clock for the text view.",
    refresh=60,
)
