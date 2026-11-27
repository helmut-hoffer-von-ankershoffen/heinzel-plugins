"""Local native process fixtures prove bounded output and process-group quiescence without Slack access."""

import os
import sys
import time
from pathlib import Path
from unittest.mock import Mock

import pytest
from heinzel import HeinzelError

from heinzel_slack.links import _cli_process
from heinzel_slack.links._cli_process import run

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("error", [None, ProcessLookupError(), PermissionError("private denial")])
def test_single_owned_group_signal_precedes_bounded_reap(monkeypatch, error):
    process = Mock(pid=123, returncode=None)
    events = []

    def signal_group(*_):
        events.append("signal")
        if error:
            raise error

    kill = Mock(side_effect=signal_group)
    monkeypatch.setattr(_cli_process.os, "killpg", kill)
    process.wait.side_effect = lambda **_: events.append("reap")
    if isinstance(error, PermissionError):
        with pytest.raises(PermissionError) as failure:
            _cli_process._retire(process)
        assert failure.value is error
    else:
        _cli_process._retire(process)
    assert events == ["signal", "reap"]
    kill.assert_called_once_with(123, _cli_process.signal.SIGKILL)
    assert 0 <= process.wait.call_args.kwargs["timeout"] <= _cli_process._CLEANUP


@pytest.mark.parametrize("denial", [None, PermissionError("private denial")])
def test_failed_bounded_reap_retains_ownership_and_original_denial(monkeypatch, denial):
    process = Mock(pid=123, returncode=None)
    kill = Mock(side_effect=denial)
    monkeypatch.setattr(_cli_process.os, "killpg", kill)
    process.wait.side_effect = _cli_process.subprocess.TimeoutExpired("owned", 1)
    deferred = Mock()
    monkeypatch.setattr(_cli_process, "_defer_reap", deferred)
    with pytest.raises(PermissionError if denial else _cli_process.subprocess.TimeoutExpired) as failure:
        _cli_process._retire(process)
    if denial:
        assert failure.value is denial
    deferred.assert_called_once_with(process)
    kill.assert_called_once_with(123, _cli_process.signal.SIGKILL)
    assert 0 <= process.wait.call_args.kwargs["timeout"] <= _cli_process._CLEANUP


def test_permission_denial_is_redacted_after_reaping(monkeypatch, tmp_path):
    process = Mock(pid=123, returncode=0)
    monkeypatch.setattr(_cli_process.subprocess, "Popen", Mock(return_value=process))
    observe = Mock(return_value=True)
    monkeypatch.setattr(_cli_process, "_exited", observe)
    kill = Mock(side_effect=PermissionError("synthetic-secret"))
    monkeypatch.setattr(_cli_process.os, "killpg", kill)
    with pytest.raises(HeinzelError, match="bounded request") as failure:
        run(Path("/fictional/cli"), [], {"HOME": str(tmp_path)}, 2)
    assert "synthetic-secret" not in str(failure.value)
    process.wait.assert_called_once()
    process.poll.assert_not_called()
    observe.assert_called_once_with(123)
    kill.assert_called_once_with(123, _cli_process.signal.SIGKILL)


def test_deferred_reaper_retains_child_until_wait_completes(monkeypatch):
    process = Mock()
    thread = Mock()
    factory = Mock(return_value=thread)
    monkeypatch.setattr(_cli_process.threading, "Thread", factory)
    _cli_process._defer_reap(process)
    assert process in _cli_process._REAPING
    thread.start.assert_called_once()
    process.wait.assert_not_called()
    factory.call_args.kwargs["target"]()
    process.wait.assert_called_once_with()
    assert process not in _cli_process._REAPING


def test_normal_completion(tmp_path):
    assert run(Path(sys.executable), ["-c", "print('ok')"], {"HOME": str(tmp_path)}, 2) == b"ok\n"


def test_leader_exit_cleans_descendant_before_delayed_work(tmp_path):
    # Only sandbox-owned native children; no Slack, credentials or host processes.
    marker = tmp_path / "finished"
    ready = tmp_path / "ready"
    child = (
        f"import time,pathlib; pathlib.Path({str(ready)!r}).touch(); "
        f"time.sleep(1); pathlib.Path({str(marker)!r}).write_text('done')"
    )
    program = (
        f"import subprocess,sys,time,pathlib; subprocess.Popen([sys.executable, '-c', {child!r}]); "
        f"\nwhile not pathlib.Path({str(ready)!r}).exists(): time.sleep(0.01)"
        "\nprint('ok')"
    )
    started = time.monotonic()
    result = run(Path(sys.executable), ["-c", program], {"HOME": str(tmp_path)}, 2)
    assert result == b"ok\n"
    assert time.monotonic() - started < 1
    time.sleep(1.1)
    assert not marker.exists()


