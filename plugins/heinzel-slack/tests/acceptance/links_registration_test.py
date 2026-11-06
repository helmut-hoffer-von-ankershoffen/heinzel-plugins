"""Installed source discovery preserves the bot channel and separately captures the CLI link module record."""

import subprocess
import sys

import pytest

pytestmark = pytest.mark.e2e

_SCRIPT = r"""
import json, subprocess
from importlib.metadata import distribution
from heinzel import CurrentUser, NotificationChannel
from heinzel.kernel import ReviewedLinkChannel, boot
metadata = distribution('heinzel-slack')
direct = metadata.read_text('direct_url.json')
assert direct is None or not json.loads(direct).get('dir_info', {}).get('editable'), 'requires installed wheel'
calls = []
def forbidden(*args, **kwargs):
    calls.append(True)
    raise AssertionError('registration may not start a provider process')
subprocess.Popen = forbidden
kernel = boot()
assert not kernel.errors, kernel.errors
current = kernel.resolve(CurrentUser)
with current.local('cli'):
    for name, contract, expected in (
        ('slack', NotificationChannel, 'SlackChannel'),
        ('slack.links', NotificationChannel, 'SlackReviewedLinks'),
        ('slack.links', ReviewedLinkChannel, 'SlackReviewedLinks'),
    ):
        record = kernel.module(name)
        assert record.origin.distribution == 'heinzel-slack'
        assert record.origin.version == metadata.version
        capture = kernel.source_discovery.service_capture(kernel, record, contract)
        service = capture.service(kernel, record, contract)
        assert type(service).__name__ == expected
        if name == 'slack.links':
            assert type(service).__module__ == 'heinzel_slack.links._reviewed_link'
            assert service.name == 'slack-reviewed-links'
            assert service.supported_operations == frozenset({'reviewed-document-link'})
assert not calls
print('installed bot and CLI source registrations passed without provider I/O')
"""


def test_installed_bot_and_cli_links_have_separate_exact_captured_module_records(tmp_path):
    env = {
        "HOME": str(tmp_path),
        "PATH": "/usr/bin:/bin",
        "HZ_CONFIG_HOME": str(tmp_path / "config"),
        "HZ_STATE_DIR": str(tmp_path / "state"),
        "HZ_DATA_DIR": str(tmp_path / "data"),
        "HZ_CACHE_DIR": str(tmp_path / "cache"),
        "HZ_LOG_DIR": str(tmp_path / "logs"),
        "HZ_SYSTEM_CREDENTIAL__BACKEND": "environment",
        "HZ_FEATURES": "captured_writes,connected_frontdoor,connected_channels",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    result = subprocess.run(  # noqa: S603 - fixed isolated interpreter and inline no-I/O fixture
        [sys.executable, "-I", "-c", _SCRIPT], env=env, capture_output=True, text=True, timeout=30, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
