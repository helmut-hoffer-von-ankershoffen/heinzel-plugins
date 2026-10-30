"""Installed core without the captured-source SDK never registers a captured Google service."""

import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def test_old_sdk_retains_ordinary_providers_without_captured_service(tmp_path):
    script = r"""
import subprocess, sys
import heinzel
from heinzel import HeinzelError
from heinzel.kernel import boot, discover, ProviderLet, ServiceLet
discover(plugins=False)
if hasattr(heinzel, 'captured_source_active'):
    delattr(heinzel, 'captured_source_active')
calls = []
def forbidden(*args, **kwargs):
    calls.append(True)
    raise AssertionError('provider process must not start')
subprocess.Popen = forbidden
kernel = boot()
assert 'heinzel_google._connected_calendar' not in sys.modules
providers = {(let.capability, record.qualname) for record, let in kernel.lets(ProviderLet)}
assert {('calendar', 'google'), ('documents', 'google'), ('mail', 'google')} <= providers
for record, let in kernel.lets(ServiceLet):
    if record.qualname == 'google':
        assert let.name != 'GoogleConnectedReadService'
if hasattr(heinzel, 'ConnectedReadService'):
    from heinzel_google._connected_calendar import GoogleConnectedReadService
    try:
        GoogleConnectedReadService(None, None)
    except HeinzelError:
        pass
    else:
        raise AssertionError('an unverified direct service could be constructed')
assert not calls
"""
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}
    result = subprocess.run([sys.executable, "-I", "-c", script], env=env, capture_output=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
