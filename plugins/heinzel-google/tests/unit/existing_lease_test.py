"""Fake-process coverage of the unregistered captured-connection adapter."""

import json
import pickle
import shutil
import subprocess
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from heinzel import CurrentUser, HeinzelError

from heinzel_google._existing_lease import (
    CapturedGwsRead,
    DriveIdentity,
    ReadWindow,
    _capture_binary,
    _credentials,
    binary_digest,
)
from heinzel_google._gws import GoogleSession, Process
from heinzel_google._models import GoogleSettings

pytestmark = pytest.mark.unit


def test_selected_path_replacement_during_launch_uses_captured_executable(tmp_path, monkeypatch):
    original = Path(shutil.which("true"))
    replacement = Path(shutil.which("false"))
    selected = tmp_path / "gws"
    next_binary = tmp_path / "replacement"
    shutil.copyfile(original, selected)
    shutil.copyfile(replacement, next_binary)
    selected.chmod(0o700)
    next_binary.chmod(0o700)
    lease = object.__new__(CapturedGwsRead)
    lease._executable = selected
    lease._digest = binary_digest(selected)
    lease._temporary = tempfile.TemporaryDirectory(dir=tmp_path)
    lease._captured_executable = Path(lease._temporary.name) / "gws-captured"
    _capture_binary(selected, lease._captured_executable, lease._digest)
    actual_popen = subprocess.Popen
    launched = []

    def replace_at_launch(args, **kwargs):
        next_binary.replace(selected)
        launched.append(args[0])
        return actual_popen(args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", replace_at_launch)
    try:
        result = lease._run(str(selected), [], 10, ({"PATH": "/usr/bin:/bin"}, str(tmp_path), 1024))
        assert result.exit_code == 0
        assert launched == [str(lease._captured_executable)]
        assert binary_digest(selected) != lease._digest
    finally:
        lease._temporary.cleanup()


def test_capture_rejects_changed_bytes(tmp_path):
    source = tmp_path / "gws"
    source.write_bytes(b"\xcf\xfa\xed\xfe" + b"first")
    digest = binary_digest(source)
    source.write_bytes(b"\xcf\xfa\xed\xfe" + b"other")
    with pytest.raises(HeinzelError, match="could not be captured"):
        _capture_binary(source, tmp_path / "captured", digest)


CREDENTIAL = json.dumps(
    {
        "type": "authorized_user",
        "client_id": "client",
        "client_secret": "private-secret",
        "refresh_token": "private-refresh",
    }
).encode()


class FakeLease(CapturedGwsRead):
    def __init__(self, current, executable):
        self.exported = CREDENTIAL
        self.version = b"gws 0.22.5"
        self.calls = []
        self.about = {"user": {"permissionId": "permission-123", "me": True, "emailAddress": "display@example.invalid"}}
        super().__init__(current, executable)

    @staticmethod
    def _exchange(exported):
        assert exported == CREDENTIAL
        return "private-access-token", time.monotonic() + 3600, ("provider.scope",)

    def _run(self, executable, arguments, timeout, context):
        env, cwd, limit = context
        args = list(arguments)
        self.calls.append((args, dict(env), cwd, limit))
        if args == ["--version"]:
            return Process(0, self.version)
        if args == ["auth", "export", "--unmasked"]:
            return Process(0, self.exported)
        assert env["GOOGLE_WORKSPACE_CLI_TOKEN"] == "private-access-token"
        assert "GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE" not in env
        assert env["HOME"] == env["GOOGLE_WORKSPACE_CLI_CONFIG_DIR"] == cwd
        assert "GOOGLE_APPLICATION_CREDENTIALS" not in env
        if args[:3] == ["drive", "about", "get"]:
            return Process(0, json.dumps(self.about).encode())
        params = json.loads(args[4])
        if "pageToken" not in params:
            return Process(0, b'{"items": [], "nextPageToken": "page-2"}')
        return Process(0, b'{"items": []}')


@pytest.fixture
def setup(tmp_path):
    binary = tmp_path / "gws"
    binary.write_bytes(b"\xcf\xfa\xed\xfe" + b"fake executable")
    binary.chmod(0o700)
    return CurrentUser(tmp_path / "identity"), binary


def _window():
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return ReadWindow(start, start + timedelta(days=1))


def _args(window, page=None):
    params = {
        "calendarId": "primary",
        "timeMin": window.since.isoformat(),
        "timeMax": window.until.isoformat(),
        "singleEvents": True,
        "showDeleted": True,
        "maxResults": 250,
    }
    if page is not None:
        params["pageToken"] = page
    return ["calendar", "events", "list", "--params", json.dumps(params), "--format", "json"]


def test_same_private_lease_for_identity_and_pages_and_cleanup(setup):
    current, binary = setup
    with current.local("cli"):
        lease = FakeLease(current, binary)
        identity = lease.inspect_identity()
        assert identity == DriveIdentity("permission-123", "display@example.invalid")
        window = _window()
        lease.bind_review(identity, window, lease.observed_scopes())
        session = GoogleSession(GoogleSettings(gws_path=str(binary)), lease)
        params = json.loads(_args(window)[4])
        pages = list(session.pages("Calendar", ("calendar", "events", "list"), params, "reviewed window", "items"))
        assert len(pages) == 2
        reads = [c for c in lease.calls if c[0][:3] in (["drive", "about", "get"], ["calendar", "events", "list"])]
        assert len({c[1]["GOOGLE_WORKSPACE_CLI_TOKEN"] for c in reads}) == 1
        directory = Path(reads[0][2])
        assert directory.stat().st_mode & 0o777 == 0o700
        assert "private-secret" not in repr(lease) + repr(identity)
        with pytest.raises(TypeError):
            pickle.dumps(lease)
        lease.close()
        assert not directory.exists()


def test_rotation_source_and_executable_rejected(setup, monkeypatch):
    current, binary = setup
    with current.local("cli"):
        lease = FakeLease(current, binary)
        window = _window()
        lease.bind_review(lease.inspect_identity(), window, lease.observed_scopes())
        lease.exported = CREDENTIAL.replace(b"private-refresh", b"rotated-refresh")
        with pytest.raises(HeinzelError):
            lease.run(str(binary), _args(window), 3)
        assert not any(c[0][:3] == ["calendar", "events", "list"] for c in lease.calls)
        lease.close()
        lease = FakeLease(current, binary)
        monkeypatch.setenv("GOOGLE_WORKSPACE_CLI_TOKEN", "ambient")
        with pytest.raises(HeinzelError):
            lease.inspect_identity()
        monkeypatch.delenv("GOOGLE_WORKSPACE_CLI_TOKEN")
        binary.write_bytes(b"\xcf\xfa\xed\xfe" + b"changed")
        with pytest.raises(HeinzelError):
            lease.inspect_identity()
        lease.close()


def test_review_scope_and_foreign_context_refused(setup):
    current, binary = setup
    with current.local("cli"):
        lease = FakeLease(current, binary)
        window = _window()
        with pytest.raises(HeinzelError):
            lease.bind_review(DriveIdentity("other", None), window, lease.observed_scopes())
        with pytest.raises(HeinzelError):
            lease.bind_review(lease.inspect_identity(), window, ("different.scope",))
        with pytest.raises(HeinzelError):
            lease.run(str(binary), _args(window), 3)
        lease.bind_review(lease.inspect_identity(), window, lease.observed_scopes())
        with pytest.raises(HeinzelError):
            lease.run(str(binary), ["calendar", "events", "insert"], 3)
        args = _args(window).copy()
        params = json.loads(args[4])
        params["calendarId"] = "other"
        args[4] = json.dumps(params)
        with pytest.raises(HeinzelError):
            lease.run(str(binary), args, 3)
        with current.local("mcp-stdio"), pytest.raises(HeinzelError):
            lease.inspect_identity()
        lease.close()


@pytest.mark.parametrize(
    "data",
    [
        b"{}",
        b'{"type":"authorized_user","type":"authorized_user"}',
        b"NaN",
        CREDENTIAL[:-1] + b',"token_uri":"https://evil.invalid"}',
        b"x" * 32769,
    ],
    ids=["empty", "duplicate", "nonfinite", "endpoint", "oversized"],
)
def test_invalid_export_is_rejected_without_credential_contents(data):
    with pytest.raises(HeinzelError) as error:
        _credentials(data)
    assert "private-secret" not in str(error.value)


def test_invalid_identity_and_expired_token_fail_closed(setup):
    current, binary = setup
    with current.local("cli"):
        lease = FakeLease(current, binary)
        lease.about = {"user": {"permissionId": "permission-123", "me": False}}
        with pytest.raises(HeinzelError):
            lease.inspect_identity()
        lease.about = {"user": {"permissionId": "permission-123", "me": True}}
        identity = lease.inspect_identity()
        assert identity.email is None
        window = _window()
        lease.bind_review(identity, window, lease.observed_scopes())
        lease._expires = time.monotonic() - 1
        with pytest.raises(HeinzelError):
            lease.run(str(binary), _args(window), 3)
        assert not any(c[0][:3] == ["calendar", "events", "list"] for c in lease.calls)
        lease.close()


def test_other_authenticated_head_and_environment_are_rejected(setup, monkeypatch):
    from heinzel import CallIdentity

    current, binary = setup
    with current.local("cli"):
        lease = FakeLease(current, binary)
        with (
            current.using(CallIdentity(current.owner(), "api-bearer", "other", "other", frozenset({"private:read"}))),
            pytest.raises(HeinzelError),
        ):
            lease.inspect_identity()
        monkeypatch.setenv("GOOGLE_WORKSPACE_CLI_CONFIG_DIR", "/different/source")
        with pytest.raises(HeinzelError):
            lease.inspect_identity()
        monkeypatch.delenv("GOOGLE_WORKSPACE_CLI_CONFIG_DIR")
        lease.close()


def test_new_lease_rejects_ambient_credentials_and_version(setup, monkeypatch):
    current, binary = setup
    with current.local("cli"):
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/ambient")
        with pytest.raises(HeinzelError):
            FakeLease(current, binary)
        monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS")

        class WrongVersion(FakeLease):
            def _run(self, executable, arguments, timeout, context):
                if list(arguments) == ["--version"]:
                    return Process(0, b"gws 0.23.0")
                msg = "unsupported version must never export credentials"
                raise AssertionError(msg)

        with pytest.raises(HeinzelError):
            WrongVersion(current, binary)


def test_page_chain_identity_and_timeout_fences(setup):
    current, binary = setup
    with current.local("cli"):
        lease = FakeLease(current, binary)
        window = _window()
        lease.bind_review(lease.inspect_identity(), window, lease.observed_scopes())
        with pytest.raises(HeinzelError):
            lease.run(str(binary), _args(window, "invented"), 3)
        for timeout in (float("nan"), float("inf"), 0, 121):
            with pytest.raises(HeinzelError):
                lease.run(str(binary), _args(window), timeout)
        lease.run(str(binary), _args(window), 3)
        with pytest.raises(HeinzelError):
            lease.run(str(binary), _args(window), 3)
        lease.about = {"user": {"permissionId": "different", "me": True}}
        with pytest.raises(HeinzelError):
            lease.run(str(binary), _args(window, "page-2"), 3)
        assert len([c for c in lease.calls if c[0][:3] == ["calendar", "events", "list"]]) == 1
        lease.close()


def test_interrupted_process_is_killed_and_reaped(monkeypatch):
    import io
    import signal

    from heinzel_google import _gws

    class Interrupted:
        pid = 1234
        stdout = io.BytesIO(b"")
        stderr = io.BytesIO(b"")
        waits = 0

        def wait(self, _timeout):
            self.waits += 1
            if self.waits == 1:
                raise KeyboardInterrupt
            return -9

    child = Interrupted()
    signals = []
    monkeypatch.setattr(_gws.subprocess, "Popen", lambda *args, **kwargs: child)
    monkeypatch.setattr(_gws, "signal_group", lambda pid, sig: signals.append((pid, sig)))
    with pytest.raises(KeyboardInterrupt):
        _gws.Gws()._run("fake", [], 1, ({}, "/", 100))
    assert signals == [(1234, signal.SIGKILL)]
    assert child.waits == 2


def test_close_waits_for_started_page(setup):
    import threading

    current, binary = setup
    entered = threading.Event()
    release = threading.Event()
    closed = threading.Event()
    failures = []

    class Delayed(FakeLease):
        def _run(self, executable, arguments, timeout, context):
            if list(arguments)[:3] == ["calendar", "events", "list"]:
                entered.set()
                if not release.wait(3):
                    raise RuntimeError
            return super()._run(executable, arguments, timeout, context)

    with current.local("cli"):
        lease = Delayed(current, binary)
        window = _window()
        lease.bind_review(lease.inspect_identity(), window, lease.observed_scopes())

        def read():
            try:
                with current.local("cli"):
                    lease.run(str(binary), _args(window), 3)
            except HeinzelError as exc:
                failures.append(exc)

        def close():
            try:
                with current.local("cli"):
                    lease.close()
                    closed.set()
            except HeinzelError as exc:
                failures.append(exc)

        reader = threading.Thread(target=read)
        closer = threading.Thread(target=close)
        reader.start()
        assert entered.wait(3)
        closer.start()
        assert not closed.wait(0.05)
        release.set()
        reader.join(3)
        closer.join(3)
        assert closed.is_set()
        assert not failures
        with pytest.raises(HeinzelError):
            lease.run(str(binary), _args(window), 3)


def test_constructor_failure_cleans_even_after_context_is_lost(setup):
    current, binary = setup
    location = []

    class ContextLost(FakeLease):
        def _run(self, executable, arguments, timeout, context):
            if list(arguments) == ["auth", "export", "--unmasked"]:
                location.append(Path(context[1]))
                current._context.set(None)
                raise KeyboardInterrupt
            return super()._run(executable, arguments, timeout, context)

    with current.local("cli"), pytest.raises(KeyboardInterrupt):
        ContextLost(current, binary)
    assert len(location) == 1
    assert not location[0].exists()


def test_interrupted_binary_capture_removes_partial_private_copy(setup, monkeypatch):
    current, binary = setup
    locations = []

    def interrupt(_source, destination, _digest):
        locations.append(destination.parent)
        destination.write_bytes(b"partial")
        raise KeyboardInterrupt

    monkeypatch.setattr("heinzel_google._existing_lease._capture_binary", interrupt)
    with current.local("cli"), pytest.raises(KeyboardInterrupt):
        FakeLease(current, binary)
    assert len(locations) == 1
    assert not locations[0].exists()


def test_fixed_token_exchange_uses_one_bounded_safe_http_request(monkeypatch):
    from heinzel_google import _token_exchange as module

    calls = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, limit):
            assert limit == 32769
            return b'{"result":"fictional"}'

    class Opener:
        def open(self, request, timeout):
            calls.append((request, timeout))
            return Response()

    def opener(*handlers):
        assert any(isinstance(h, module._NoRedirect) for h in handlers)
        assert any(isinstance(h, module.urllib.request.ProxyHandler) and not h.proxies for h in handlers)
        return Opener()

    monkeypatch.setattr(module.urllib.request, "build_opener", opener)
    assert module.exchange(CREDENTIAL) == b'{"result":"fictional"}'
    request, timeout = calls[0]
    assert request.full_url == "https://oauth2.googleapis.com/token"
    assert request.get_method() == "POST"
    assert timeout == 10
    assert len(calls) == 1
    assert module._NoRedirect().redirect_request(None, None, 302, "", None, "https://evil.invalid") is None


