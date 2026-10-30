"""Captured Gmail metadata reads are separate from calendar grants and stay inside exact reviewed terms."""

import json
import time

import heinzel
import pytest
from heinzel import Config, CurrentUser, HeinzelError, Kernel, Module, ModuleRecord, Settings
from heinzel.kernel import Origin

if not hasattr(heinzel, "ConnectedReadLease"):
    pytest.skip("Captured reads require the newer host SDK", allow_module_level=True)

from heinzel_google import _connected_mail as mail
from heinzel_google._captured_mail import CapturedGmailRead
from heinzel_google._connected_calendar import GoogleConnectedReadService
from heinzel_google._gws import GoogleSession, Gws, Process
from heinzel_google._mail import Gmail
from heinzel_google._models import GoogleSettings

pytestmark = pytest.mark.unit


def _bounded_page(count, params):
    assert params["maxResults"] == 100
    start = 100 if "pageToken" in params else 0
    end = min(start + 100, count)
    page = {"messages": [{"id": f"m{index}"} for index in range(start, end)]}
    if end < count:
        page["nextPageToken"] = "next"
    return Process(0, json.dumps(page).encode())


def _metadata_page(params, state):
    item = {
        "id": "foreign" if state["bad_id"] else params["id"],
        "internalDate": "1767261600000",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Example"},
                {"name": "From", "value": "A Person <person@example.org>"},
            ]
        },
    }
    if state["snippet"]:
        item["snippet"] = "private-body-excerpt"
    if state["extra_header"]:
        item["payload"]["headers"].append({"name": "X-Secret", "value": "private-body-excerpt"})
    return Process(0, json.dumps(item).encode())


@pytest.fixture
def prepared(tmp_path, monkeypatch):  # noqa: C901 - multiple explicit fake provider routes
    # Unit tests isolate adapter behavior; installed-wheel tests cover real host source admission.
    monkeypatch.setattr("heinzel_google._connected_calendar._captured_source_enabled", True)
    executable = tmp_path / "gws"
    executable.write_bytes(b"\xcf\xfa\xed\xfe" + b"fake")
    executable.chmod(0o700)
    config = Config(files=(), data={"google": {"gws_path": str(executable)}, "capabilities": {"mail": "google"}})
    current_config = {"value": config}
    monkeypatch.setattr(Config, "load", classmethod(lambda _cls, _cwd=None: current_config["value"]))
    credential = json.dumps(
        {"type": "authorized_user", "client_id": "client", "client_secret": "secret", "refresh_token": "refresh"}
    ).encode()
    state = {
        "account": "account-one",
        "commands": [],
        "exports": 0,
        "credential": credential,
        "bad_id": False,
        "snippet": False,
        "extra_header": False,
        "provider_error": False,
        "repeat": False,
        "rotate_on_first_page": False,
        "list_size": None,
    }

    class FakeLease(CapturedGmailRead):
        @staticmethod
        def _exchange(exported):
            assert exported == credential
            return "private-token", time.monotonic() + 300, ("drive", "gmail")

        def _run(self, executable, arguments, timeout, context):  # noqa: C901, PLR0911 - explicit fake provider routes
            args = list(arguments)
            if args == ["--version"]:
                return Process(0, b"gws 0.22.5")
            if args == ["auth", "export", "--unmasked"]:
                state["exports"] += 1
                return Process(0, state["credential"])
            assert context[0]["GOOGLE_WORKSPACE_CLI_TOKEN"] == "private-token"
            if args[:3] == ["drive", "about", "get"]:
                return Process(0, json.dumps({"user": {"permissionId": state["account"], "me": True}}).encode())
            state["commands"].append(args)
            if state["provider_error"]:
                return Process(1, b"private-provider-secret", b"private-provider-secret")
            if args[:4] == ["gmail", "users", "labels", "list"]:
                return Process(0, b'{"labels":[]}')
            if args[:4] == ["gmail", "users", "messages", "list"]:
                params = json.loads(args[5])
                if state["list_size"] is not None:
                    return _bounded_page(state["list_size"], params)
                if "pageToken" not in params:
                    if state["rotate_on_first_page"]:
                        state["account"] = "other"
                    return Process(0, b'{"messages":[{"id":"m1"}],"nextPageToken":"next"}')
                if state["repeat"]:
                    return Process(0, b'{"messages":[{"id":"m2"}],"nextPageToken":"next"}')
                return Process(0, b'{"messages":[{"id":"m1"},{"id":"m2"}]}')
            if args[:4] == ["gmail", "users", "messages", "get"]:
                return _metadata_page(json.loads(args[5]), state)
            msg = "unexpected command"
            raise AssertionError(msg)

    monkeypatch.setattr(mail, "CapturedGmailRead", FakeLease)
    module = Module("google", "fixture")
    module.settings(GoogleSettings)
    module.service(GoogleSession)
    module.service(Gws)
    module.provides("mail", modes={"read"}, name="google", hosts=["fixture.invalid"])(Gmail)
    kernel = Kernel(
        Settings(),
        [
            ModuleRecord(
                qualname="google",
                module=module,
                origin=Origin(distribution="heinzel-google", version="0.9.1", builtin=False),
            )
        ],
        config=config,
    )
    current = CurrentUser(tmp_path / "identity")
    kernel.bind(CurrentUser, current)
    fixed = {"query": "", "window": {"since": "2026-01-01T00:00:00Z", "until": "2026-01-02T00:00:00Z"}}
    with current.local("cli"):
        yield GoogleConnectedReadService(kernel, current), fixed, state, current_config


