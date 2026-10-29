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


@pytest.mark.timeout(600)
def test_installed_resource_meters(tmp_path):
    environment = dict(os.environ)
    environment["HZ_PLUGINS_ENABLED"] = "true"
    backend = subprocess.Popen(
        [sys.executable, "-m", "heinzel", "ui", "--no-browser", "--port", "0"],
        env=environment,
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    transcript = []
    try:
        deadline = time.monotonic() + 60
        url = ""
        assert backend.stdout is not None
        while time.monotonic() < deadline and backend.poll() is None:
            if select.select([backend.stdout], [], [], 1)[0]:
                line = backend.stdout.readline()
                transcript.append(line)
                found = re.search(r"http://127\.0\.0\.1:\d+/[^\s]*#token=[A-Za-z0-9_-]+", line)
                if found:
                    url = found.group()
                    break
        assert url, "".join(transcript)
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
                url,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    finally:
        backend.terminate()
        try:
            backend.wait(timeout=30)
        except subprocess.TimeoutExpired:
            backend.kill()
            backend.wait(timeout=30)
        backend.stdout.close()