def test_token_helper_deadline_and_scope(monkeypatch):
    from heinzel_google import _existing_lease as module

    class Child:
        pid = 1234
        returncode = 0
        scope = " ".join(module._SCOPES)
        slow = False

        def __init__(self):
            self.calls = []

        def communicate(self, data=None, timeout=None):
            self.calls.append((data, timeout))
            if self.slow and data is not None:
                command = "helper"
                raise module.subprocess.TimeoutExpired(command, timeout)
            body = json.dumps(
                {"access_token": "fake", "expires_in": 3600, "token_type": "Bearer", "scope": self.scope}
            ).encode()
            return body, None

    child = Child()
    signals = []
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: child)
    monkeypatch.setattr(module, "signal_group", lambda pid, sig: signals.append((pid, sig)))
    token, expiry, scopes = module._exchange_token(CREDENTIAL)
    assert token == "fake"
    assert expiry > time.monotonic()
    assert set(scopes) == set(module._SCOPES)
    assert child.calls[0] == (CREDENTIAL, 30.0)
    assert signals
    child.scope += " previously-granted-extra-scope"
    _, _, broad_scopes = module._exchange_token(CREDENTIAL)
    assert "previously-granted-extra-scope" in broad_scopes
    child.scope = "previously-granted-extra-scope"
    with pytest.raises(HeinzelError):
        module._exchange_token(CREDENTIAL)
    child.slow = True
    with pytest.raises(HeinzelError):
        module._exchange_token(CREDENTIAL)


