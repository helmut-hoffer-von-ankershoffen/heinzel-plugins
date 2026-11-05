"""Isolated installed wheels: captured helper bytes survive an on-disk replacement without network access."""

import subprocess
import sys

import pytest

pytestmark = pytest.mark.e2e


def test_captured_helper_executes_original_bytes_without_provider_access(tmp_path):
    script = r"""
import json, os, subprocess, sys
from importlib.metadata import distribution
from pathlib import Path
from heinzel import HeinzelError
from heinzel.kernel import boot
entry = next(e for e in distribution("heinzel-google").entry_points if e.group == "heinzel.modules")
root = Path(entry.dist.locate_file(entry.module))
kernel = boot()
import heinzel_google
assert heinzel_google._captured_source_enabled is True
assert kernel.module("google").origin.distribution == "heinzel-google"
from heinzel_google import _existing_lease as lease
helper = root / "_token_exchange.py"
original = helper.read_bytes()
marker = Path(os.environ["HZ_TEST_MARKER"])
real_popen = subprocess.Popen
calls = []
class Child:
    def __init__(self, child): self.child = child
    def __getattr__(self, name): return getattr(self.child, name)
    def communicate(self, data=None, timeout=None):
        return self.child.communicate(b"{}" if data is not None else None, timeout=timeout)
def launch(args, **kwargs):
    assert args[1:4] == ["-I", "-S", "-c"]
    assert args[4].encode() == original
    assert "fixture-refresh-secret" not in repr(args)
    helper.write_text("from pathlib import Path\nPath(%r).write_text('unsafe')\n" % str(marker))
    child = real_popen(args, **kwargs)
    calls.append(child)
    return Child(child)
lease.subprocess.Popen = launch
credential = json.dumps({"type":"authorized_user", "client_id":"fixture",
                         "client_secret":"fixture-secret", "refresh_token":"fixture-refresh-secret"}).encode()
try:
    try:
        lease._exchange_token(credential)
        raise AssertionError("invalid fake credentials must fail before any request")
    except HeinzelError:
        pass
    assert len(calls) == 1 and calls[0].poll() is not None
    assert not marker.exists()
finally:
    helper.write_bytes(original)
"""
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "HZ_TEST_MARKER": str(tmp_path / "unsafe-marker")}
    result = subprocess.run([sys.executable, "-I", "-c", script], env=env, capture_output=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert not (tmp_path / "unsafe-marker").exists()
