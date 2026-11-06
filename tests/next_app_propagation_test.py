"""Only exact-version metadata 404 propagation receives a finite wait."""

import io
import json
import runpy
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

import pytest

pytestmark = pytest.mark.unit
URL = "https://pypi.org/pypi/heinzel/1.2.3/json"


@pytest.fixture
def lookup(monkeypatch):
    package = runpy.run_path(str(Path(__file__).parents[1] / "scripts/next_app.py"))["package"]
    download, sleep = Mock(), Mock()
    monkeypatch.setitem(package.__globals__, "download", download)
    monkeypatch.setattr(package.__globals__["time"], "sleep", sleep)
    return package, download, sleep


def missing(url=URL, code=404):
    error = HTTPError(url, code, "fixture error", {}, io.BytesIO())
    error.close()  # Final raised fixture errors are retained by pytest; release their temporary wrapper.
    return error


def test_exact_version_propagates_then_returns_unchanged_metadata(lookup, capsys):
    package, download, sleep = lookup
    metadata = {"info": {"version": "1.2.3"}, "urls": []}
    errors = [missing(), missing()]
    for error in errors:
        error.close = Mock()
    download.side_effect = [*errors, json.dumps(metadata).encode()]
    assert package("1.2.3") == metadata
    for error in errors:
        error.close.assert_called_once()
    assert download.call_args_list == [((URL,),)] * 3
    assert sleep.call_args_list == [((10,),)] * 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "attempt 1/4" in output.err and "attempt 2/4" in output.err
    assert URL not in output.err and "fixture error" not in output.err


def test_fourth_404_stops_with_original_error_and_no_final_sleep(lookup):
    package, download, sleep = lookup
    errors = [missing() for _ in range(4)]
    download.side_effect = errors
    with pytest.raises(HTTPError) as failure:
        package("1.2.3")
    assert failure.value is errors[-1]
    assert download.call_count == 4
    assert sleep.call_args_list == [((10,),)] * 3


@pytest.mark.parametrize("version", ["", "1.2.3.dev1", "1.2.3rc1", "01.2.3", "1.2.3/other"])
def test_latest_or_noncanonical_version_never_retries(lookup, version):
    package, download, sleep = lookup
    error = missing(f"https://pypi.org/pypi/heinzel/{version + '/' if version else ''}json")
    download.side_effect = error
    with pytest.raises(HTTPError) as failure:
        package(version)
    assert failure.value is error
    download.assert_called_once()
    sleep.assert_not_called()


@pytest.mark.parametrize("code", [400, 401, 403, 408, 429, 500, 502, 503])
def test_other_status_never_retries(lookup, code):
    package, download, sleep = lookup
    error = missing(code=code)
    download.side_effect = error
    with pytest.raises(HTTPError) as failure:
        package("1.2.3")
    assert failure.value is error
    download.assert_called_once_with(URL)
    sleep.assert_not_called()


@pytest.mark.parametrize(
    "error", [URLError("private network failure"), TimeoutError("timeout"), missing("https://other.invalid/json")]
)
def test_network_or_redirected_404_never_retries(lookup, error):
    package, download, sleep = lookup
    download.side_effect = error
    with pytest.raises(type(error)) as failure:
        package("1.2.3")
    assert failure.value is error
    download.assert_called_once_with(URL)
    sleep.assert_not_called()


def test_invalid_json_after_404_is_not_retried(lookup):
    package, download, sleep = lookup
    download.side_effect = [missing(), b"not json"]
    with pytest.raises(json.JSONDecodeError):
        package("1.2.3")
    assert download.call_count == 2
    sleep.assert_called_once_with(10)


def test_successful_yanked_metadata_is_not_waited_away(lookup):
    package, download, sleep = lookup
    value = {"info": {"version": "1.2.3"}, "urls": [{"yanked": True}]}
    download.return_value = json.dumps(value).encode()
    assert package("1.2.3") == value
    download.assert_called_once_with(URL)
    sleep.assert_not_called()


@pytest.mark.parametrize("problem", ["wrong-version", "yanked", "wrong-hash"])
def test_propagation_never_relaxes_original_selection_checks(lookup, monkeypatch, problem):
    package, download, sleep = lookup
    select = package.__globals__["select"]
    metadata = {
        "info": {"version": "1.2.4" if problem == "wrong-version" else "1.2.3"},
        "urls": [
            {
                "filename": "heinzel-1.2.3-py3-none-any.whl",
                "yanked": problem == "yanked",
                "digests": {"sha256": "a" * 64},
            }
        ],
    }
    download.side_effect = [missing(), json.dumps(metadata).encode()]
    monkeypatch.setitem(package.__globals__, "find_release", lambda *_: None)
    monkeypatch.setitem(
        package.__globals__,
        "api",
        lambda path, **_: (
            None
            if "/git/ref/" in path
            else {
                "assets": [
                    {
                        "name": "heinzel-1.2.3-py3-none-any.whl",
                        "digest": "sha256:" + ("b" if problem == "wrong-hash" else "a") * 64,
                    }
                ]
            }
        ),
    )
    wheel = "https://github.com/helmut-hoffer-von-ankershoffen/heinzel/releases/download/v1.2.3/heinzel-1.2.3-py3-none-any.whl"
    if problem == "yanked":
        assert select("example/plugins", version="1.2.3", core_wheel=wheel) is None
    else:
        with pytest.raises(ValueError, match="does not match"):
            select("example/plugins", version="1.2.3", core_wheel=wheel)
    assert download.call_count == 2
    sleep.assert_called_once_with(10)
