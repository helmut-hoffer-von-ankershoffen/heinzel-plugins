"""The weather module's settings and what its operations return; strict, so a head shows only what was checked."""

import ipaddress
from datetime import date, datetime
from enum import StrEnum
from typing import ClassVar, Literal
from urllib.parse import urlsplit

from heinzel import ModuleSettings
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

DEFAULT_BASE_URL = "https://api.openweathermap.org"
LOOPBACK_NAMES = frozenset({"localhost"})


class Units(StrEnum):
    """How temperatures and wind speeds are given."""

    METRIC = "metric"
    """Degrees Celsius, metres per second."""
    IMPERIAL = "imperial"
    """Degrees Fahrenheit, miles per hour."""

    @property
    def degree(self) -> str:
        """The temperature unit's symbol."""
        return "°C" if self is Units.METRIC else "°F"

    @property
    def speed(self) -> str:
        """The wind speed unit."""
        return "m/s" if self is Units.METRIC else "mph"


class Provider(StrEnum):
    """Who the weather comes from."""

    OPEN_METEO = "open-meteo"
    """Open-Meteo: no account and no key (CC BY 4.0, non-commercial use); no severe weather alerts."""
    OPENWEATHER = "openweather"
    """OpenWeather's One Call API 3.0: an API key of your own (free tier), with severe weather alerts."""


class Condition(StrEnum):
    """What the weather is like, in one word: also the `weather` signal a theme can follow."""

    CLEAR = "clear"
    CLOUDS = "clouds"
    RAIN = "rain"
    DRIZZLE = "drizzle"
    THUNDER = "thunder"
    SNOW = "snow"
    FOG = "fog"
    WIND = "wind"
    HEAT = "heat"
    COLD = "cold"


