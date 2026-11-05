"""Installed wheel discovery validates the real legacy provider and source-bound service registrations."""

import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.e2e

_SCRIPT = r"""
import inspect, json, subprocess, sys
from importlib.metadata import distribution
from pathlib import Path
for site in reversed(sys.argv[1:]):
    sys.path.insert(0, site)
import heinzel
from heinzel import CurrentUser
from heinzel.kernel import boot, discover
discover(plugins=False)
metadata = distribution('heinzel-google')
direct = metadata.read_text('direct_url.json')
assert direct is None or not json.loads(direct).get('dir_info', {}).get('editable'), 'requires installed wheel'
calls = []
def forbidden(*args, **kwargs):
    calls.append(True)
    raise AssertionError('registration must not start a provider process')
subprocess.Popen = forbidden
kernel = boot()
assert 'google' not in kernel.errors, kernel.errors.get('google')
record, registration = kernel.selected_capability_provider('documents')
assert record.origin.distribution == 'heinzel-google'
assert record.origin.version == metadata.version
assert registration.modes == frozenset({'read'})
assert callable(registration.factory.read)
from heinzel_google import GoogleSession
assert isinstance(kernel.resolve_registered_service(GoogleSession, record), GoogleSession)
result = {'legacy_discovery': 'passed', 'source_bound': False}
if hasattr(heinzel, 'captured_source_active'):
    from heinzel.kernel import CapturedWriteService, ConnectedReadService
    import heinzel_google
    assert heinzel_google._captured_source_enabled is True
    assert kernel.source_discovery is not None
    current = kernel.resolve(CurrentUser)
    with current.local('cli'):
        for contract, expected in (
            (ConnectedReadService, 'GoogleConnectedReadService'),
            (CapturedWriteService, 'GoogleDocumentWrites'),
        ):
            binding = kernel.source_discovery.binding(kernel, 'documents', contract)
            service = binding.capture.service(kernel, record, contract)
            assert type(service).__name__ == expected
            if contract is CapturedWriteService:
                assert service.supported_operations == frozenset({"insert-draft"})
            assert binding.capture.approved_runtime == frozenset({'heinzel', 'pydantic'})
        from heinzel.kernel import OperationLet
        operation = next(let for owner, let in kernel.lets(OperationLet)
                         if owner.qualname == 'heinzel' and let.name == 'propose-captured-write')
        assert operation.private and not operation.read_only
        execute = next(let for owner, let in kernel.lets(OperationLet)
                       if owner.qualname == 'heinzel' and let.name == 'execute-captured-write')
        assert execute.private and not execute.read_only
        contract = inspect.signature(operation.func, eval_str=True).parameters['selected'].annotation
        selected = kernel.resolve(contract)
        assert selected.record is record
        selected.check_available()
    result.update(source_bound=True, captured_service='registered', captured_host='available')
assert not calls
print(json.dumps(result, sort_keys=True))
"""


def test_installed_discovery_and_source_bound_registration(tmp_path):
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
    }
    # An owning acceptance environment has the wheel installed. Local proof can additionally provide
    # an isolated wheel installation directory; it must retain real distribution metadata and RECORD.
    site = os.environ.get("HZ_TEST_INSTALLED_GOOGLE_SITE")
    core = os.environ.get("HZ_TEST_INSTALLED_CORE_SITE")
    result = subprocess.run(
        [sys.executable, "-I", "-c", _SCRIPT, *([site] if site else []), *([core] if core else [])],
        env=env,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
