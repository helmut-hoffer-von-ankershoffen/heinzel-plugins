"""Open-Meteo over HTTPS: its geocoding and forecast APIs, free and keyless for non-commercial use.

Open-Meteo's data is CC BY 4.0 (open-meteo.com/en/license): `ATTRIBUTION` is shown wherever the weather is. Only this
module talks to Open-Meteo, and only to the two hosts below; redirects are not followed. Errors name the host, never
the URL, because the query holds the place the person asked about. The forecast is turned into the shape the rest of
the plugin already reads (`OneCall`), so a report looks the same whichever provider served it.
"""

import json
from typing import Any, Self

import httpx
from heinzel import HeinzelError
from pydantic import BaseModel, ConfigDict, ValidationError

from heinzel_weather._api import (
    OneCall,
    Place,
    RawCondition,
    RawCurrent,
    RawDay,
    RawHour,
    RawPrecipitation,
    RawTemperatures,
)
from heinzel_weather._models import Units

FORECAST_URL = "https://api.open-meteo.com"
GEOCODING_URL = "https://geocoding-api.open-meteo.com"
TIMEOUT = 10.0
"""Seconds to wait for Open-Meteo."""
MAX_BYTES = 2_000_000
"""The most an answer may hold; a week of hours is a few tens of kilobytes."""
DAYS = 8
ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0), https://open-meteo.com/"
"""What Open-Meteo's licence asks to be shown with its data."""
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
CODES = {
    0: ("clear sky", 800),
    1: ("mainly clear", 800),
    2: ("partly cloudy", 802),
    3: ("overcast", 804),
    45: ("fog", 741),
    48: ("freezing fog", 741),
    51: ("light drizzle", 300),
    53: ("drizzle", 301),
    55: ("heavy drizzle", 302),
    56: ("light freezing drizzle", 310),
    57: ("freezing drizzle", 312),
    61: ("light rain", 500),
    63: ("rain", 501),
    65: ("heavy rain", 502),
    66: ("light freezing rain", 511),
    67: ("freezing rain", 511),
    71: ("light snow", 600),
    73: ("snow", 601),
    75: ("heavy snow", 602),
    77: ("snow grains", 600),
    80: ("light rain showers", 520),
    81: ("rain showers", 521),
    82: ("violent rain showers", 522),
    85: ("light snow showers", 620),
    86: ("heavy snow showers", 622),
    95: ("thunderstorm", 211),
    96: ("thunderstorm with hail", 221),
    99: ("thunderstorm with heavy hail", 221),
}
"""WMO weather codes as Open-Meteo reports them: the words, and the OpenWeather condition id the module reads."""
_UNKNOWN = ("unknown", 804)


