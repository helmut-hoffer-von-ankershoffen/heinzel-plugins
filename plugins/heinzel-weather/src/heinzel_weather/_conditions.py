"""From OpenWeather's condition codes to one word, a symbol, and the units of your locale. Pure functions."""

import locale
import os

from heinzel import Icon

from heinzel_weather._models import Accessory, Condition, Now, Units

IMPERIAL_REGIONS = frozenset({"US", "LR", "MM"})
"""Where Fahrenheit and miles per hour are what people read: the United States, Liberia, Myanmar."""
ICONS = {
    Condition.CLEAR: "☀",
    Condition.CLOUDS: "☁",
    Condition.RAIN: "🌧",
    Condition.DRIZZLE: "🌦",
    Condition.THUNDER: "⛈",
    Condition.SNOW: "❄",
    Condition.FOG: "🌫",
    Condition.WIND: "💨",
    Condition.HEAT: "🔥",
    Condition.COLD: "🥶",
}
NIGHT_ICONS = {Condition.CLEAR: "☾"}
UI_ICONS: dict[Condition, Icon] = {
    Condition.CLEAR: "sun",
    Condition.CLOUDS: "cloud-sun",
    Condition.RAIN: "cloud-rain",
    Condition.DRIZZLE: "cloud-drizzle",
    Condition.THUNDER: "cloud-lightning",
    Condition.SNOW: "cloud-snow",
    Condition.FOG: "cloud-fog",
    Condition.WIND: "wind",
    Condition.HEAT: "sun",
    Condition.COLD: "cloud-snow",
}
WET = frozenset({Condition.RAIN, Condition.DRIZZLE, Condition.THUNDER, Condition.SNOW})
"""Conditions that bring rain or snow."""
WINDY = {Units.METRIC: 10.8, Units.IMPERIAL: 24.2}
"""Beaufort 6, a strong breeze: from here on the wind is what you notice."""
HOT = {Units.METRIC: 30.0, Units.IMPERIAL: 86.0}
FREEZING = {Units.METRIC: -5.0, Units.IMPERIAL: 23.0}
_GROUPS = {2: Condition.THUNDER, 3: Condition.DRIZZLE, 5: Condition.RAIN, 6: Condition.SNOW, 7: Condition.FOG}
_SQUALLS = frozenset({771, 781})
"""Squalls and tornadoes: OpenWeather files them under atmosphere (7xx), but they are wind."""
_CLEAR = 800


def condition(code: int, *, temperature: float, wind_speed: float, units: Units) -> Condition:
    """One word for OpenWeather's condition `code` (openweathermap.org/weather-conditions), the heat and the wind.

    Precipitation, fog and storms come first; wind, then heat or cold, then the sky.
    """
    if code in _SQUALLS:
        return Condition.WIND
    if (group := _GROUPS.get(code // 100)) is not None:
        return group
    if wind_speed >= WINDY[units]:
        return Condition.WIND
    if temperature >= HOT[units]:
        return Condition.HEAT
    if temperature <= FREEZING[units]:
        return Condition.COLD
    return Condition.CLEAR if code == _CLEAR else Condition.CLOUDS


def icon(value: Condition, *, night: bool = False) -> str:
    """One symbol for a condition; a moon for a clear night."""
    return (NIGHT_ICONS if night else ICONS).get(value, ICONS[value])


def ui_icon(value: Condition) -> Icon:
    """A shared app icon name for this condition."""
    return UI_ICONS[value]


def units_for_locale(name: str | None = None) -> Units:
    """Imperial where the locale's region is the US, Liberia or Myanmar; metric everywhere else.

    `name` is a locale such as `en_US.UTF-8`; by default the environment's (`LC_ALL`, `LC_MEASUREMENT`, `LANG`),
    then Python's.
    """
    if name is None:
        name = next(
            (value for key in ("LC_ALL", "LC_MEASUREMENT", "LANG") if (value := os.environ.get(key))), None
        ) or (locale.getlocale()[0] or "")
    region = name.split(".")[0].replace("-", "_").partition("_")[2].upper()
    return Units.IMPERIAL if region in IMPERIAL_REGIONS else Units.METRIC


COLD = {Units.METRIC: 5.0, Units.IMPERIAL: 41.0}
"""From here down a scarf is welcome."""


def accessories(now: Now, *, units: Units, rain: float) -> list[Accessory]:
    """What the Heinzelmännchen wears for the weather, in the order the avatar layers it.

    An umbrella in or near rain (`rain` is the chance from which today needs one), sunglasses in clear daylight, a
    scarf in the cold.
    """
    worn: list[Accessory] = []
    if now.condition in WET or now.rain_chance >= rain:
        worn.append("umbrella")
    daylight = now.sunrise is None or now.sunset is None or now.sunrise <= now.observed_at <= now.sunset
    if now.condition in {Condition.CLEAR, Condition.HEAT} and daylight and "umbrella" not in worn:
        worn.append("sunglasses")
    if now.condition is Condition.COLD or now.temperature <= COLD[units]:
        worn.append("scarf")
    return worn