def test_bound_metadata_pagination_deduplicates_and_rejects_unreviewed_reads(prepared):
    service, fixed, state, _ = prepared
    assert {f"{item.capability}.{item.method}" for item in service.supported_reads()} == {
        "calendar.events",
        "mail.messages",
        "documents.read",
    }
    lease = service.open_lease("hz-test", "capability-method:mail.messages", fixed)
    review = lease.review()
    assert review.fixed_arguments == fixed
    assert "candidate metadata outside" in review.candidate_read_disclosure
    assert "at most 100" in review.candidate_read_disclosure
    if hasattr(heinzel, "ConnectedItemIdentity"):
        assert review.item_identity.collection == ()
        assert review.item_identity.identity_field == "id"
        assert review.item_identity.revision_field is None
    else:
        assert "item_identity" not in review.model_dump()
    values = lease.read({})
    assert [item["id"] for item in values] == ["m1", "m2"]
    gets = [item for item in state["commands"] if item[:4] == ["gmail", "users", "messages", "get"]]
    assert len(gets) == 2
    assert all(json.loads(item[5])["format"] == "metadata" for item in gets)
    assert all(json.loads(item[5])["fields"] == "id,threadId,internalDate,labelIds,payload(headers)" for item in gets)
    with pytest.raises(HeinzelError):
        lease.read({"id": "foreign"})
    lease.close()


@pytest.mark.parametrize("count", [100, 101])
def test_mail_bounded_listing_never_silently_truncates(prepared, count):
    service, fixed, state, _ = prepared
    state["list_size"] = count
    lease = service.open_lease("hz-test", "capability-method:mail.messages", fixed)
    try:
        if count == 100:
            assert len(lease.read({})) == 100
        else:
            with pytest.raises(HeinzelError):
                lease.read({})
            assert not any(args[:4] == ["gmail", "users", "messages", "get"] for args in state["commands"])
    finally:
        lease.close()


def test_changed_account_credentials_or_mail_selection_fail_closed(prepared):
    service, fixed, state, current_config = prepared
    lease = service.open_lease("hz-test", "capability-method:mail.messages", fixed)
    state["account"] = "other"
    with pytest.raises(HeinzelError):
        lease.read({})
    lease.close()
    state["account"] = "account-one"
    lease = service.open_lease("hz-test", "capability-method:mail.messages", fixed)
    state["credential"] = state["credential"].replace(b"refresh", b"changed")
    with pytest.raises(HeinzelError):
        lease.read({})
    lease.close()
    state["credential"] = state["credential"].replace(b"changed", b"refresh")
    lease = service.open_lease("hz-test", "capability-method:mail.messages", fixed)
    current_config["value"] = Config(files=(), data={"capabilities": {"mail": "other"}})
    with pytest.raises(HeinzelError):
        lease.read({})
    lease.close()


def test_mismatched_metadata_id_fails_without_returning_content(prepared):
    service, fixed, state, _ = prepared
    state["bad_id"] = True
    lease = service.open_lease("hz-test", "capability-method:mail.messages", fixed)
    with pytest.raises(HeinzelError, match="reviewed terms"):
        lease.read({})
    lease.close()


