"""Owner-selected GWS source continuity, without running a launcher or a Google process."""

import hashlib
from pathlib import Path

import pytest
from heinzel import HeinzelError

from heinzel_google import _selected_gws as source
from heinzel_google._gws import GoogleSession, Gws
from heinzel_google._models import GoogleSettings

pytestmark = pytest.mark.unit


def test_direct_native_selected_from_owner_settings(tmp_path):
    executable = tmp_path / "gws"
    executable.write_bytes(b"\xcf\xfa\xed\xfe" + b"native")
    executable.chmod(0o700)
    session = GoogleSession(GoogleSettings(gws_path=str(executable)), Gws())
    snapshot = source.selected(session)
    assert snapshot.command == executable
    assert snapshot.binary == executable
    assert snapshot.wrapper is False
    executable.write_bytes(b"\xcf\xfa\xed\xfe" + b"different")
    assert source.selected(session) != snapshot


def test_known_wrapper_maps_to_existing_binary_and_detects_changes(tmp_path, monkeypatch):
    root = tmp_path / "package"
    root.mkdir()
    files = {"run.js": b"known launcher", "platform.js": b"known platform", "package.json": b"known package"}
    for name, contents in files.items():
        (root / name).write_bytes(contents)
    (root / "run.js").chmod(0o700)
    bindir = root / "bin"
    bindir.mkdir()
    binary = bindir / "gws"
    binary.write_bytes(b"\xcf\xfa\xed\xfe" + b"native")
    binary.chmod(0o700)
    monkeypatch.setattr(
        source, "_WRAPPER_FILES", {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    )
    session = GoogleSession(GoogleSettings(gws_path=str(root / "run.js")), Gws())
    snapshot = source.selected(session)
    assert snapshot.wrapper is True
    assert snapshot.binary == binary
    (root / "platform.js").write_bytes(b"changed")
    with pytest.raises(HeinzelError):
        source.selected(session)
    (root / "platform.js").write_bytes(files["platform.js"])
    binary.unlink()
    with pytest.raises(HeinzelError):
        source.selected(session)


@pytest.mark.parametrize("change", ["injected", "fresh-config"])
def test_captured_lease_refuses_changed_owner_selection_before_subprocess(tmp_path, monkeypatch, change):
    import json
    import time

    from heinzel import CurrentUser

    from heinzel_google._gws import Process

    first = tmp_path / "first"
    second = tmp_path / "second"
    for executable in (first, second):
        executable.write_bytes(b"\xcf\xfa\xed\xfe" + b"native")
        executable.chmod(0o700)
    session = GoogleSession(GoogleSettings(gws_path=str(first)), Gws())
    chosen = {"path": first}
    monkeypatch.setattr(
        source.Config,
        "load",
        classmethod(
            lambda _cls, _cwd=None: source.Config(files=(), data={"google": {"gws_path": str(chosen["path"])}})
        ),
    )
    credential = json.dumps(
        {"type": "authorized_user", "client_id": "id", "client_secret": "secret", "refresh_token": "refresh"}
    ).encode()

    class FakeSelected(source.SelectedCapturedGwsRead):
        def __init__(self, current, selected_session):
            self.calls = []
            super().__init__(current, selected_session)

        @staticmethod
        def _exchange(exported):
            assert exported == credential
            return "access", time.monotonic() + 3600, ("scope",)

        def _run(self, executable, arguments, timeout, context):
            self.calls.append(list(arguments))
            if list(arguments) == ["--version"]:
                return Process(0, b"gws 0.22.5")
            if list(arguments) == ["auth", "export", "--unmasked"]:
                return Process(0, credential)
            return Process(0, b'{"user":{"permissionId":"id","me":true}}')

    current = CurrentUser(tmp_path / "identity")
    with current.local("cli"):
        lease = FakeSelected(current, session)
        if change == "injected":
            session._settings = GoogleSettings(gws_path=str(second))
        else:
            chosen["path"] = second
        before = len(lease.calls)
        with pytest.raises(HeinzelError):
            lease.inspect_identity()
        assert len(lease.calls) == before
        lease.close()


def test_stale_initial_selection_refuses_before_version_or_export(tmp_path, monkeypatch):
    from heinzel import CurrentUser

    selected_path = tmp_path / "selected"
    changed_path = tmp_path / "changed"
    for path in (selected_path, changed_path):
        path.write_bytes(b"\xcf\xfa\xed\xfe" + b"native")
        path.chmod(0o700)
    session = GoogleSession(GoogleSettings(gws_path=str(selected_path)), Gws())
    changed = source.Config(files=(), data={"google": {"gws_path": str(changed_path)}})
    monkeypatch.setattr(source.Config, "load", classmethod(lambda _cls, _cwd=None: changed))
    calls = []

    class FakeSelected(source.SelectedCapturedGwsRead):
        def _run(self, executable, arguments, timeout, context):
            calls.append(list(arguments))
            raise AssertionError

    current = CurrentUser(tmp_path / "identity")
    with current.local("cli"), pytest.raises(HeinzelError):
        FakeSelected(current, session)
    assert calls == []


def test_unconfigured_path_never_starts_or_inspects_path(monkeypatch, tmp_path):
    from heinzel import CurrentUser

    session = GoogleSession(GoogleSettings(), Gws())
    monkeypatch.setattr(session, "executable", lambda: pytest.fail("ambient PATH must not be consulted"))
    current = CurrentUser(tmp_path / "identity")
    with current.local("cli"), pytest.raises(HeinzelError, match="Select the Google Workspace CLI"):
        source.SelectedCapturedGwsRead(current, session)


def test_owner_source_description_reads_bytes_without_launch_or_account(tmp_path, monkeypatch):
    from heinzel import CurrentUser

    executable = tmp_path / "gws"
    executable.write_bytes(b"\xcf\xfa\xed\xfe" + b"native")
    executable.chmod(0o700)
    session = GoogleSession(GoogleSettings(gws_path=str(executable)), Gws())
    config = source.Config(files=(), data={"google": {"gws_path": str(executable)}})
    monkeypatch.setattr(source.Config, "load", classmethod(lambda _cls, _cwd=None: config))
    current = CurrentUser(tmp_path / "identity")
    with current.local("cli"):
        result = source.describe_selection(current, session)
    assert result.binary == executable
    assert result.binary_sha256 == hashlib.sha256(executable.read_bytes()).hexdigest()
    assert result.wrapper is False
    with current.local("mcp-stdio"), pytest.raises(HeinzelError):
        source.describe_selection(current, session)
    changed = source.Config(files=(), data={"google": {"gws_path": str(tmp_path / "other")}})
    monkeypatch.setattr(source.Config, "load", classmethod(lambda _cls, _cwd=None: changed))
    with current.local("cli"), pytest.raises(HeinzelError):
        source.describe_selection(current, session)


def test_source_review_operation_discloses_unconfigured_and_never_calls_mcp(tmp_path, monkeypatch):
    from heinzel import CurrentUser
    from heinzel.kernel import OperationLet

    from heinzel_google import module, source_review

    current = CurrentUser(tmp_path / "identity")
    session = GoogleSession(GoogleSettings(), Gws())
    monkeypatch.setattr(source.Config, "load", classmethod(lambda _cls, _cwd=None: source.Config(files=(), data={})))
    monkeypatch.setattr(session, "executable", lambda: pytest.fail("source review must not resolve PATH"))
    with current.local("cli"):
        review = source_review(current, session)
    assert review.configured is False
    assert review.binary is None
    with current.local("mcp-stdio"), pytest.raises(HeinzelError):
        source_review(current, session)
    operation = next(op for op in module.lets if isinstance(op, OperationLet) and op.name == "source-review")
    assert operation.heads == frozenset({"cli", "web"})


@pytest.mark.parametrize("kind", ["calendar", "mail"])
def test_selected_npm_wrapper_runs_only_verified_native_binary_and_fences_changes(tmp_path, monkeypatch, kind):  # noqa: PLR0915 - inspect each source fence
    import json
    import time
    from datetime import UTC, datetime, timedelta

    from heinzel import Config, CurrentUser

    from heinzel_google._captured_mail import CapturedGmailRead
    from heinzel_google._existing_lease import CapturedGwsRead, ReadWindow
    from heinzel_google._gws import Process

    root = tmp_path / "package"
    root.mkdir()
    files = {"run.js": b"known launcher", "platform.js": b"known platform", "package.json": b"known package"}
    for name, contents in files.items():
        (root / name).write_bytes(contents)
    (root / "run.js").chmod(0o700)
    (root / "bin").mkdir()
    binary = root / "bin" / "gws"
    binary.write_bytes(b"\xcf\xfa\xed\xfe" + b"native")
    binary.chmod(0o700)
    monkeypatch.setattr(
        source, "_WRAPPER_FILES", {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    )
    config = Config(files=(), data={"google": {"gws_path": str(root / "run.js")}})
    monkeypatch.setattr(Config, "load", classmethod(lambda _cls, _cwd=None: config))
    credential = json.dumps(
        {"type": "authorized_user", "client_id": "id", "client_secret": "secret", "refresh_token": "refresh"}
    ).encode()
    commands = []

    def fake_run(_self, executable, args, _timeout, _context):
        assert executable == str(_self._captured_executable)
        assert Path(executable).read_bytes() == binary.read_bytes()
        commands.append(list(args))
        if list(args) == ["--version"]:
            return Process(0, b"gws 0.22.5")
        if list(args) == ["auth", "export", "--unmasked"]:
            return Process(0, credential)
        if list(args)[:3] == ["drive", "about", "get"]:
            return Process(0, b'{"user":{"permissionId":"owner","me":true}}')
        if list(args)[:3] == ["calendar", "events", "list"]:
            return Process(0, b'{"items":[]}')
        if list(args)[:4] == ["gmail", "users", "labels", "list"]:
            return Process(0, b'{"labels":[]}')
        raise AssertionError

    monkeypatch.setattr(Gws, "_run", fake_run)
    monkeypatch.setattr(
        CapturedGwsRead, "_exchange", staticmethod(lambda _data: ("private", time.monotonic() + 300, ("scope",)))
    )
    monkeypatch.setattr(
        CapturedGmailRead, "_exchange", staticmethod(lambda _data: ("private", time.monotonic() + 300, ("scope",)))
    )
    session = GoogleSession(GoogleSettings(gws_path=str(root / "run.js")), Gws())
    current = CurrentUser(tmp_path / "identity")
    window = ReadWindow(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=1))
    with current.local("cli"):
        lease = (
            source.SelectedCapturedGwsRead(current, session)
            if kind == "calendar"
            else CapturedGmailRead(current, session)
        )
        identity, scopes = lease.inspect_identity(), lease.observed_scopes()
        if kind == "calendar":
            lease.bind_review(identity, window, scopes)
            params = {
                "calendarId": "primary",
                "timeMin": window.since.isoformat(),
                "timeMax": window.until.isoformat(),
                "singleEvents": True,
                "showDeleted": False,
                "maxResults": 10,
            }
            args = ["calendar", "events", "list", "--params", json.dumps(params), "--format", "json"]
        else:
            lease.bind_mail_review(identity, window, scopes, "")
            args = ["gmail", "users", "labels", "list", "--params", '{"userId":"me"}', "--format", "json"]
        assert lease.run(str(root / "run.js"), args, 3).exit_code == 0
        before = len(commands)
        (root / "platform.js").write_bytes(b"changed")
        with pytest.raises(HeinzelError):
            lease.run(str(root / "run.js"), args, 3)
        assert len(commands) == before
        (root / "platform.js").write_bytes(files["platform.js"])
        binary.write_bytes(b"\xcf\xfa\xed\xfe" + b"changed")
        with pytest.raises(HeinzelError):
            lease.run(str(root / "run.js"), args, 3)
        assert len(commands) == before
        binary.unlink()
        with pytest.raises(HeinzelError):
            lease.run(str(root / "run.js"), args, 3)
        assert len(commands) == before
        lease.discard()
        with pytest.raises(HeinzelError):
            source.SelectedCapturedGwsRead(current, session)
        assert len(commands) == before
