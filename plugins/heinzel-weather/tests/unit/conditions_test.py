import pytest
from pydantic import ValidationError

from heinzel_weather import Condition, Units, WeatherSettings
from heinzel_weather._api import coordinates
from heinzel_weather._conditions import condition, icon, ui_icon, units_for_locale

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (211, Condition.THUNDER),
        (300, Condition.DRIZZLE),
        (501, Condition.RAIN),
        (601, Condition.SNOW),
        (741, Condition.FOG),
        (781, Condition.WIND),
        (800, Condition.CLEAR),
        (803, Condition.CLOUDS),
    ],
)
def test_codes_become_one_word(code, expected):
    assert condition(code, temperature=15, wind_speed=2, units=Units.METRIC) is expected


def test_wind_heat_and_cold_come_before_the_sky_but_after_rain():
    assert condition(800, temperature=15, wind_speed=12, units=Units.METRIC) is Condition.WIND
    assert condition(800, temperature=31, wind_speed=2, units=Units.METRIC) is Condition.HEAT
    assert condition(803, temperature=-8, wind_speed=2, units=Units.METRIC) is Condition.COLD
    assert condition(800, temperature=90, wind_speed=2, units=Units.IMPERIAL) is Condition.HEAT
    assert condition(501, temperature=31, wind_speed=20, units=Units.METRIC) is Condition.RAIN


def test_a_clear_night_shows_the_moon():
    assert icon(Condition.CLEAR, night=True) == "☾"
    assert icon(Condition.CLEAR) == "☀"
    assert icon(Condition.RAIN, night=True) == icon(Condition.RAIN)


@pytest.mark.parametrize(
    ("condition_", "expected"),
    [
        (Condition.CLEAR, "sun"),
        (Condition.CLOUDS, "cloud-sun"),
        (Condition.RAIN, "cloud-rain"),
        (Condition.DRIZZLE, "cloud-drizzle"),
        (Condition.THUNDER, "cloud-lightning"),
        (Condition.SNOW, "cloud-snow"),
        (Condition.FOG, "cloud-fog"),
        (Condition.WIND, "wind"),
        (Condition.HEAT, "sun"),
        (Condition.COLD, "cloud-snow"),
    ],
)
def test_conditions_have_shared_ui_icons(condition_, expected):
    assert ui_icon(condition_) == expected


@pytest.mark.parametrize(
    ("name", "units"),
    [("en_US.UTF-8", Units.IMPERIAL), ("de_DE.UTF-8", Units.METRIC), ("en-LR", Units.IMPERIAL), ("C", Units.METRIC)],
)
def test_units_follow_the_locale(name, units):
    assert units_for_locale(name) is units


def test_units_read_the_environment(monkeypatch):
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MEASUREMENT", raising=False)
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    assert units_for_locale() is Units.IMPERIAL


def test_coordinates_or_a_place_name():
    assert coordinates("52.52, 13.405") == (52.52, 13.405)
    assert coordinates("-33.9,18.4") == (-33.9, 18.4)
    assert coordinates("Berlin, DE") is None
    assert coordinates("95,10") is None


@pytest.mark.parametrize("url", ["https://api.example.org/", "http://127.0.0.1:8787", "http://localhost:1"])
def test_base_url_is_https_or_on_this_machine(url):
    assert WeatherSettings(base_url=url).base_url == url.rstrip("/")


@pytest.mark.parametrize("url", ["http://api.example.org", "ftp://127.0.0.1", "https://", "file:///etc"])
def test_base_url_never_sends_the_key_in_the_clear(url):
    with pytest.raises(ValidationError, match="base_url must be https"):
        WeatherSettings(base_url=url)