def test_cancelled_page_removes_private_temporary_state(setup):
    current, binary = setup

    class Interrupted(FakeLease):
        def _run(self, executable, arguments, timeout, context):
            if list(arguments)[:3] == ["calendar", "events", "list"]:
                raise KeyboardInterrupt
            return super()._run(executable, arguments, timeout, context)

    with current.local("cli"):
        lease = Interrupted(current, binary)
        window = _window()
        lease.bind_review(lease.inspect_identity(), window, lease.observed_scopes())
        directory = Path(lease._temporary.name)
        assert lease._captured_executable.is_file()
        with pytest.raises(KeyboardInterrupt):
            lease.run(str(binary), _args(window), 3)
        assert not directory.exists()
        assert lease._token == ""


def test_continuation_cannot_change_query(setup):
    current, binary = setup
    with current.local("cli"):
        lease = FakeLease(current, binary)
        window = _window()
        lease.bind_review(lease.inspect_identity(), window, lease.observed_scopes())
        lease.run(str(binary), _args(window), 3)
        args = _args(window, "page-2")
        params = json.loads(args[4])
        params["showDeleted"] = False
        args[4] = json.dumps(params)
        with pytest.raises(HeinzelError):
            lease.run(str(binary), args, 3)
        lease.run(str(binary), _args(window, "page-2"), 3)
        with pytest.raises(HeinzelError):
            lease.run(str(binary), _args(window, "page-2"), 3)
        lease.close()


