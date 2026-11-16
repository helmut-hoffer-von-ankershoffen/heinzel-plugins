"""Resource's installed meters use generic UI contracts at desktop and phone widths."""

import os
import re
import select
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e
ROOT = Path(__file__).resolve().parents[2]


def backend_environment(directory):
    environment = {key: value for key, value in os.environ.items() if key in {"PATH", "LANG", "LC_ALL", "TMPDIR"}}
    paths = {"HOME": ".", "XDG_CONFIG_HOME": "xdg-config", "HZ_SYSTEM_DAEMON__UNIT_DIR": "units"}
    paths.update(
        {
            f"HZ_{key}": folder
            for key, folder in (
                ("CONFIG_HOME", "config"),
                ("DATA_DIR", "data"),
                ("CACHE_DIR", "cache"),
                ("STATE_DIR", "state"),
                ("LOG_DIR", "log"),
            )
        }
    )
    environment.update({key: str(directory / folder) for key, folder in paths.items()})
    return environment | {"HZ_SYSTEM_CREDENTIAL__BACKEND": "environment", "HZ_PLUGINS_ENABLED": "true"}


def ready_url(backend):
    assert backend.stdout is not None
    deadline = time.monotonic() + 60
    transcript = []
    while backend.poll() is None and time.monotonic() < deadline:
        readable, _, _ = select.select([backend.stdout], [], [], 1)
        if not readable:
            continue
        line = backend.stdout.readline()
        transcript.append(line)
        if found := re.search(r"http://127\.0\.0\.1:\d+/[^\s]*#token=[A-Za-z0-9_-]+", line):
            return found.group()
    pytest.fail("Backend did not announce its URL: " + "".join(transcript))


@pytest.fixture
def meter_url(tmp_path):
    with subprocess.Popen(
        [sys.executable, "-m", "heinzel", "ui", "--no-browser", "--port", "0"],
        env=backend_environment(tmp_path),
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ) as backend:
        try:
            yield ready_url(backend)
        finally:
            backend.terminate()
            try:
                backend.wait(timeout=30)
            except subprocess.TimeoutExpired:
                backend.kill()
                backend.wait(timeout=30)


@pytest.mark.timeout(600)
def test_installed_resource_meters(meter_url):
    result = subprocess.run(
        [
            "uv",
            "run",
            "--no-project",
            "--script",
            str(ROOT / "web/build.py"),
            "exec",
            "node",
            str(ROOT / "tests/browser/meters.mjs"),
            meter_url,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
