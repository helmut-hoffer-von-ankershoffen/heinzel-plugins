"""The module and its credential, apart from `__init__` so the service can name the credential without a cycle."""

from heinzel import Module

module = Module(
    "weather", "Weather where you are, from Open-Meteo or OpenWeather: now, the next hours and days, and what changes."
)

API_KEY = module.credential(
    "api-key",
    purpose="OpenWeather API key (only with provider = openweather): One Call API 3.0, free tier, "
    "from home.openweathermap.org/api_keys",
)
"""Read from the keychain, `HZ_CREDENTIAL_WEATHER_API_KEY`, or else `OPENWEATHER_API_KEY`."""
FALLBACK_VARIABLE = "OPENWEATHER_API_KEY"
"""The variable OpenWeather's own tools read; used when the credential isn't stored."""