def test_unreaped_process_is_reported_uncertain(monkeypatch):
    import io

    from heinzel_google import _gws

    class Unreaped:
        pid = 1234
        stdout = io.BytesIO(b"")
        stderr = io.BytesIO(b"")

        def wait(self, _timeout):
            command = "fake"
            raise _gws.subprocess.TimeoutExpired(command, 1)

    monkeypatch.setattr(_gws.subprocess, "Popen", lambda *args, **kwargs: Unreaped())
    monkeypatch.setattr(_gws, "signal_group", lambda _pid, _sig: None)
    with pytest.raises(OSError, match="could not be confirmed stopped"):
        _gws.Gws()._run("fake", [], 1, ({}, "/", 100))


def test_dribbling_helper_is_killed_at_total_deadline(monkeypatch):
    import subprocess
    import sys

    from heinzel_google import _existing_lease as module

    original = subprocess.Popen
    children = []
    script = (
        "import sys,time; sys.stdin.buffer.read();\nwhile True:\n"
        " sys.stdout.buffer.write(b'x'); sys.stdout.buffer.flush(); time.sleep(.03)"
    )

    def slow_helper(*_args, **kwargs):
        process = original([sys.executable, "-I", "-S", "-c", script], **kwargs)
        children.append(process)
        return process

    monkeypatch.setattr(module, "_EXCHANGE_TIMEOUT", 0.15)
    monkeypatch.setattr(module.subprocess, "Popen", slow_helper)
    started = time.monotonic()
    with pytest.raises(HeinzelError):
        module._exchange_token(CREDENTIAL)
    assert time.monotonic() - started < 3
    assert len(children) == 1
    assert children[0].poll() is not None


