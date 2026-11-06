"""Local native process fixtures prove bounded output and process-group quiescence without Slack access."""

import os
import sys
from pathlib import Path

import pytest
from heinzel import HeinzelError

from heinzel_slack.links._cli_process import run

pytestmark = pytest.mark.integration


def test_timeout_reaps_a_native_child_before_returning(tmp_path):
    pidfile = tmp_path / "pid"
    program = f"import os,time,pathlib; pathlib.Path({str(pidfile)!r}).write_text(str(os.getpid())); time.sleep(30)"
    with pytest.raises(HeinzelError, match="bounded request"):
        run(Path(sys.executable), ["-c", program], {"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"}, 0.2)
    pid = int(pidfile.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_oversized_output_and_unstructured_failure_are_bounded_and_never_echoed(tmp_path):
    environment = {"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"}
    with pytest.raises(HeinzelError, match="bounded request"):
        run(Path(sys.executable), ["-c", "print('x' * (2 * 1024 * 1024))"], environment, 2)
    with pytest.raises(HeinzelError, match="bounded request") as failure:
        run(Path(sys.executable), ["-c", "raise RuntimeError('synthetic-secret')"], environment, 2)
    assert "synthetic-secret" not in str(failure.value)