def test_timeout_reaps_a_native_child_before_returning(tmp_path):
    pidfile = tmp_path / "pid"
    program = f"import os,time,pathlib; pathlib.Path({str(pidfile)!r}).write_text(str(os.getpid())); time.sleep(30)"
    with pytest.raises(HeinzelError, match="bounded request"):
        run(
            Path(sys.executable),
            ["-c", program],
            {"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"},
            0.2,
        )
    pid = int(pidfile.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_oversized_output_and_unstructured_failure_are_bounded_and_never_echoed(
    tmp_path,
):
    environment = {"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"}
    with pytest.raises(HeinzelError, match="bounded request"):
        run(
            Path(sys.executable),
            ["-c", "print('x' * (2 * 1024 * 1024))"],
            environment,
            2,
        )
    with pytest.raises(HeinzelError, match="bounded request") as failure:
        run(
            Path(sys.executable),
            ["-c", "raise RuntimeError('synthetic-secret')"],
            environment,
            2,
        )
    assert "synthetic-secret" not in str(failure.value)


@pytest.mark.parametrize(
    "members,size,code,accepted",
    [
        ([], 0, 0, True),
        ([123], 4, 0, True),
        ([456], 4, 0, False),
        ([123, 456], 8, 0, False),
        ([123, 123], 8, 0, False),
        ([0], 4, 0, False),
        ([], -1, 0, False),
        ([], 1, 0, False),
        ([123, 456, 789], 12, 0, False),
        ([], 16, 0, False),
        ([], 0, 1, False),
    ],
)
def test_darwin_scoped_group_snapshot(monkeypatch, members, size, code, accepted):
    def snapshot(kind, pid, buffer, capacity):
        assert (kind, pid, capacity) == (2, 123, 12)
        assert _cli_process.ctypes.get_errno() == 0
        for index, member in enumerate(members):
            buffer[index] = member
        _cli_process.ctypes.set_errno(code)
        return size

    function = Mock(side_effect=snapshot)
    monkeypatch.setattr(_cli_process.ctypes, "CDLL", Mock(return_value=Mock(proc_listpids=function)))
    assert _cli_process._darwin_group_empty_or_leader(123) is accepted
    function.assert_called_once()


@pytest.mark.parametrize(
    "exited,group,accepted",
    [(True, True, True), (False, True, False), (True, False, False)],
)
def test_darwin_eperm_is_checked_before_reap(monkeypatch, exited, group, accepted):
    import errno

    events = []
    process = Mock(pid=123, returncode=None)
    denial = PermissionError(errno.EPERM, "private")
    monkeypatch.setattr(_cli_process.sys, "platform", "darwin")
    monkeypatch.setattr(_cli_process.os, "killpg", Mock(side_effect=denial))
    monkeypatch.setattr(_cli_process, "_exited", lambda pid: events.append("exit") or exited)
    snapshot = Mock(side_effect=lambda pid: events.append("group") or group)
    monkeypatch.setattr(_cli_process, "_darwin_group_empty_or_leader", snapshot)
    process.wait.side_effect = lambda **kw: events.append("reap")
    if accepted:
        _cli_process._retire(process)
    else:
        with pytest.raises(PermissionError):
            _cli_process._retire(process)
    assert events == (["exit", "group", "reap"] if exited else ["exit", "reap"])


def test_python_waitid_is_non_reaping_and_checks_identity(monkeypatch):
    observe = Mock(return_value=Mock(si_pid=123, si_code=1))
    for name, value in {
        "P_PID": 1,
        "WEXITED": 4,
        "WNOHANG": 1,
        "WNOWAIT": 32,
        "CLD_EXITED": 1,
        "CLD_KILLED": 2,
        "CLD_DUMPED": 3,
    }.items():
        monkeypatch.setattr(_cli_process.os, name, value, raising=False)
    monkeypatch.setattr(_cli_process.os, "waitid", observe, raising=False)
    assert _cli_process._exited(123)
    observe.assert_called_once_with(1, 123, 37)
    observe.return_value = Mock(si_pid=456, si_code=1)
    assert not _cli_process._exited(123)


def test_darwin_observation_error_preserves_denial(monkeypatch):
    import errno

    monkeypatch.setattr(_cli_process.sys, "platform", "darwin")
    monkeypatch.setattr(_cli_process, "_exited", Mock(side_effect=ChildProcessError()))
    group = Mock()
    monkeypatch.setattr(_cli_process, "_darwin_group_empty_or_leader", group)
    assert not _cli_process._benign_denial(Mock(pid=123, returncode=None), PermissionError(errno.EPERM, "private"))
    group.assert_not_called()


@pytest.mark.parametrize(
    "platform,code,returncode",
    [("linux", 1, None), ("darwin", 13, None), ("darwin", 1, 0)],
)
def test_denial_probe_requires_darwin_eperm_and_pinned_child(monkeypatch, platform, code, returncode):
    monkeypatch.setattr(_cli_process.sys, "platform", platform)
    observe = Mock()
    monkeypatch.setattr(_cli_process, "_exited", observe)
    assert not _cli_process._benign_denial(Mock(pid=123, returncode=returncode), OSError(code, "private"))
    observe.assert_not_called()