def test_actual_calendar_adapter_returns_fake_provider_event(setup):
    from heinzel import Window

    from heinzel_google._calendar import GoogleCalendar

    current, binary = setup

    class CalendarLease(FakeLease):
        def _run(self, executable, arguments, timeout, context):
            result = super()._run(executable, arguments, timeout, context)
            if list(arguments)[:3] == ["calendar", "events", "list"]:
                page = json.loads(arguments[4]).get("pageToken")
                if page is None:
                    payload = {
                        "items": [
                            {
                                "id": "event-1",
                                "summary": "Example event",
                                "start": {"dateTime": "2026-01-01T10:00:00Z"},
                                "end": {"dateTime": "2026-01-01T11:00:00Z"},
                            }
                        ],
                        "nextPageToken": "page-2",
                    }
                    return Process(0, json.dumps(payload).encode())
            return result

    with current.local("cli"):
        lease = CalendarLease(current, binary)
        window = _window()
        lease.bind_review(lease.inspect_identity(), window, lease.observed_scopes())
        calendar = GoogleCalendar(GoogleSession(GoogleSettings(gws_path=str(binary)), lease))
        events = calendar.events(Window(since=window.since, until=window.until))
        assert [event.id for event in events] == ["event-1"]
        assert events[0].title == "Example event"
        lease.close()


@pytest.mark.parametrize(("artifact", "scope_name"), [("document", "document"), ("spreadsheet", "spreadsheet")])
def test_artifact_exchange_requires_its_exact_read_scope_without_exposing_credential(monkeypatch, artifact, scope_name):
    from heinzel_google import _existing_lease as module

    expected = module.ARTIFACT_SCOPES[scope_name]
    commands = []

    class Child:
        pid = 1234
        returncode = 0
        scope = " ".join(expected)

        def communicate(self, data=None, timeout=None):
            assert timeout is not None
            return json.dumps(
                {"access_token": "fake", "expires_in": 3600, "token_type": "Bearer", "scope": self.scope}
            ).encode(), None

    child = Child()

    def launch(args, **_kwargs):
        commands.append(args)
        return child

    monkeypatch.setattr(module.subprocess, "Popen", launch)
    monkeypatch.setattr(module, "signal_group", lambda *_args: None)
    _token, _expiry, scopes = module._exchange_token(CREDENTIAL, artifact=artifact)
    assert set(scopes) == set(expected)
    assert commands[0][-1] == artifact
    assert "private-refresh" not in str(commands[0])
    child.scope = "https://www.googleapis.com/auth/drive.metadata.readonly"
    with pytest.raises(HeinzelError):
        module._exchange_token(CREDENTIAL, artifact=artifact)
