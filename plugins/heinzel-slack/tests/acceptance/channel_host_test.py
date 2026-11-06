"""Real installed source capture and host confirmation use only fictional external Slack/document transports."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e
ROOT = Path(__file__).resolve().parents[2]


def test_installed_channel_and_host_require_exact_human_consent_and_owner_reply(tmp_path):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("HZ_")}
    environment.pop("PYTHONPATH", None)
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        environment.pop(key, None)
    environment.update(PYTHONDONTWRITEBYTECODE="1", SLACK_PROOF="0")
    core = environment["PLUGIN_TEST_CORE"]
    wheel = environment["PLUGIN_TEST_WHEEL"]
    fixture = ROOT / "tests/fixtures/captured_writer"
    built = tmp_path / "fixture-wheel"
    interpreter = tmp_path / "environment/bin/python"
    uv = shutil.which("uv")
    assert uv is not None
    commands = [
        [
            uv,
            "build",
            "--offline",
            "--wheel",
            "--project",
            str(fixture),
            "--build-constraints",
            str(ROOT / "requirements.lock"),
            "--out-dir",
            str(built),
        ],
        [uv, "venv", "--python", sys.executable, str(interpreter.parent.parent)],
        [
            uv,
            "pip",
            "sync",
            "--offline",
            "--python",
            str(interpreter),
            "--require-hashes",
            "--no-build",
            str(ROOT / "requirements.lock"),
        ],
    ]
    for command in commands:
        subprocess.run(  # noqa: S603 - fixed executable and fixture paths, never a shell
            command, env=environment, check=True, capture_output=True, text=True, timeout=30
        )
    fixture_wheel = next(built.glob("heinzel_slack_capture_fixture-*.whl"))
    subprocess.run(  # noqa: S603 - the selected local test artifacts are passed as argv operands
        [
            uv,
            "pip",
            "install",
            "--offline",
            "--python",
            str(interpreter),
            "--no-deps",
            "--no-build",
            core,
            wheel,
            str(fixture_wheel),
        ],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    result = subprocess.run(  # noqa: S603 - fresh fixture interpreter and checked-in probe, never a shell
        [str(interpreter), "-I", str(ROOT / "tests/fixtures/channel_host_probe.py"), str(tmp_path / "private")],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    proof = json.loads(result.stdout)
    assert proof["captured_packages"] == ["heinzel_slack", "fixture_captured_writer"]
    assert proof["notice_posts"] == proof["approval_posts"] == proof["captured_writes"] == 1
    assert proof["wrong_scope_refused"]
    assert proof["changed_account_refused"]
    assert proof["nonowner_click_refused"]
    assert proof["unauthenticated_confirmation_refused"]
    assert proof["repeat_confirmation_and_consumption_refused"]
    assert proof["vendor_source_tamper_refused"]
