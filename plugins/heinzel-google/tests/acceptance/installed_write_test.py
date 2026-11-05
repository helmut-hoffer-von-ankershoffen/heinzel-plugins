"""Installed Google and candidate core wheels exercise real trusted confirmation with offline provider transport."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

_SCRIPT = r"""
import json, os, sys
from importlib.metadata import distribution
from pathlib import Path
for site in reversed(sys.argv[1:]):
    sys.path.insert(0, site)
root = Path(os.environ['HZ_TEST_ROOT'])
gws = root / 'gws'
gws.write_bytes(b'\xcf\xfa\xed\xfe' + b'offline-fixture')
gws.chmod(0o700)
os.environ['HZ_GOOGLE__GWS_PATH'] = str(gws)
from heinzel.kernel import boot, CapturedWriteService
assert hasattr(CapturedWriteService, 'supported_operations'), 'requires declaration-aware candidate core'
metadata = distribution('heinzel-google')
direct = metadata.read_text('direct_url.json')
assert direct is None or not json.loads(direct).get('dir_info', {}).get('editable'), 'requires installed wheel'
kernel = boot()
assert 'google' not in kernel.errors, kernel.errors.get('google')
import heinzel_google
assert heinzel_google._captured_source_enabled is True
sys.path.insert(0, os.environ['HZ_TEST_PLUGIN_TESTS'])
from pytest import MonkeyPatch
from tests.support.installed_write_fixture import exercise_installed_write
with MonkeyPatch.context() as patches:
    exercise_installed_write(kernel, patches)
print('legacy-read-only; source-bound; zero unapproved; one conditional approved; zero replay')
"""


def test_installed_google_requires_exact_trusted_approval_and_never_replays(tmp_path):
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path),
        "HZ_CONFIG_HOME": str(tmp_path / "config"),
        "HZ_STATE_DIR": str(tmp_path / "state"),
        "HZ_DATA_DIR": str(tmp_path / "data"),
        "HZ_CACHE_DIR": str(tmp_path / "cache"),
        "HZ_LOG_DIR": str(tmp_path / "logs"),
        "HZ_CAPABILITIES__DOCUMENTS": "google",
        "HZ_FEATURES": "captured_writes",
        "HZ_TEST_ROOT": str(tmp_path),
        "HZ_TEST_PLUGIN_TESTS": str(Path(__file__).resolve().parents[2]),
    }
    site = os.environ.get("HZ_TEST_INSTALLED_GOOGLE_SITE")
    core = os.environ.get("HZ_TEST_INSTALLED_CORE_SITE")
    result = subprocess.run(
        [sys.executable, "-I", "-c", _SCRIPT, *([site] if site else []), *([core] if core else [])],
        env=env,
        capture_output=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace") + result.stdout.decode(errors="replace")
