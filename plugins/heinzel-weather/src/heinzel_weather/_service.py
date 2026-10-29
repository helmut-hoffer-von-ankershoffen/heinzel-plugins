"""The weather module's logic, independent of any head: ask OpenWeather, check the answer, shape it, watch it."""

import json
import os
import tempfile
from collections.abc import Callable  # noqa: TC003 - pydantic and the kernel read annotations at runtime
from datetime import UTC, datetime, timedelta, timezone, tzinfo
from pathlib import Path
from threading import Lock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from heinzel import Credentials, HeinzelError, NoticeKind, Notifications, Settings, clean_text
from pydantic import BaseModel, ConfigDict, ValidationError

from heinzel_weather._api import OneCall, OpenWeather, Place, RawCondition, RawHour, coordinates
from heinzel_weather._conditions import accessories, condition, icon, units_for_locale
from heinzel_weather._models import (
    Alert,
    Change,
    Conditions,
    Day,
    Forecast,
    Hour,
    Info,
    Now,
    Provider,
    Report,
    Signals,
    UiWeather,
    Units,
    Watched,
    WeatherSettings,
)
from heinzel_weather._module import API_KEY, FALLBACK_VARIABLE
from heinzel_weather._openmeteo import ATTRIBUTION, LICENSE_URL, OpenMeteo
from heinzel_weather._watch import changes, fresh, prune

HOURS = 12
"""How many of the next hours a report shows."""
DAYS = 5
"""How many days a report shows by default; OpenWeather forecasts eight."""
MAX_DAYS = 8
UI_REFRESH = timedelta(minutes=15)
"""The one refresh interval for every weather value shown in the app."""
NO_LOCATION = (
    "No location is set. Set yours with `hz setup weather`, or "
    "`hz system config set weather.locations '[\"Berlin, DE\"]'`."
)
NOTICE_KIND: NoticeKind = NoticeKind.PLUGIN
"""The kind of the module's notices: the core's kind for plugins once it has one; until then doctor's, whose switch
in `[system.notify]` they follow."""


class _Watch(BaseModel):
    """What the watch job remembers between runs, in `<state_dir>/weather/watch.json`."""

    model_config = ConfigDict(extra="ignore")

    checked_at: datetime | None = None
    noticed: dict[str, datetime] = {}


class _Places(BaseModel):
    """The configured places OpenWeather found, in `<state_dir>/weather/places.json`, so each is looked up once."""

    model_config = ConfigDict(extra="ignore")

    places: dict[str, Place] = {}


