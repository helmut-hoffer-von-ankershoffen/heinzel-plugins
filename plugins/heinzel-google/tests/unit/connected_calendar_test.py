"""The unregistered Google connected service reads only through a fixed, owner-bound fake lease."""

import json
import time

import pytest
from heinzel import CallIdentity, Config, CurrentUser, HeinzelError, Kernel, Module, ModuleRecord, Principal, Settings
from heinzel.kernel import Origin

from heinzel_google import _connected_calendar as connected
from heinzel_google._calendar import GoogleCalendar
from heinzel_google._gws import GoogleSession, Gws, Process
from heinzel_google._models import GoogleSettings
from heinzel_google._selected_gws import SelectedCapturedGwsRead

pytestmark = pytest.mark.unit


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    # Unit tests isolate adapter behavior; installed-wheel tests cover real host source admission.
    monkeypatch.setattr(connected, "_captured_source_enabled", True)
    executable = tmp_path / "gws"
    executable.write_bytes(b"\xcf\xfa\xed\xfe" + b"fake")
    executable.chmod(0o700)
    config = Config(files=(), data={"google": {"gws_path": str(executable)}, "capabilities": {"calendar": "google"}})
    config_state = {"current": config}
    monkeypatch.setattr(Config, "load", classmethod(lambda _cls, _cwd=None: config_state["current"]))
    credential = json.dumps(
        {"type": "authorized_user", "client_id": "client", "client_secret": "secret", "refresh_token": "refresh"}
    ).encode()
    state = {"account": "account-one", "reads": 0, "exports": 0, "mutation": None, "source_changed": False}
    original_digest = connected.source_digest
    monkeypatch.setattr(
        connected,
        "source_digest",
        lambda path: "changed" if state["source_changed"] and path.name == "_calendar.py" else original_digest(path),
    )

    class FakeLease(SelectedCapturedGwsRead):
        @staticmethod
        def _exchange(exported):
            assert exported == credential
            return "access", time.monotonic() + 300, ("calendar", "drive")

        def _run(self, executable, arguments, timeout, context):
            args = list(arguments)
            if args == ["--version"]:
                return Process(0, b"gws 0.22.5")
            if args == ["auth", "export", "--unmasked"]:
                state["exports"] += 1
                return Process(0, credential)
            assert context[0]["GOOGLE_WORKSPACE_CLI_TOKEN"] == "access"
            if args[:3] == ["drive", "about", "get"]:
                return Process(0, json.dumps({"user": {"permissionId": state["account"], "me": True}}).encode())
            assert args[:3] == ["calendar", "events", "list"]
            state["reads"] += 1
            if state["mutation"] == "source":
                state["source_changed"] = True
            if state["mutation"] == "config":
                config_state["current"] = Config(
                    files=(), data={"google": {"gws_path": str(executable)}, "capabilities": {"calendar": "other"}}
                )
            if state["mutation"]:
                return Process(0, b'{"items":[],"nextPageToken":"next"}')
            return Process(
                0,
                b'{"items":[{"id":"event-1","summary":"Example","start":{"dateTime":"2026-01-01T10:00:00Z"},"end":{"dateTime":"2026-01-01T11:00:00Z"}}]}',
            )

    monkeypatch.setattr(connected, "SelectedCapturedGwsRead", FakeLease)
    module = Module("google", "fixture")
    module.settings(GoogleSettings)
    module.service(GoogleSession)
    module.service(Gws)
    module.provides("calendar", modes={"read"}, name="google", hosts=["fixture.invalid"])(GoogleCalendar)
    origin = Origin(distribution="heinzel-google", version="0.9.1", builtin=False)
    kernel = Kernel(Settings(), [ModuleRecord(qualname="google", module=module, origin=origin)], config=config)
    current = CurrentUser(tmp_path / "identity")
    kernel.bind(CurrentUser, current)
    fixed = {"window": {"since": "2026-01-01T00:00:00Z", "until": "2026-01-02T00:00:00Z"}}
    with current.local("cli"):
        service = connected.GoogleConnectedReadService(kernel, current)
        yield service, current, kernel, executable, fixed, state, config, config_state


def test_owner_bound_service_observes_and_reads_selected_calendar(prepared, monkeypatch):
    service, current, kernel, executable, fixed, state, config, config_state = prepared
    with pytest.raises(HeinzelError):
        service.open_lease("hz-test", "capability-method:calendar.create_event", fixed)
    with pytest.raises(HeinzelError):
        service.open_lease("hz-test", "capability-method:calendar.events", {"window": {"since": "invalid"}})
    assert state["exports"] == 0
    lease = service.open_lease("hz-test", "capability-method:calendar.events", fixed)
    review = lease.review()
    assert review.account_identity == "account-one"
    assert review.account_display is None
    assert review.fixed_arguments == fixed
    with pytest.raises(HeinzelError):
        lease.read({"unreviewed": "value"})
    events = lease.read({})
    assert events[0]["id"] == "event-1"
    assert state["reads"] == 1
    config_state["current"] = Config(
        files=(), data={"google": {"gws_path": str(executable)}, "capabilities": {"calendar": "other"}}
    )
    with pytest.raises(HeinzelError):
        lease.read({})
    assert state["reads"] == 1
    config_state["current"] = config
    original_digest = connected.source_digest
    with monkeypatch.context() as patch:
        patch.setattr(
            connected, "source_digest", lambda path: "changed" if path.name == "_calendar.py" else original_digest(path)
        )
        with pytest.raises(HeinzelError):
            lease.read({})
    assert state["reads"] == 1
    foreign = CallIdentity(Principal("u-" + "a" * 32), "api-bearer", "other", "private", frozenset({"private:read"}))
    with current.using(foreign), pytest.raises(HeinzelError):
        lease.read({})
    state["account"] = "account-two"
    with pytest.raises(HeinzelError):
        lease.read({})
    assert state["reads"] == 1
    lease.close()
    kernel.bind(GoogleSession, GoogleSession(GoogleSettings(gws_path=str(executable)), Gws()))
    with pytest.raises(HeinzelError):
        service.open_lease("hz-test", "capability-method:calendar.events", fixed)


@pytest.mark.parametrize("mutation", ["source", "config"])
def test_each_page_rechecks_reviewed_source_and_binding(prepared, mutation):
    service, _current, _kernel, _executable, fixed, state, _config, _config_state = prepared
    lease = service.open_lease("hz-test", "capability-method:calendar.events", fixed)
    state["mutation"] = mutation
    with pytest.raises(HeinzelError):
        lease.read({})
    assert state["reads"] == 1
    lease.close()
