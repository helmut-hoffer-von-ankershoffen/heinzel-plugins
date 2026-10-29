import httpx
import pytest
from heinzel import HeinzelError

from heinzel_weather import Units, fake
from heinzel_weather._api import OpenWeather

pytestmark = pytest.mark.unit

KEY = "secret-key-1234"


def client(handler) -> OpenWeather:
    return OpenWeather("https://api.example.org", KEY, httpx.MockTransport(handler))


def test_one_call_sends_the_key_units_and_coordinates():
    requests: list[httpx.Request] = []
    with OpenWeather("https://api.example.org", KEY, fake.transport(record=requests)) as weather:
        answer = weather.one_call(52.52, 13.405, Units.IMPERIAL)
    assert answer.current.temp == 70.7  # 21.5 °C
    assert requests[0].url.params["appid"] == KEY
    assert requests[0].url.params["units"] == "imperial"
    assert requests[0].url.params["lat"] == "52.5200"


def test_geocoding_finds_a_place_or_says_so():
    with OpenWeather("https://api.example.org", KEY, fake.transport()) as weather:
        assert weather.geocode("Lisbon, PT").name == "Lisbon"
        with pytest.raises(HeinzelError, match="no place called 'Atlantis'"):
            weather.geocode("Atlantis")


@pytest.mark.parametrize(
    ("status", "message"),
    [(401, "refused the API key"), (429, "too many requests"), (500, "answered 500")],
)
def test_errors_say_what_to_do_and_never_show_the_key(status, message):
    with client(lambda _: httpx.Response(status, json={})) as weather, pytest.raises(HeinzelError) as raised:
        weather.one_call(1, 2, Units.METRIC)
    assert message in str(raised.value)
    assert KEY not in str(raised.value)


def test_a_network_error_never_shows_the_url():
    def fail(request: httpx.Request) -> httpx.Response:
        msg = f"cannot connect to {request.url}"
        raise httpx.ConnectError(msg, request=request)

    with client(fail) as weather, pytest.raises(HeinzelError, match="can't be reached: ConnectError") as raised:
        weather.one_call(1, 2, Units.METRIC)
    assert KEY not in str(raised.value)


def test_an_answer_that_isnt_json_or_has_another_shape_is_refused():
    with client(lambda _: httpx.Response(200, text="<html>")) as weather, pytest.raises(HeinzelError, match="JSON"):
        weather.one_call(1, 2, Units.METRIC)
    with (
        client(lambda _: httpx.Response(200, json={"lat": 1})) as weather,
        pytest.raises(HeinzelError, match="shape this plugin doesn't know"),
    ):
        weather.one_call(1, 2, Units.METRIC)


def test_the_fake_refuses_requests_without_a_key_and_unknown_paths():
    assert fake.answer("/data/3.0/onecall", {})[0] == 401
    assert fake.answer("/elsewhere", {"appid": "x"})[0] == 404
    assert fake.one_call("standard")["current"]["temp"] == 294.65
