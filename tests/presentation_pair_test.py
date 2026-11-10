"""Exercise the diagnostic supervisor's fixed reports and process cleanup."""

import errno
import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
TRACE = b"Node transport=pipe child=exited phases=entry,before-vm,after-vm,after-output node=24.22.2"


@pytest.fixture
def pair(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    return importlib.import_module("presentation_pair")


def test_trace_relays_one_fixed_marker_for_the_expected_condition(pair):
    raw = b"private test output\n" + TRACE + b"\nprivate traceback\n"
    assert pair.read_trace(raw, "pipe") == ("exited", pair.PHASES, "24.22.2")
    assert pair.read_trace(raw, "file") == pair.UNOBSERVED
    assert pair.read_trace(raw + TRACE, "pipe") == pair.UNOBSERVED
    assert pair.read_trace(TRACE + b" command=/private", "pipe") == pair.UNOBSERVED


@pytest.mark.parametrize("cleanup", [True, False])
def test_first_failure_records_both_conditions_and_refuses_unproven_cleanup(pair, monkeypatch, capsys, cleanup):
    monkeypatch.setattr(pair.platform, "python_version", lambda: "3.14.4")
    monkeypatch.setattr(pair, "enable_subreaper", lambda: None)
    calls = []

    def run(transport):
        calls.append(transport)
        if transport == "pipe":
            return "failed", cleanup, ("exited", pair.PHASES, "24.22.2")
        return "passed", True, ("completed", pair.PHASES, "24.22.2")

    monkeypatch.setattr(pair, "run_condition", run)
    assert pair.main() == 1
    assert calls == (["pipe", "file"] if cleanup else ["pipe"])
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "python=3.14.4"
    assert lines[1] == (
        f"condition=pipe result=failed cleanup={'proven' if cleanup else 'unproven'} "
        f"child=exited phases={pair.PHASES} node=24.22.2"
    )
    assert lines[2] == (
        f"condition=file result=passed cleanup=proven child=completed phases={pair.PHASES} node=24.22.2"
        if cleanup
        else "condition=file result=refused cleanup=unproven child=unobserved phases=none node=unobserved"
    )


@pytest.mark.parametrize(
    ("exit_status", "cleanup_error", "expected"),
    [(1, False, "failed"), (None, False, "outer-timeout"), (1, True, "failed"), (0, False, "invalid-trace")],
)
def test_worker_runs_exact_selector_and_cleans_even_after_timeout(
    pair, monkeypatch, exit_status, cleanup_error, expected
):
    calls = []

    class Worker:
        def wait(self, *, timeout):
            assert timeout == pair.TEST_TIMEOUT
            if exit_status is None:
                raise subprocess.TimeoutExpired("worker", timeout)
            return exit_status

    worker = Worker()

    def spawn(args, *, env, stdout, stderr):
        assert args == [sys.executable, "-m", "coverage", "run", "-m", "pytest", "-q", "-s", "--tb=no", pair.TEST]
        assert env["HZ_COMPARE_PRESENTATION_NODE"] == "pipe"
        assert stdout is stderr
        os.write(stderr.fileno(), b"private traceback\n" + TRACE + b"\n")
        return worker

    def reap(process):
        calls.append(process)
        if cleanup_error:
            raise OSError(errno.EPERM, "fixture")
        return True

    monkeypatch.setattr(pair.subprocess, "Popen", spawn)
    monkeypatch.setattr(pair, "reap_children", reap)
    assert pair.run_condition("pipe") == (expected, not cleanup_error, ("exited", pair.PHASES, "24.22.2"))
    assert calls == [worker]


def test_cleanup_rescans_adopted_children_until_kernel_reports_echild(pair, monkeypatch, tmp_path):
    children = tmp_path / "children"
    children.write_text("42")
    monkeypatch.setattr(pair, "CHILDREN", children)
    events = iter([(0, 0), (42, 0), (0, 0), (43, 0)])
    signals = []

    def waitpid(*args):
        try:
            return next(events)
        except StopIteration:
            raise ChildProcessError from None

    def send(fd, sig):
        signals.append((fd, sig))
        children.write_text("43")

    monkeypatch.setattr(pair.os, "waitpid", waitpid)
    monkeypatch.setattr(pair.os, "pidfd_open", lambda pid: pid + 100, raising=False)
    monkeypatch.setattr(pair.signal, "pidfd_send_signal", send, raising=False)
    monkeypatch.setattr(pair.os, "close", lambda _fd: None)
    monkeypatch.setattr(pair.time, "sleep", lambda _seconds: None)
    assert pair.reap_children(None)
    assert signals == [(142, pair.signal.SIGKILL), (143, pair.signal.SIGKILL)]


@pytest.mark.skipif(sys.platform != "linux", reason="Linux subreaper and pidfd kernel contract")
def test_kernel_adopts_and_reaps_a_descendant_in_another_session():
    fixture = """
import os
import subprocess
import sys

from presentation_pair import enable_subreaper, reap_children

enable_subreaper()
grandchild = "import time; time.sleep(8)"
parent = (
    "import subprocess, sys; "
    "child = subprocess.Popen([sys.executable, '-c', sys.argv[1]], start_new_session=True); "
    "print(child.pid, flush=True)"
)
with subprocess.Popen([sys.executable, "-c", parent, grandchild], stdout=subprocess.PIPE, text=True) as process:
    assert process.wait(timeout=3) == 0
    child_pid = int(process.stdout.readline())
assert os.path.isdir(f"/proc/{child_pid}")
assert reap_children(process)
assert not os.path.isdir(f"/proc/{child_pid}")
"""
    subprocess.run(  # noqa: S603 - disposable Python supervisor and descendant
        [sys.executable, "-c", fixture],
        env={**os.environ, "PYTHONPATH": str(SCRIPTS)},
        check=True,
        timeout=10,
    )
