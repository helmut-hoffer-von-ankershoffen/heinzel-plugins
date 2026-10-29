"""OpenWeather over HTTPS: the One Call API 3.0 for the weather and the geocoding API for place names.

Answers are checked against the models below before anything uses them; fields OpenWeather adds are ignored. The
API key travels as the `appid` query parameter, so no error message here ever includes a URL.
"""

import logging
import re
from http import HTTPStatus
from typing import Annotated, Any, Self, cast

import httpx
from heinzel import HeinzelError
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from heinzel_weather._models import Units

TIMEOUT = 10.0
"""Seconds to wait for OpenWeather."""
COORDINATES = re.compile(r"\s*(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*")
"""A location given as `lat,lon`."""
ONE_CALL = "/data/3.0/onecall"
GEOCODING = "/geo/1.0/direct"
_KEY_IN_URL = re.compile(r"(appid=)[^&\s\"']+")
_METEO_QUERY = re.compile(r"(https://(?:api|geocoding-api)\.open-meteo\.com/[^\s?\"']*)\?[^\s\"']+")


class _RedactKey(logging.Filter):
    """Redact credentials and Open-Meteo location queries from HTTP request logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = _METEO_QUERY.sub(r"\1?[location-redacted]", _KEY_IN_URL.sub(r"\1***", message))
        if redacted != message:
            record.msg, record.args = redacted, None
        return True


logging.getLogger("httpx").addFilter(_RedactKey())


class _Answer(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


class RawCondition(_Answer):
    id: int
    main: str
    description: str
    icon: str


class RawPrecipitation(_Answer):
    one_hour: Annotated[float, Field(alias="1h")] = 0.0


class RawCurrent(_Answer):
    dt: int
    sunrise: int | None = None  # left out in polar day and night
    sunset: int | None = None
    temp: float
    feels_like: float
    humidity: int
    wind_speed: float
    weather: list[RawCondition] = Field(min_length=1)


class RawHour(_Answer):
    dt: int
    temp: float
    wind_speed: float = 0.0
    pop: float = Field(default=0.0, ge=0, le=1)
    weather: list[RawCondition] = Field(min_length=1)
    rain: RawPrecipitation | None = None
    snow: RawPrecipitation | None = None


class RawTemperatures(_Answer):
    min: float
    max: float


class RawDay(_Answer):
    dt: int
    sunrise: int | None = None
    sunset: int | None = None
    temp: RawTemperatures
    wind_speed: float = 0.0
    pop: float = Field(default=0.0, ge=0, le=1)
    weather: list[RawCondition] = Field(min_length=1)


class RawAlert(_Answer):
    sender_name: str = ""
    event: str
    start: int
    end: int
    description: str = ""


class OneCall(_Answer):
    """The One Call API's answer, as far as the module uses it."""

    lat: float
    lon: float
    timezone: str
    timezone_offset: int
    current: RawCurrent
    hourly: list[RawHour] = []
    daily: list[RawDay] = []
    alerts: list[RawAlert] = []


class Place(_Answer):
    """A geocoding match."""

    name: str
    lat: float
    lon: float
    country: str = ""
    state: str = ""


class OpenWeather:
    """A client of OpenWeather's APIs at `base_url`, with the API key; `transport` replaces the network in tests."""

    def __init__(self, base_url: str, api_key: str, transport: httpx.BaseTransport | None = None) -> None:
        """Talk to OpenWeather at `base_url` with `api_key`."""
        self._client = httpx.Client(base_url=base_url, timeout=TIMEOUT, transport=transport)
        self._key = api_key

    def __enter__(self) -> Self:
        """Use the client; its connections close at the end of the block."""
        return self

    def __exit__(self, *_: object) -> None:
        """Close the connections."""
        self._client.close()

    def geocode(self, query: str) -> Place:
        """The first place OpenWeather finds for a name such as "Berlin, DE".

        Raises:
            HeinzelError: If nothing matches, or OpenWeather can't be asked.
        """
        places = self._get(GEOCODING, {"q": query, "limit": "1"})
        if not isinstance(places, list) or not places:
            msg = f"OpenWeather knows no place called {query!r}; try a city and a country code, such as 'Berlin, DE'."
            raise HeinzelError(msg)
        return self._parse(Place, cast("list[object]", places)[0])

    def one_call(self, lat: float, lon: float, units: Units) -> OneCall:
        """The weather now, by the hour and by the day, and the alerts, at a place.

        Raises:
            HeinzelError: If OpenWeather can't be asked or answers something unexpected.
        """
        answer = self._get(
            ONE_CALL, {"lat": f"{lat:.4f}", "lon": f"{lon:.4f}", "units": units.value, "exclude": "minutely"}
        )
        return self._parse(OneCall, answer)

    def _get(self, path: str, params: dict[str, str]) -> Any:  # noqa: ANN401 - JSON, checked by the caller
        failure = response = None
        try:
            response = self._client.get(path, params={**params, "appid": self._key})
        except httpx.HTTPError as error:
            failure = type(error).__name__
        if response is None:
            # Raised outside the except block, so no exception chain holds the request and its URL with the key.
            msg = f"OpenWeather can't be reached: {failure}. Check your connection, or weather.base_url."
            raise HeinzelError(msg)
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            msg = (
                "OpenWeather refused the API key (401). Check it with `hz system credential set weather.api-key`; "
                "the One Call API 3.0 needs its own (free) subscription at openweathermap.org."
            )
            raise HeinzelError(msg)
        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            msg = "OpenWeather says too many requests (429); try again later, or raise weather.refresh_minutes."
            raise HeinzelError(msg)
        if not response.is_success:
            msg = f"OpenWeather answered {response.status_code} for {path}."
            raise HeinzelError(msg)
        try:
            return response.json()
        except ValueError:
            msg = f"OpenWeather answered something that isn't JSON for {path}."
            raise HeinzelError(msg) from None

    @staticmethod
    def _parse[M: BaseModel](model: type[M], data: object) -> M:
        try:
            return model.model_validate(data)
        except ValidationError as error:
            fields = ", ".join(sorted({".".join(map(str, e["loc"])) for e in error.errors()})[:5])
            msg = f"OpenWeather answered in a shape this plugin doesn't know (at {fields})."
            raise HeinzelError(msg) from None


def coordinates(location: str) -> tuple[float, float] | None:
    """`(lat, lon)` for a location given as coordinates, such as "52.52,13.405"; None for a place name."""
    found = COORDINATES.fullmatch(location)
    if not found:
        return None
    lat, lon = float(found[1]), float(found[2])
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):  # noqa: PLR2004 - degrees
        return None
    return lat, lon
