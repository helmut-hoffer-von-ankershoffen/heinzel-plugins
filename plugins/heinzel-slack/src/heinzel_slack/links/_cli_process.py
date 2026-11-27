"""Bounded native CLI requests with ownership-safe group signaling and leader reaping."""

import ctypes
import errno
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

from heinzel import HeinzelError

_LIMIT = 1024 * 1024
_CLEANUP = 1.0
_REAPING: set[subprocess.Popen[bytes]] = set()
_REAP_LOCK = threading.Lock()


def _exited(pid: int) -> bool:
    """Observe only our child, leaving its PID reserved until final cleanup."""
    info = os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
    return info is not None and info.si_pid == pid and info.si_code in (os.CLD_EXITED, os.CLD_KILLED, os.CLD_DUMPED)


def _darwin_group_empty_or_leader(pid: int) -> bool:
    """Bounded group-only snapshot; a full, malformed or failed result is unknown."""
    members = (ctypes.c_int * 3)()
    listpids = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True).proc_listpids
    listpids.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_int]
    listpids.restype = ctypes.c_int
    ctypes.set_errno(0)  # libproc maps syscall failure to zero; preserve the distinction.
    size = listpids(2, pid, members, ctypes.sizeof(members))  # PROC_PGRP_ONLY
    if ctypes.get_errno() or size < 0 or size >= ctypes.sizeof(members) or size % ctypes.sizeof(ctypes.c_int):
        return False
    return list(members[: size // ctypes.sizeof(ctypes.c_int)]) in ([], [pid])


def _benign_denial(process: subprocess.Popen[bytes], error: OSError) -> bool:
    if error.errno != errno.EPERM or sys.platform != "darwin" or process.returncode is not None:
        return False
    try:
        # Exit is irreversible; with the owned zombie pinned, no member can fork
        # after a snapshot containing only that leader (or no members).
        return _exited(process.pid) and _darwin_group_empty_or_leader(process.pid)
    except (OSError, AttributeError):
        return False


def _defer_reap(process: subprocess.Popen[bytes]) -> None:
    """Retain ownership after a bounded wait fails; never signal this ID again."""
    with _REAP_LOCK:
        _REAPING.add(process)

    def reap() -> None:
        try:
            process.wait()
        except OSError:
            # Keep the ownership record if the OS cannot complete the wait.
            return
        with _REAP_LOCK:
            _REAPING.discard(process)

    threading.Thread(target=reap, name="slack-cli-reap", daemon=True).start()


def _retire(process: subprocess.Popen[bytes]) -> None:
    """Signal once while the unreaped leader pins ownership, then bound its wait."""
    deadline = time.monotonic() + _CLEANUP
    failure: OSError | None = None
    try:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError as error:
            if not _benign_denial(process, error):
                failure = error
    finally:
        try:
            process.wait(timeout=max(0.0, deadline - time.monotonic()))
        except (OSError, subprocess.TimeoutExpired):
            _defer_reap(process)
            if failure is not None:
                raise failure from None
            raise
    if failure is not None:
        raise failure


def run(
    executable: Path,
    arguments: Sequence[str],
    environment: Mapping[str, str],
    timeout: float,
) -> bytes:
    """Run fixed adapter arguments, cap both outputs and reap the process group before returning.

    Raises:
        HeinzelError: If the bounded request fails; stdout and stderr never enter error messages.
    """
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        cleanup_failed = False
        try:
            process = subprocess.Popen(  # noqa: S603 - fixed native executable and adapter-only argument lists
                [str(executable), *arguments],
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                env=dict(environment),
                cwd=environment["HOME"],
                start_new_session=True,
            )
        except OSError:
            msg = "The captured Slack CLI could not start"
            raise HeinzelError(msg) from None
        deadline, exceeded = time.monotonic() + timeout, False
        try:
            # Do not poll/wait here: an unreaped leader reserves the process-group ID.
            while True:
                if (
                    time.monotonic() >= deadline
                    or max(os.fstat(out.fileno()).st_size, os.fstat(err.fileno()).st_size) > _LIMIT
                ):
                    exceeded = True
                    break
                try:
                    if _exited(process.pid):
                        break
                except InterruptedError:
                    continue
                time.sleep(0.01)
        except OSError:
            cleanup_failed = True
        finally:
            # The process group is killed even when the parent exited normally; descendants cannot retain work.
            try:
                _retire(process)
            except (OSError, subprocess.TimeoutExpired):
                cleanup_failed = True
        if (
            cleanup_failed
            or exceeded
            or process.returncode != 0
            or max(os.fstat(out.fileno()).st_size, os.fstat(err.fileno()).st_size) > _LIMIT
        ):
            msg = "Slack CLI did not acknowledge this bounded request; inspect before any retry"
            raise HeinzelError(msg)
        out.seek(0)
        return out.read(_LIMIT)
