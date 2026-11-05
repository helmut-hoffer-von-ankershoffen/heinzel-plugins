"""Installed candidate wheels with default boot and only offline Google/CLI fixtures."""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("kind", ["document", "spreadsheet"])
def test_declared_plugin_default_boot_private_review_read_and_revoke(tmp_path, kind):
    script = r"""
import os, sys
from pathlib import Path
from heinzel.kernel import boot
root = Path(os.environ["HZ_TEST_ROOT"])
# Boot before importing any test fixtures or Google package. This must use installed wheel metadata.
first = boot()
import heinzel_google
assert heinzel_google._captured_source_enabled is True
assert first.module('google').origin.distribution == 'heinzel-google'
sys.path.insert(0, os.environ["HZ_TEST_PLUGIN_TESTS"])
from pytest import MonkeyPatch
from tests.support.connected_artifact_support import test_artifact_read_requires_its_own_review_and_revocation
def guarded_boot():
    return boot()
with MonkeyPatch.context() as patches:
    test_artifact_read_requires_its_own_review_and_revocation(
        guarded_boot, root / "case", patches, os.environ["HZ_TEST_KIND"]
    )
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
        "HZ_TEST_ROOT": str(tmp_path),
        "HZ_TEST_PLUGIN_TESTS": str(Path(__file__).resolve().parents[2]),
        "HZ_TEST_KIND": kind,
    }
    result = subprocess.run([sys.executable, "-I", "-c", script], env=env, capture_output=True, timeout=45, check=False)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