class WeatherService:
    """Everything the weather module does; operations stay thin and call into it."""

    transport: httpx.BaseTransport | None = None
    """Replaces the network, in tests: an `httpx.MockTransport`, such as `heinzel_weather.fake.transport()`."""

    def __init__(self, settings: WeatherSettings, credentials: Credentials, hz: Settings) -> None:
        """Create the service; the module's settings, the credentials and Heinzelmännchen's settings are injected."""
        self._settings = settings
        self._credentials = credentials
        self._watch_file = hz.state_dir / "weather" / "watch.json"
        self._places_file = hz.state_dir / "weather" / "places.json"
        self.clock: Callable[[], datetime] = lambda: datetime.now(UTC)
        """What time it is; a fixed one in tests."""
        self._ui_cache: UiWeather | None = None
        self._ui_attempted_at: datetime | None = None
        self._ui_error: str | None = None
        self._ui_lock = Lock()

    @property
    def units(self) -> Units:
        """The configured units, or those of your locale."""
        return self._settings.units or units_for_locale()

    @property
    def provider(self) -> Provider:
        """Who the weather comes from."""
        return self._settings.provider

    def has_key(self) -> bool:
        """Whether an API key is stored or in `OPENWEATHER_API_KEY`."""
        return self._key() is not None

    def ready(self) -> bool:
        """Whether the weather can be asked: Open-Meteo always, OpenWeather once it has a key."""
        return self.provider is Provider.OPEN_METEO or self.has_key()

    def attribution(self) -> str:
        """Where the weather comes from, and the licence the provider asks to be shown."""
        return (
            ATTRIBUTION if self.provider is Provider.OPEN_METEO else "Weather data by OpenWeather, openweathermap.org"
        )

    def info(self, version: str, heinzel: str) -> Info:
        """What the plugin is, who serves the weather, and the attribution that goes with the data."""
        keyless = self.provider is Provider.OPEN_METEO
        return Info(
            version=version,
            heinzel=heinzel,
            provider=self.provider,
            keyless=keyless,
            attribution=self.attribution(),
            license_url=LICENSE_URL if keyless else None,
        )

    def conditions(self) -> Conditions:
        """The weather now, the next days and what to wear, or that a place is still to be set (no error)."""
        if not self._settings.locations:
            return Conditions(
                needs_location=True,
                now=None,
                days=[],
                accessories=[],
                provider=self.provider,
                attribution=self.attribution(),
            )
        report = self.report()
        return Conditions(
            needs_location=False,
            now=report.now,
            days=report.days[:4],
            accessories=accessories(report.now, units=report.now.units, rain=self._settings.rain_chance),
            provider=self.provider,
            attribution=self.attribution(),
        )

    def primary(self) -> str:
        """The primary location: the first configured one.

        Raises:
            HeinzelError: If none is configured.
        """
        if not self._settings.locations:
            raise HeinzelError(NO_LOCATION)
        return self._settings.locations[0]

    def now(self) -> Now:
        """The weather now at the primary location."""
        return self.report().now

    def ui_weather(self) -> UiWeather:
        """Return the app's shared primary observation, asking the provider at most once every 15 minutes.

        Raises:
            HeinzelError: If no observation has been cached and no location/key is available or the provider fails.
        """
        with self._ui_lock:
            now = self.clock()
            cached = self._ui_cache
            if self._ui_attempted_at is not None and now - self._ui_attempted_at < UI_REFRESH:
                if cached is not None:
                    return cached
                if self._ui_error is not None:
                    raise HeinzelError(self._ui_error)
            self._ui_attempted_at = now
            try:
                result = UiWeather(conditions=self.conditions(), fetched_at=now, stale=False)
            except HeinzelError as error:
                self._ui_error = str(error)
                if cached is None:
                    raise
                stale = cached.model_copy(update={"stale": True})
                self._ui_cache = stale
                return stale
            self._ui_error = None
            self._ui_cache = result
            return result

    def report(self, location: str | None = None, days: int = DAYS) -> Report:
        """The weather now, the next hours and `days` days, and alerts, at `location` or the primary one.

        Raises:
            HeinzelError: If no location is configured, the API key is missing, or OpenWeather fails.
        """
        query = location or self.primary()
        if self.provider is Provider.OPEN_METEO:
            with OpenMeteo(self.transport) as meteo:
                place = self._place(meteo, query)
                answer = meteo.one_call(place.lat, place.lon, self.units)
        else:
            with OpenWeather(self._settings.base_url, self._require_key(), self.transport) as weather:
                place = self._place(weather, query)
                answer = weather.one_call(place.lat, place.lon, self.units)
        report = _report(answer, place, self.units, self.clock(), min(max(days, 1), MAX_DAYS))
        return report.model_copy(update={"now": report.now.model_copy(update={"attribution": self.attribution()})})

    def forecast(self, location: str | None = None, days: int = DAYS) -> Forecast:
        """The next `days` days at `location` or the primary one."""
        report = self.report(location, days)
        return Forecast(
            location=report.now.location, units=report.now.units, days=report.days, attribution=self.attribution()
        )

    def signals(self) -> Signals:
        """The weather now and today's sun at the primary location, for a theme to follow."""
        now = self.now()
        return Signals(
            weather=now.condition,
            sunrise=now.sunrise,
            sunset=now.sunset,
            location=now.location,
            attribution=self.attribution(),
        )

    def watch(self, notifications: Notifications | None) -> Watched:
        """Check the primary location's forecast once `refresh_minutes` passed and record a notice for each change.

        Quietly does nothing while no location is set, or an OpenWeather key is missing: `hz system doctor` says what
        is missing. A failed
        check counts as a check, so a refusing or unreachable OpenWeather is asked again only after `refresh_minutes`.

        Raises:
            HeinzelError: If OpenWeather fails; the daemon reports the run as failed.
        """
        now = self.clock()
        state = _read(_Watch, self._watch_file)
        recent = state.checked_at and now - state.checked_at < timedelta(minutes=self._settings.refresh_minutes)
        if recent or not self._settings.locations or not self.ready():
            return Watched(checked=False, checked_at=state.checked_at, changes=[], noticed=0)
        state.checked_at = now
        try:
            report = self.report()
        finally:
            _write(self._watch_file, state)
        found = changes(report, now=now, rain_chance=self._settings.rain_chance, swing=self._settings.temperature_swing)
        new = fresh(found, state.noticed, now)
        noticed = sum(
            1 for change in new if notifications is not None and _notify(notifications, change, self.attribution())
        )
        # An alert still in effect stays remembered for as long as it lasts, not just KEEP after it was first seen.
        current = {change.key: now for change in found if change.kind == "alert"}
        state.noticed = prune({**state.noticed, **current, **{change.key: now for change in new}}, now)
        _write(self._watch_file, state)
        return Watched(checked=True, checked_at=now, changes=new, noticed=noticed)

    def _key(self) -> str | None:
        return self._credentials.get(API_KEY) or os.environ.get(FALLBACK_VARIABLE) or None

    def _require_key(self) -> str:
        if (key := self._key()) is None:
            msg = (
                "The OpenWeather API key is missing. Get one at home.openweathermap.org/api_keys (subscribe to the "
                f"free One Call API 3.0), then `hz system credential set weather.api-key`, or set {FALLBACK_VARIABLE}."
            )
            raise HeinzelError(msg)
        return key

    def _place(self, client: OpenWeather | OpenMeteo, query: str) -> Place:
        if (found := coordinates(query)) is not None:
            return Place(name=f"{found[0]:g},{found[1]:g}", lat=found[0], lon=found[1])
        if query not in self._settings.locations:
            return client.geocode(query)  # asked for once, e.g. by an agent: not worth remembering
        key = f"{self.provider.value}:{' '.join(query.lower().split())}"
        cache = _read(_Places, self._places_file)
        if key not in cache.places:
            cache.places[key] = client.geocode(query)
            _write(self._places_file, cache)
        return cache.places[key]


