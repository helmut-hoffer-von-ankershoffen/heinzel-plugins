"""Bounded synchronous native CLI processes; no return leaves local provider work running."""

import os
import signal
import subprocess
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

from heinzel import HeinzelError

_LIMIT = 1024 * 1024


def run(executable: Path, arguments: Sequence[str], environment: Mapping[str, str], timeout: float) -> bytes:
    """Run fixed adapter arguments, cap both outputs and reap the process group before returning.

    Raises:
        HeinzelError: If the bounded request fails; stdout and stderr never enter error messages.
    """
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
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
            while process.poll() is None:
                if (
                    time.monotonic() >= deadline
                    or max(os.fstat(out.fileno()).st_size, os.fstat(err.fileno()).st_size) > _LIMIT
                ):
                    exceeded = True
                    break
                time.sleep(0.01)
        finally:
            # The process group is killed even when the parent exited normally; descendants cannot retain work.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        if (
            exceeded
            or process.returncode != 0
            or max(os.fstat(out.fileno()).st_size, os.fstat(err.fileno()).st_size) > _LIMIT
        ):
            msg = "Slack CLI did not acknowledge this bounded request; inspect before any retry"
            raise HeinzelError(msg)
        out.seek(0)
        return out.read(_LIMIT)
