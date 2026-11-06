"""Relocated upstream annotations remain useful to strict first-party SDK consumers."""

import json
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration

_CONSUMER = """
from heinzel_slack._vendor.slack_sdk import WebClient
from heinzel_slack._vendor.slack_sdk.socket_mode import SocketModeClient

def calls() -> None:
    WebClient(token=BOT)
    SocketModeClient(app_token=APP)
"""


@pytest.mark.parametrize("checker", ["mypy", "pyright"])
@pytest.mark.parametrize("valid", [True, False])
def test_relocated_sdk_types_accept_valid_calls_and_reject_wrong_arguments(tmp_path, checker, valid):
    source = _CONSUMER.replace("BOT", '"synthetic fixture"' if valid else "42").replace(
        "APP", '"synthetic fixture"' if valid else "42"
    )
    consumer = tmp_path / "consumer.py"
    consumer.write_text(source)
    if checker == "mypy":
        # Silent imported implementation diagnostics still retain SDK symbols and argument types.
        command = [
            sys.executable,
            "-m",
            "mypy",
            "--strict",
            "--follow-imports=silent",
            "--no-incremental",
            "--cache-dir",
            str(tmp_path / "mypy-cache"),
            "--python-executable",
            sys.executable,
            str(consumer),
        ]
    else:
        config = tmp_path / "pyrightconfig.json"
        config.write_text(json.dumps({"typeCheckingMode": "strict", "pythonVersion": "3.12"}))
        command = [
            sys.executable,
            "-m",
            "pyright",
            "--pythonpath",
            sys.executable,
            "--project",
            str(config),
            "--outputjson",
            str(consumer),
        ]
    result = subprocess.run(  # noqa: S603 - fixed checkers with a generated non-executable consumer fixture
        command, capture_output=True, text=True, check=False, timeout=30
    )
    if valid:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0
        if checker == "mypy":
            assert 'Argument "token"' in result.stdout
            assert 'Argument "app_token"' in result.stdout
            assert "[arg-type]" in result.stdout
        else:
            diagnostics = json.loads(result.stdout)["generalDiagnostics"]
            errors = [item for item in diagnostics if item["severity"] == "error"]
            assert len(errors) == 2, errors
            assert all(item["rule"] == "reportArgumentType" for item in errors)