def _read[M: BaseModel](model: type[M], path: Path) -> M:
    try:
        return model.model_validate_json(path.read_bytes())
    except (OSError, ValidationError):
        return model()


def _write(path: Path, state: BaseModel) -> None:
    """Replace `path` atomically, readable by you only (it holds your places); a failure loses a cache, no more."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(state.model_dump(mode="json"), file)
        Path(temporary).replace(path)
    except OSError:
        return


def _notify(notifications: Notifications, change: Change, attribution: str) -> bool:
    notice = notifications.emit(
        NOTICE_KIND,
        change.title,
        f"{change.body} {attribution}",
        route="/",
        command="hz weather show",
        key=f"weather:{change.key}",
        urgent=change.urgent,
    )
    return notice is not None


def _label(place: Place) -> str:
    return clean_text(", ".join(part for part in (place.name, place.country) if part))


def _zone(answer: OneCall) -> tzinfo:
    try:
        return ZoneInfo(answer.timezone)
    except (ValueError, ZoneInfoNotFoundError):
        return timezone(timedelta(seconds=answer.timezone_offset))


def _at(timestamp: int, zone: tzinfo) -> datetime:
    return datetime.fromtimestamp(timestamp, zone)


def _maybe(timestamp: int | None, zone: tzinfo) -> datetime | None:
    return None if timestamp is None else _at(timestamp, zone)


def _night(raw: RawCondition) -> bool:
    """Whether OpenWeather draws it as night: its icon codes end in `n` (`01n`), in `d` by day."""
    return raw.icon.endswith("n")


def _describe(raw: RawCondition) -> str:
    return clean_text(raw.description)


def _report(answer: OneCall, place: Place, units: Units, now: datetime, days: int) -> Report:
    zone = _zone(answer)
    current = answer.current
    sky = current.weather[0]
    sunrise, sunset = _maybe(current.sunrise, zone), _maybe(current.sunset, zone)
    observed = _at(current.dt, zone)
    local_today = now.astimezone(zone).date()
    today = next((raw for raw in answer.daily if _at(raw.dt, zone).date() >= local_today), None)
    weather = condition(sky.id, temperature=current.temp, wind_speed=current.wind_speed, units=units)
    return Report(
        now=Now(
            location=_label(place),
            latitude=place.lat,
            longitude=place.lon,
            condition=weather,
            description=_describe(sky),
            icon=icon(weather, night=_night(sky)),
            temperature=current.temp,
            feels_like=current.feels_like,
            high=today.temp.max if today else current.temp,
            low=today.temp.min if today else current.temp,
            rain_chance=today.pop if today else 0.0,
            humidity=current.humidity,
            wind_speed=current.wind_speed,
            units=units,
            observed_at=observed,
            sunrise=sunrise,
            sunset=sunset,
        ),
        hours=[_hour(raw, zone, units) for raw in answer.hourly if _at(raw.dt, zone) + timedelta(hours=1) > now][
            :HOURS
        ],
        days=[
            Day(
                day=_at(raw.dt, zone).date(),
                condition=(
                    c := condition(raw.weather[0].id, temperature=raw.temp.max, wind_speed=raw.wind_speed, units=units)
                ),
                description=_describe(raw.weather[0]),
                icon=icon(c),
                high=raw.temp.max,
                low=raw.temp.min,
                rain_chance=raw.pop,
                sunrise=_maybe(raw.sunrise, zone),
                sunset=_maybe(raw.sunset, zone),
            )
            for raw in answer.daily
            if _at(raw.dt, zone).date() >= local_today
        ][:days],
        alerts=[
            Alert(
                event=clean_text(raw.event),
                sender=clean_text(raw.sender_name),
                start=_at(raw.start, zone),
                end=_at(raw.end, zone),
                description=clean_text(raw.description),
            )
            for raw in answer.alerts
        ],
    )


def _hour(raw: RawHour, zone: tzinfo, units: Units) -> Hour:
    at = _at(raw.dt, zone)
    weather = condition(raw.weather[0].id, temperature=raw.temp, wind_speed=raw.wind_speed, units=units)
    rain = (raw.rain.one_hour if raw.rain else 0.0) + (raw.snow.one_hour if raw.snow else 0.0)
    return Hour(
        at=at,
        condition=weather,
        description=_describe(raw.weather[0]),
        icon=icon(weather, night=_night(raw.weather[0])),
        temperature=raw.temp,
        rain_chance=raw.pop,
        rain_mm=rain,
    )