class WeatherSettings(ModuleSettings):
    """Where you want the weather for, and how: the `[weather]` table or `HZ_WEATHER__*` variables.

    With `provider = "openweather"`, the OpenWeather API key is a credential
    (`hz system credential set weather.api-key`), never a setting.
    """

    provider: Provider = Field(
        default=Provider.OPEN_METEO,
        description="Where the weather comes from: open-meteo (no key needed) or openweather (needs an API key).",
    )
    locations: list[str] = Field(
        default=[],
        description='Where you want the weather for, yours first (the primary one): a place such as "Berlin, DE" '
        'or coordinates such as "52.52,13.405".',
    )
    units: Units | None = Field(
        default=None,
        description="metric (°C, m/s) or imperial (°F, mph); unset: imperial where your locale is the US, "
        "Liberia or Myanmar, metric everywhere else.",
    )
    refresh_minutes: int = Field(
        default=15, ge=5, le=24 * 60, description="How often the daemon checks the forecast for changes, in minutes."
    )
    rain_chance: float = Field(
        default=0.5, ge=0, le=1, description="The chance of rain, 0 to 1, from which rain within the hour is news."
    )
    temperature_swing: float = Field(
        default=8,
        gt=0,
        le=50,
        description="A change of this many degrees (in your units) within the next 12 hours is news.",
    )
    base_url: str = Field(
        default=DEFAULT_BASE_URL,
        description="Where the OpenWeather API answers: https, or http on this machine only (a fake for tests "
        "and recordings, `python -m heinzel_weather.fake`).",
    )

    ignored_in_project: ClassVar[frozenset[str]] = frozenset({"base_url"})
    """A project's hz.toml must not send your API key somewhere else."""

    @field_validator("base_url")
    @classmethod
    def _secure(cls, value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme == "https" and parts.hostname:
            return value.rstrip("/")
        if parts.scheme == "http" and parts.hostname and _loopback(parts.hostname):
            return value.rstrip("/")
        msg = f"base_url must be https://..., or http:// on this machine (127.0.0.1, localhost), not {value!r}"
        raise ValueError(msg)


def _loopback(host: str) -> bool:
    if host in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")


class Now(_Strict):
    """The weather now at one place, with today's range."""

    attribution: str = Field(default="", description="Where the weather data comes from, with its licence.")

    location: str = Field(description='The place, as OpenWeather names it, e.g. "Berlin, DE".')
    latitude: float = Field(description="The selected place's latitude, in degrees north.")
    longitude: float = Field(description="The selected place's longitude, in degrees east.")
    condition: Condition = Field(description="What it is like, in one word.")
    description: str = Field(description='In words, e.g. "light rain".')
    icon: str = Field(description="One symbol for it.")
    temperature: float = Field(description="Temperature, in `units`.")
    feels_like: float = Field(description="What it feels like, in `units`.")
    high: float = Field(description="Today's high, in `units`.")
    low: float = Field(description="Today's low, in `units`.")
    rain_chance: float = Field(description="Today's chance of rain or snow, 0 to 1.")
    humidity: int = Field(description="Relative humidity, percent.")
    wind_speed: float = Field(description="Wind speed, m/s (metric) or mph (imperial).")
    units: Units = Field(description="metric or imperial.")
    observed_at: AwareDatetime = Field(description="When it was observed, in the place's time zone.")
    sunrise: AwareDatetime | None = Field(description="Today's sunrise there; none in polar day or night.")
    sunset: AwareDatetime | None = Field(description="Today's sunset there; none in polar day or night.")


class Hour(_Strict):
    """One of the next hours."""

    at: AwareDatetime = Field(description="The start of the hour, in the place's time zone.")
    condition: Condition = Field(description="What it is like, in one word.")
    description: str = Field(description="In words.")
    icon: str = Field(description="One symbol for it.")
    temperature: float = Field(description="Temperature, in the report's units.")
    rain_chance: float = Field(description="Chance of rain or snow, 0 to 1.")
    rain_mm: float = Field(description="Rain and snow expected within the hour, millimetres.")


class Day(_Strict):
    """One of the next days."""

    day: date = Field(description="The day, in the place's time zone.")
    condition: Condition = Field(description="What it is like, in one word.")
    description: str = Field(description="In words.")
    icon: str = Field(description="One symbol for it.")
    high: float = Field(description="The high, in the report's units.")
    low: float = Field(description="The low, in the report's units.")
    rain_chance: float = Field(description="Chance of rain or snow, 0 to 1.")
    sunrise: AwareDatetime | None = Field(description="Sunrise; none in polar day or night.")
    sunset: AwareDatetime | None = Field(description="Sunset; none in polar day or night.")


class Alert(_Strict):
    """A severe weather alert a national weather service issued for the place."""

    event: str = Field(description='What it warns of, e.g. "Thunderstorm warning".')
    sender: str = Field(description="Who issued it.")
    start: AwareDatetime = Field(description="From when.")
    end: AwareDatetime = Field(description="Until when.")
    description: str = Field(description="What the issuer says, in plain text.")


class Report(_Strict):
    """The weather now, the next hours and days, and alerts, at one place."""

    now: Now = Field(description="The weather now, with today's range.")
    hours: list[Hour] = Field(description="The next hours, from this one.")
    days: list[Day] = Field(description="The next days, from today.")
    alerts: list[Alert] = Field(description="Severe weather alerts in effect or ahead.")


class Forecast(_Strict):
    """The next days at one place."""

    attribution: str = Field(default="", description="Where the weather data comes from, with its licence.")

    location: str = Field(description="The place.")
    units: Units = Field(description="metric or imperial.")
    days: list[Day] = Field(description="The next days, from today.")


class Signals(_Strict):
    """What a theme can follow: the weather now and the sun at the primary location."""

    attribution: str = Field(default="", description="Where the weather data comes from, with its licence.")

    weather: Condition = Field(description="What it is like now, in one word.")
    sunrise: AwareDatetime | None = Field(description="Today's sunrise; none in polar day or night.")
    sunset: AwareDatetime | None = Field(description="Today's sunset; none in polar day or night.")
    location: str = Field(description="The primary location they are for.")


Accessory = Literal["umbrella", "sunglasses", "scarf"]
"""What the Heinzelmännchen can wear for the weather: the closed set of the web app's avatar."""


class Conditions(_Strict):
    """What the status item, the Today widgets and the avatar show: the weather now, or that no place is set."""

    needs_location: bool = Field(description="Whether no place is set yet, so there is no weather to show.")
    now: Now | None = Field(description="The weather now at the primary location; none while no place is set.")
    days: list[Day] = Field(description="The next days, from today; none while no place is set.")
    accessories: list[Accessory] = Field(
        description="What the Heinzelmännchen wears for it: umbrella, sunglasses, scarf."
    )
    provider: Provider = Field(description="Who the weather comes from.")
    attribution: str = Field(description="Where the data comes from, and under which licence if it asks one.")


class UiWeather(_Strict):
    """One observation shared by every weather item in the app."""

    conditions: Conditions
    fetched_at: AwareDatetime
    stale: bool = False


class Info(_Strict):
    """What this plugin is, which provider serves the weather, and the attribution its data asks for."""

    version: str = Field(description="This plugin's version.")
    heinzel: str = Field(description="The Heinzelmännchen it runs on.")
    provider: Provider = Field(description="Who the weather comes from.")
    keyless: bool = Field(description="Whether the provider needs no account or key.")
    attribution: str = Field(description="Where the data comes from, and under which licence if it asks one.")
    license_url: str | None = Field(description="The licence of the data, if it has one.")


class Change(_Strict):
    """Something about the weather worth a notice."""

    kind: str = Field(description="rain, swing or alert.")
    key: str = Field(description="What makes two changes the same, so one is noticed once.")
    title: str = Field(description="One line.")
    body: str = Field(description="A sentence more.")
    urgent: bool = Field(description="Whether it may interrupt outside working hours: severe weather alerts.")


class Observation(_Strict):
    """Cached weather evidence and candidate signals, without delivery or approval authority."""

    needs_location: bool = Field(description="Whether the primary location still needs to be configured.")
    report: Report | None = Field(description="The last complete report; absent until a location is configured.")
    provider: Provider = Field(description="Who supplied this observation.")
    attribution: str = Field(description="The provider attribution to retain in derived drafts.")
    fetched_at: AwareDatetime = Field(description="When this evidence was fetched; unchanged on refresh failure.")
    stale: bool = Field(description="Whether the latest refresh failed; stale evidence cannot offer new signals.")
    changes: list[Change] = Field(description="Candidate signals from this report, not delivery receipts or approval.")


class Watched(_Strict):
    """What a run of the watch job did."""

    checked: bool = Field(description="Whether it asked OpenWeather; false while the last check is recent enough.")
    checked_at: datetime | None = Field(description="When the forecast was last checked.")
    changes: list[Change] = Field(description="What changed and was new, noticed now.")
    noticed: int = Field(description="How many of them became notices (none where notifications are off).")
