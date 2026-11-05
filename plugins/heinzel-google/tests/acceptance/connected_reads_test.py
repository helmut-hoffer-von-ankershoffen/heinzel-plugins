"""Installed-wheel connected reads, with the host booted before importing the plugin."""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("kind", ["document", "spreadsheet", "mail", "schedule"])
def test_installed_connected_reads_and_revocation(tmp_path, kind):
    script = r"""
import os, sys
from pathlib import Path
from heinzel.kernel import boot
boot()  # Capture the installed provider before importing its source or fixture helpers.
sys.path.insert(0, os.environ['HZ_TEST_PLUGIN_TESTS'])
from pytest import MonkeyPatch
from tests.support.connected_artifact_support import test_artifact_read_requires_its_own_review_and_revocation
from tests.support.connected_mail_support import test_mail_read_requires_its_own_review_and_revocation
from tests.support.connected_schedule_support import (
    test_owner_reviewed_rolling_calendar_schedule_survives_daemon_restart,
)
root = Path(os.environ['HZ_TEST_ROOT'])
with MonkeyPatch.context() as patches:
    kind = os.environ['HZ_TEST_KIND']
    if kind in ('document', 'spreadsheet'):
        test_artifact_read_requires_its_own_review_and_revocation(boot, root, patches, kind)
    elif kind == 'mail':
        test_mail_read_requires_its_own_review_and_revocation(boot, root, patches)
    else:
        test_owner_reviewed_rolling_calendar_schedule_survives_daemon_restart(boot, root, patches)
"""
    case = tmp_path / "case"
    case.mkdir()
    for name in ("home", "config", "state", "data", "cache", "logs"):
        (tmp_path / name).mkdir()
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path / "home"),
        "HZ_CONFIG_HOME": str(tmp_path / "config"),
        "HZ_STATE_DIR": str(tmp_path / "state"),
        "HZ_DATA_DIR": str(tmp_path / "data"),
        "HZ_CACHE_DIR": str(tmp_path / "cache"),
        "HZ_LOG_DIR": str(tmp_path / "logs"),
        "HZ_TEST_PLUGIN_TESTS": str(Path(__file__).resolve().parents[2]),
        "HZ_TEST_ROOT": str(case),
        "HZ_TEST_KIND": kind,
    }
    result = subprocess.run([sys.executable, "-I", "-c", script], env=env, capture_output=True, timeout=90, check=False)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
