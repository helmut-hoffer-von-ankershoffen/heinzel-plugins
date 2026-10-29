"""A fake OpenWeather with fixed weather, for tests, end-to-end tests and the docs' recordings. Never the network.

The same canned answers three ways: `answer()` for a request, `transport()` for an `httpx.MockTransport`, and
`serve()` for a local HTTP server that `weather.base_url` can point at:

    python -m heinzel_weather.fake --port 8787
    HZ_WEATHER__BASE_URL=http://127.0.0.1:8787 OPENWEATHER_API_KEY=fake hz weather

The weather, relative to the hour it is asked in (`anchor`): 21.5 °C and clear in "Berlin, DE" now, rain from the
next hour (80%), 12 °C six hours on, a thunderstorm warning in three hours; eight days ahead. Imperial units get the
same weather in °F and mph. Any place name is found except "Atlantis"; requests without `appid` get a 401.
"""

import argparse
import json
import threading
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import httpx

TEMPERATURE = 21.5
"""The temperature now, °C."""
PLACE = {"name": "Berlin", "lat": 52.52, "lon": 13.405, "country": "DE", "state": "Berlin"}
UNKNOWN = "atlantis"
HOST = "127.0.0.1"
ZONE = "Europe/Berlin"
_CLEAR = {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
_RAIN = {"id": 501, "main": "Rain", "description": "moderate rain", "icon": "10d"}
_CLOUDS = {"id": 803, "main": "Clouds", "description": "broken clouds", "icon": "04d"}
_DAY_TEMPERATURES = [(24.0, 11.5), (19.0, 10.0), (17.5, 9.0), (21.0, 12.0), (23.5, 13.0), (22.0, 12.5)]
_DAY_SKIES = [_RAIN, _CLOUDS, _RAIN, _CLEAR, _CLEAR, _CLOUDS]


def anchor(now: datetime | None = None) -> datetime:
    """The hour the fake weather is relative to: the start of the current hour, UTC."""
    return (now or datetime.now(UTC)).astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def one_call(units: str = "metric", now: datetime | None = None) -> dict[str, Any]:
    """The One Call API 3.0 answer for `units` (metric, imperial, standard)."""
    start = anchor(now)

    def t(celsius: float) -> float:
        if units == "imperial":
            return round(celsius * 9 / 5 + 32, 1)
        if units == "standard":
            return round(celsius + 273.15, 2)
        return celsius

    def speed(metres: float) -> float:
        return round(metres * 2.237, 1) if units == "imperial" else metres

    def ts(moment: datetime) -> int:
        return int(moment.timestamp())

    zone = ZoneInfo(ZONE)
    midnight = start.astimezone(zone).replace(hour=0)  # Berlin's, where the canned days begin
    sunrise, sunset = midnight + timedelta(hours=4, minutes=50), midnight + timedelta(hours=18, minutes=40)
    hourly: list[dict[str, object]] = []
    for hour in range(48):
        # The canned story: clear now, rain for four hours, cooling to 12 °C by six hours on, clear from eleven.
        cooling = max(12.0, TEMPERATURE - 1.6 * hour) if hour <= 6 else 12.0 + hour % 5  # noqa: PLR2004
        celsius = TEMPERATURE if hour == 0 else cooling
        sky = _RAIN if 1 <= hour <= 4 else _CLOUDS if hour <= 10 else _CLEAR  # noqa: PLR2004
        hourly.append(
            {
                "dt": ts(start + timedelta(hours=hour)),
                "temp": t(celsius),
                "feels_like": t(celsius - 1),
                "humidity": 80 if sky is _RAIN else 55,
                "clouds": 90 if sky is not _CLEAR else 5,
                "wind_speed": speed(4.2),
                "pop": 0.8 if sky is _RAIN else 0.1,
                "weather": [sky],
                **({"rain": {"1h": 1.6}} if sky is _RAIN else {}),
            }
        )
    daily = [
        {
            "dt": ts(midnight + timedelta(days=day, hours=12)),
            "sunrise": ts(sunrise + timedelta(days=day)),
            "sunset": ts(sunset + timedelta(days=day)),
            "summary": "A fake day.",
            "temp": {"min": t(low), "max": t(high), "day": t(high - 2), "night": t(low + 1)},
            "humidity": 60,
            "wind_speed": speed(5.0),
            "pop": 0.8 if sky is _RAIN else 0.1,
            "weather": [sky],
        }
        for day, ((high, low), sky) in enumerate(
            zip(_DAY_TEMPERATURES + _DAY_TEMPERATURES[:2], _DAY_SKIES * 2, strict=False)
        )
    ]
    return {
        "lat": PLACE["lat"],
        "lon": PLACE["lon"],
        "timezone": ZONE,
        "timezone_offset": int((start.astimezone(zone).utcoffset() or timedelta()).total_seconds()),
        "current": {
            "dt": ts(start + timedelta(minutes=5)),
            "sunrise": ts(sunrise),
            "sunset": ts(sunset),
            "temp": t(TEMPERATURE),
            "feels_like": t(TEMPERATURE - 0.5),
            "pressure": 1015,
            "humidity": 48,
            "uvi": 3.1,
            "clouds": 5,
            "visibility": 10000,
            "wind_speed": speed(4.2),
            "wind_deg": 240,
            "weather": [_CLEAR],
        },
        "hourly": hourly,
        "daily": daily,
        "alerts": [
            {
                "sender_name": "Example Weather Service",
                "event": "Thunderstorm warning",
                "start": ts(start + timedelta(hours=3)),
                "end": ts(start + timedelta(hours=6)),
                "description": "Thunderstorms with heavy rain and gusts up to 70 km/h.",
                "tags": ["Thunderstorm"],
            }
        ],
    }


def answer(path: str, query: Mapping[str, str], now: datetime | None = None) -> tuple[int, object]:
    """The status and JSON body the fake answers for a GET of `path` with `query`."""
    if not query.get("appid"):
        return 401, {"cod": 401, "message": "Invalid API key."}
    if path == "/geo/1.0/direct":
        name = query.get("q", "")
        if UNKNOWN in name.lower():
            return 200, []
        return 200, [{**PLACE, "name": name.split(",")[0].strip() or PLACE["name"]}]
    if path == "/data/3.0/onecall":
        return 200, one_call(query.get("units", "standard"), now)
    return 404, {"cod": 404, "message": "Not found."}


def transport(now: datetime | None = None, record: list[httpx.Request] | None = None) -> httpx.MockTransport:
    """An `httpx.MockTransport` answering like the fake server; `record` collects the requests it got."""

    def handle(request: httpx.Request) -> httpx.Response:
        if record is not None:
            record.append(request)
        status, body = answer(request.url.path, dict(request.url.params), now)
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handle)


def serve(port: int = 0, now: Callable[[], datetime | None] = lambda: None) -> ThreadingHTTPServer:
    """Start the fake on 127.0.0.1:`port` (0 picks a free one) in a background thread; `.shutdown()` stops it."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            url = urlsplit(self.path)
            query = {key: values[-1] for key, values in parse_qs(url.query).items()}
            status, body = answer(url.path, query, now())
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - the base class's name
            """Log nothing: the query holds the API key."""

    server = ThreadingHTTPServer((HOST, port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main() -> None:
    """Run the fake in the foreground: `python -m heinzel_weather.fake --port 8787`."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--port", type=int, default=8787, help="port on 127.0.0.1 (0: a free one)")
    port = parser.parse_args().port
    server = serve(port)
    print(f"http://{HOST}:{server.server_address[1]}", flush=True)  # noqa: T201 - the URL to point base_url at
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
