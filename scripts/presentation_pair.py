"""Run the exact presentation selector twice and prove each test's process tree is gone."""

import ctypes
import os
import platform
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TEST = (
    "tests/presentation_test.py::"
    "test_only_exact_owning_path_text_changes_and_all_doctor_rows_statuses_and_details_remain"
)
TEST_TIMEOUT = 40
CLEANUP_TIMEOUT = 3
CHILDREN = Path(f"/proc/self/task/{os.getpid()}/children")
PHASES = "entry,before-vm,after-vm,after-output"
UNOBSERVED = ("unobserved", "none", "unobserved")
TRACE = re.compile(
    rb"Node transport=(pipe|file) child=(completed|running|exited)"
    rb" phases=(none|(?:entry|before-vm|after-vm|after-output)(?:,(?:entry|before-vm|after-vm|after-output))*)"
    rb" node=(unobserved|[0-9]+\.[0-9]+\.[0-9]+)"
)


def enable_subreaper() -> None:
    """Adopt orphaned descendants, including processes that start a new session."""
    if (
        sys.platform != "linux"
        or not CHILDREN.is_file()
        or not hasattr(os, "pidfd_open")
        or not hasattr(signal, "pidfd_send_signal")
    ):
        raise OSError("Linux process cleanup primitives unavailable.")
    # PR_SET_CHILD_SUBREAPER. A failure is fatal before the first test starts.
    if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0):
        raise OSError(ctypes.get_errno(), "Cannot become a child subreaper.")


def reap_children(process: subprocess.Popen[bytes] | None) -> bool:
    deadline = time.monotonic() + CLEANUP_TIMEOUT
    while time.monotonic() < deadline:
        try:
            child, status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            # The kernel reparents descendants before reporting their parent's exit.
            # ECHILD proves there is neither a direct child nor a tree beneath one.
            return True
        if child:
            if process is not None and child == process.pid:
                process.returncode = os.waitstatus_to_exitcode(status)
            continue
        for pid in CHILDREN.read_text().split():
            # Only this single-threaded parent can reap these PIDs. Use pidfds to
            # signal the identified children, and rescan for their adopted children.
            try:
                fd = os.pidfd_open(int(pid))
                try:
                    signal.pidfd_send_signal(fd, signal.SIGKILL)
                finally:
                    os.close(fd)
            except ProcessLookupError:
                continue
        time.sleep(0.02)
    return False


def read_trace(log: bytes, transport: str) -> tuple[str, str, str]:
    matches = [match for line in log.splitlines() if (match := TRACE.fullmatch(line))]
    if len(matches) != 1 or matches[0][1].decode() != transport:
        return UNOBSERVED
    _, child, phases, node = (part.decode() for part in matches[0].groups())
    return child, phases, node


def run_condition(transport: str) -> tuple[str, bool, tuple[str, str, str]]:
    process = None
    result = "runner-error"
    trace = UNOBSERVED
    cleanup = False
    try:
        # Keep private test output out of the job log and never wait on pipe EOF.
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryFile() as log:
            try:
                process = subprocess.Popen(
                    [sys.executable, "-m", "coverage", "run", "-m", "pytest", "-q", "-s", "--tb=no", TEST],
                    env={
                        **os.environ,
                        "HZ_COMPARE_PRESENTATION_NODE": transport,
                        "PYTEST_ADDOPTS": "",
                        "COVERAGE_FILE": str(Path(directory) / ".coverage"),
                    },
                    stdout=log,
                    stderr=log,
                )
                result = "passed" if process.wait(timeout=TEST_TIMEOUT) == 0 else "failed"
            except subprocess.TimeoutExpired:
                result = "outer-timeout"
            except OSError:
                result = "runner-error"
            finally:
                try:
                    cleanup = reap_children(process)
                except OSError:
                    pass
            log.seek(0)
            trace = read_trace(log.read(65536), transport)
    except OSError:
        pass
    if result == "passed" and (trace[:2] != ("completed", PHASES) or trace[2] == "unobserved"):
        result = "invalid-trace"
    return result, cleanup, trace


def report(transport: str, result: str, cleanup: bool, trace: tuple[str, str, str]) -> None:
    child, phases, node = trace
    proof = "proven" if cleanup else "unproven"
    print(
        f"condition={transport} result={result} cleanup={proof} child={child} phases={phases} node={node}", flush=True
    )


def main() -> int:
    print(f"python={platform.python_version()}", flush=True)
    try:
        if platform.python_version() != "3.14.4":
            raise OSError("Unexpected Python.")
        enable_subreaper()
    except OSError:
        report("pipe", "refused", False, UNOBSERVED)
        report("file", "refused", False, UNOBSERVED)
        return 1

    pipe_result, pipe_cleanup, pipe_trace = run_condition("pipe")
    report("pipe", pipe_result, pipe_cleanup, pipe_trace)
    if not pipe_cleanup:
        report("file", "refused", False, UNOBSERVED)
        return 1

    file_result, file_cleanup, file_trace = run_condition("file")
    report("file", file_result, file_cleanup, file_trace)
    return int(pipe_result != "passed" or file_result != "passed" or not file_cleanup or pipe_trace[2] != file_trace[2])


if __name__ == "__main__":
    raise SystemExit(main())
