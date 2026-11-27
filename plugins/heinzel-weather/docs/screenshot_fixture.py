"""Serve the plugin's own fixed fictional weather locally while capturing documentation."""

import os
import sys
from datetime import datetime

from heinzel import Config, Kernel, Settings
from heinzel.heads.cli import build
from heinzel.kernel import discover

from heinzel_weather import WeatherService
from heinzel_weather.fake import serve

CAPTURE_TIME = datetime.fromisoformat("2026-11-01T12:00:00+01:00")


def main():
    server = serve(0, now=lambda: CAPTURE_TIME)
    os.environ.update(
        HZ_WEATHER__PROVIDER="openweather",
        HZ_WEATHER__BASE_URL=f"http://127.0.0.1:{server.server_address[1]}",
        HZ_WEATHER__LOCATIONS='["Berlin, DE"]',
        HZ_WEATHER__UNITS="metric",
        OPENWEATHER_API_KEY="fixture-not-a-real-key",
    )
    try:
        config = Config.load()
        records, errors = discover()
        kernel = Kernel(config.settings(Settings, "hz"), records, errors, config)
        # Use the owning service's public test clock, not any process-wide or Core clock.
        kernel.resolve(WeatherService).clock = lambda: CAPTURE_TIME
        sys.argv = ["hz", *sys.argv[1:]]
        build(kernel)()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