def test_exact_sender_query_is_enforced_in_provider_request(prepared):
    service, fixed, state, _ = prepared
    fixed = {**fixed, "query": "from:example.org"}
    lease = service.open_lease("hz-test", "capability-method:mail.messages", fixed)
    assert len(lease.read({})) == 2
    listing = next(item for item in state["commands"] if item[:4] == ["gmail", "users", "messages", "list"])
    assert 'from:"example.org"' in json.loads(listing[5])["q"]
    lease.close()


def test_subject_filter_is_refused_before_credential_capture(prepared):
    service, fixed, state, _ = prepared
    with pytest.raises(HeinzelError):
        service.open_lease("hz-test", "capability-method:mail.messages", {**fixed, "query": 'subject:"private"'})
    assert state["exports"] == 0
    assert state["commands"] == []


def test_repeated_provider_cursor_fails_closed(prepared):
    service, fixed, state, _ = prepared
    state["repeat"] = True
    lease = service.open_lease("hz-test", "capability-method:mail.messages", fixed)
    with pytest.raises(HeinzelError):
        lease.read({})
    assert not any(item[:4] == ["gmail", "users", "messages", "get"] for item in state["commands"])
    lease.close()


def test_account_change_between_pages_stops_before_next_read(prepared):
    service, fixed, state, _ = prepared
    state["rotate_on_first_page"] = True
    lease = service.open_lease("hz-test", "capability-method:mail.messages", fixed)
    with pytest.raises(HeinzelError):
        lease.read({})
    assert sum(item[:4] == ["gmail", "users", "messages", "list"] for item in state["commands"]) == 1
    lease.close()


def test_provider_failure_does_not_expose_private_output(prepared):
    service, fixed, state, _ = prepared
    lease = service.open_lease("hz-test", "capability-method:mail.messages", fixed)
    state["provider_error"] = True
    with pytest.raises(HeinzelError) as error:
        lease.read({})
    assert "private-provider-secret" not in str(error.value)
    lease.close()


@pytest.mark.parametrize("field", ["snippet", "extra_header"])
def test_unexpected_provider_content_is_refused_and_never_returned(prepared, field):
    service, fixed, state, _ = prepared
    state[field] = True
    lease = service.open_lease("hz-test", "capability-method:mail.messages", fixed)
    with pytest.raises(HeinzelError) as error:
        lease.read({})
    assert "private-body-excerpt" not in str(error.value)
    lease.close()


@pytest.mark.parametrize(
    ("command", "params"),
    [
        (
            ["gmail", "users", "messages", "get"],
            {
                "userId": "me",
                "id": "unlisted",
                "format": "metadata",
                "metadataHeaders": ["From", "To", "Cc", "Subject"],
            },
        ),
        (["gmail", "users", "messages", "get"], {"userId": "me", "id": "m1", "format": "full"}),
        (["gmail", "users", "messages", "list"], {"userId": "other", "q": "after:0", "maxResults": 200}),
        (["gmail", "users", "messages", "send"], {"userId": "me"}),
    ],
)
def test_forbidden_commands_do_not_launch(prepared, command, params):
    service, fixed, state, _ = prepared
    lease = service.open_lease("hz-test", "capability-method:mail.messages", fixed)
    before = len(state["commands"])
    captured = lease._lease
    with pytest.raises(HeinzelError):
        captured.run(str(captured.selection.binary), [*command, "--params", json.dumps(params), "--format", "json"], 10)
    assert len(state["commands"]) == before
    lease.close()


def test_calendar_token_does_not_satisfy_mail_scope(monkeypatch):
    from heinzel_google import _existing_lease as module

    class Child:
        pid = 1234
        returncode = 0
        scope = " ".join(module._SCOPES)

        def communicate(self, data=None, timeout=None):
            del data, timeout
            return json.dumps(
                {"access_token": "fake", "expires_in": 3600, "token_type": "Bearer", "scope": self.scope}
            ).encode(), None

    child = Child()
    commands = []
    monkeypatch.setattr(module.subprocess, "Popen", lambda args, **kwargs: commands.append(args) or child)
    monkeypatch.setattr(module, "signal_group", lambda *_args: None)
    credential = json.dumps(
        {"type": "authorized_user", "client_id": "a", "client_secret": "b", "refresh_token": "c"}
    ).encode()
    with pytest.raises(HeinzelError):
        module._exchange_token(credential, mail=True)
    assert commands[-1][-1] == "mail"
    child.scope = " ".join(module._MAIL_SCOPES)
    assert set(module._exchange_token(credential, mail=True)[2]) == set(module._MAIL_SCOPES)