class _Answer(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


class Match(_Answer):
    """A geocoding match."""

    name: str
    latitude: float
    longitude: float
    country: str = ""
    country_code: str = ""
    admin1: str = ""


class Geocoding(_Answer):
    """The geocoding API's answer; it leaves `results` out when nothing matches."""

    results: list[Match] = []


class _Current(_Answer):
    time: int
    temperature_2m: float
    apparent_temperature: float
    relative_humidity_2m: int | None = None
    weather_code: int
    wind_speed_10m: float = 0.0
    is_day: int = 1


class _Hourly(_Answer):
    time: list[int]
    temperature_2m: list[float | None]
    precipitation_probability: list[float | None] = []
    precipitation: list[float | None] = []
    weather_code: list[int | None]
    wind_speed_10m: list[float | None] = []
    is_day: list[int | None] = []


class _Daily(_Answer):
    time: list[int]
    weather_code: list[int | None]
    temperature_2m_max: list[float | None]
    temperature_2m_min: list[float | None]
    precipitation_probability_max: list[float | None] = []
    wind_speed_10m_max: list[float | None] = []
    sunrise: list[int | None] = []
    sunset: list[int | None] = []


class _Forecast(_Answer):
    timezone: str
    utc_offset_seconds: int = 0
    latitude: float
    longitude: float
    current: _Current
    hourly: _Hourly
    daily: _Daily


class OpenMeteo:
    """A client of Open-Meteo's APIs; `transport` replaces the network in tests."""

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        """Talk to Open-Meteo."""
        self._client = httpx.Client(timeout=TIMEOUT, transport=transport, headers={"User-Agent": "heinzel-weather"})

    def __enter__(self) -> Self:
        """Use the client; its connections close at the end of the block."""
        return self

    def __exit__(self, *_: object) -> None:
        """Close the connections."""
        self._client.close()

    def geocode(self, query: str) -> Place:
        """The place called `query`: a name, optionally narrowed by a country code, country or region after a comma.

        Raises:
            HeinzelError: If nothing matches, or Open-Meteo can't be asked.
        """
        name, _, qualifier = (part.strip() for part in query.partition(","))
        params = {"name": name, "count": "10", "language": "en", "format": "json"}
        matches = _parse(Geocoding, self._get(GEOCODING_URL, "/v1/search", params)).results if name else []
        wanted = qualifier.casefold()
        found = next(
            (
                m
                for m in matches
                if not wanted or wanted in {m.country_code.casefold(), m.country.casefold(), m.admin1.casefold()}
            ),
            None,
        )
        if found is None:
            msg = f"Open-Meteo knows no place called {query!r}; try a city and a country code, such as 'Berlin, DE'."
            raise HeinzelError(msg)
        return Place(
            name=found.name, lat=found.latitude, lon=found.longitude, country=found.country_code, state=found.admin1
        )

    def one_call(self, lat: float, lon: float, units: Units) -> OneCall:
        """The weather now, by the hour and by the day, at a place; there are no alerts.

        Raises:
            HeinzelError: If Open-Meteo can't be asked or answers something unexpected.
        """
        imperial = units is Units.IMPERIAL
        params = {
            "latitude": f"{lat:.4f}",
            "longitude": f"{lon:.4f}",
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,is_day",
            "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m,is_day",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,"
            "wind_speed_10m_max,sunrise,sunset",
            "timezone": "auto",
            "timeformat": "unixtime",
            "forecast_days": str(DAYS),
            "temperature_unit": "fahrenheit" if imperial else "celsius",
            "wind_speed_unit": "mph" if imperial else "ms",
            "precipitation_unit": "inch" if imperial else "mm",
        }
        return _convert(_parse(_Forecast, self._get(FORECAST_URL, "/v1/forecast", params)), imperial=imperial)

    def _get(self, base: str, path: str, params: dict[str, str]) -> Any:  # noqa: ANN401 - JSON, checked by the caller
        host = base.removeprefix("https://")
        failure = None
        body = bytearray()
        try:
            with self._client.stream("GET", f"{base}{path}", params=params) as response:
                if not response.is_success:
                    msg = (
                        f"Open-Meteo ({host}) answered {response.status_code}; it is free but rate limited, try later."
                    )
                    raise HeinzelError(msg)
                for chunk in response.iter_bytes():
                    if len(body) + len(chunk) > MAX_BYTES:
                        msg = f"Open-Meteo ({host}) answered more than {MAX_BYTES} bytes."
                        raise HeinzelError(msg)
                    body.extend(chunk)
        except httpx.HTTPError as error:
            failure = type(error).__name__
        if failure is not None:  # no exception chain may retain the request URL and its location
            msg = (
                f"Open-Meteo ({host}) can't be reached: {failure}. Check your connection; it is free but rate limited."
            )
            raise HeinzelError(msg)
        try:
            return json.loads(body)
        except ValueError:
            msg = f"Open-Meteo ({host}) answered something that isn't JSON."
            raise HeinzelError(msg) from None


def _parse[M: BaseModel](model: type[M], data: object) -> M:
    try:
        return model.model_validate(data)
    except ValidationError as error:
        fields = ", ".join(sorted({".".join(map(str, e["loc"])) for e in error.errors()})[:5])
        msg = f"Open-Meteo answered in a shape this plugin doesn't know (at {fields})."
        raise HeinzelError(msg) from None


def _sky(code: int | None, *, day: bool = True) -> RawCondition:
    description, identifier = CODES.get(code, _UNKNOWN) if code is not None else _UNKNOWN
    return RawCondition(
        id=identifier, main=description, description=description, icon=f"{identifier}{'d' if day else 'n'}"
    )


def _at[T, D](values: list[T | None], index: int, default: D) -> T | D:
    value = values[index] if index < len(values) else None
    return default if value is None else value


def _chance(values: list[float | None], index: int) -> float:
    return min(max(_at(values, index, 0.0) / 100, 0.0), 1.0)


def _convert(forecast: _Forecast, *, imperial: bool) -> OneCall:
    now, hourly, daily = forecast.current, forecast.hourly, forecast.daily
    sunrise = next((t for t in daily.sunrise if t is not None), None)
    sunset = next((t for t in daily.sunset if t is not None), None)
    hours = [
        RawHour(
            dt=at,
            temp=_at(hourly.temperature_2m, index, now.temperature_2m),
            wind_speed=_at(hourly.wind_speed_10m, index, 0.0),
            pop=_chance(hourly.precipitation_probability, index),
            weather=[_sky(_code(hourly.weather_code, index), day=bool(_at(hourly.is_day, index, 1)))],
            rain=RawPrecipitation.model_validate({"1h": _millimetres(_at(hourly.precipitation, index, 0.0), imperial)}),
        )
        for index, at in enumerate(hourly.time)
    ]
    days = [
        RawDay(
            dt=at,
            sunrise=daily.sunrise[index] if index < len(daily.sunrise) else None,
            sunset=daily.sunset[index] if index < len(daily.sunset) else None,
            temp=RawTemperatures(
                min=_at(daily.temperature_2m_min, index, now.temperature_2m),
                max=_at(daily.temperature_2m_max, index, now.temperature_2m),
            ),
            wind_speed=_at(daily.wind_speed_10m_max, index, 0.0),
            pop=_chance(daily.precipitation_probability_max, index),
            weather=[_sky(_code(daily.weather_code, index))],
        )
        for index, at in enumerate(daily.time)
    ]
    return OneCall(
        lat=forecast.latitude,
        lon=forecast.longitude,
        timezone=forecast.timezone,
        timezone_offset=forecast.utc_offset_seconds,
        current=RawCurrent(
            dt=now.time,
            sunrise=sunrise,
            sunset=sunset,
            temp=now.temperature_2m,
            feels_like=now.apparent_temperature,
            humidity=now.relative_humidity_2m or 0,
            wind_speed=now.wind_speed_10m,
            weather=[_sky(now.weather_code, day=bool(now.is_day))],
        ),
        hourly=hours,
        daily=days,
    )


def _code(values: list[int | None], index: int) -> int | None:
    return values[index] if index < len(values) else None


def _millimetres(amount: float, imperial: bool) -> float:
    """Open-Meteo gave inches when asked for them; the module counts rain in millimetres."""
    return round(amount * 25.4, 2) if imperial else amount
