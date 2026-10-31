"""Serve the plugin's own fixed fictional weather locally while capturing documentation."""

import os
import runpy
import sys

from heinzel_weather.fake import serve

server = serve(0)
os.environ.update(
    HZ_WEATHER__PROVIDER="openweather",
    HZ_WEATHER__BASE_URL=f"http://127.0.0.1:{server.server_address[1]}",
    HZ_WEATHER__LOCATIONS='["Berlin, DE"]',
    HZ_WEATHER__UNITS="metric",
    OPENWEATHER_API_KEY="fixture-not-a-real-key",
)
sys.argv = ["hz", *sys.argv[1:]]
try:
    runpy.run_module("heinzel", run_name="__main__")
finally:
    server.shutdown()
    server.server_close()
