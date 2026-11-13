"""Sharing status reads no peer roster and never changes OS networking or user configuration."""

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest
from heinzel import DetailLine, HeinzelError, LocalWebRuntime, Settings

import heinzel_tailscale
from heinzel_tailscale import sharing
from heinzel_tailscale._cli import TailscaleCli
from heinzel_tailscale._mapping import Mapping
from heinzel_tailscale._models import SharingIntent, SharingState, TailscaleSettings
from heinzel_tailscale._readiness import SharingReadiness
from heinzel_tailscale._service import Sharing

pytestmark = pytest.mark.unit
DNS = "workstation.tail-example.ts.net."
MAPPING = Mapping.for_node(DNS, 8737)
OTHER = "https://other.tail-example.ts.net"
INTERNAL = re.compile(
    r"\b(?:requested|applied|verified|owning|apply|intent|mapping|origin|handler|readiness)\b", re.IGNORECASE
)


@dataclass
class FakeCli(TailscaleCli):
    found: bool = True
    node: object = field(
        default_factory=lambda: {"BackendState": "Running", "Self": {"DNSName": DNS}, "CertDomains": [DNS[:-1]]}
    )
    serve: object = None
    error: bool = False
    calls: list[tuple[str, ...]] = field(default_factory=list)

    def executable(self):
        return "/fake/tailscale" if self.found else None

    def json(self, arguments: Sequence[str]):
        self.calls.append(tuple(arguments))
        if self.error:
            msg = "The client did not answer."
            raise HeinzelError(msg)
        assert tuple(arguments) in {("status", "--json", "--peers=false"), ("serve", "status", "--json")}
        return self.node if arguments[0] == "status" else self.serve


class MemoryConfig:
    def __init__(self, settings, intent=None):
        self.root = settings
        self.choices = TailscaleSettings(intent=intent)

    def reread(self):
        return self

    def settings(self, model, _section):
        return self.root if model is Settings else self.choices


class NoWebUser:
    def context(self):
        msg = "No authenticated web request"
        raise HeinzelError(msg)


class WebUser:
    def __init__(self, authentication="web-session"):
        self.authentication = authentication

    def context(self):
        return SimpleNamespace(authentication=self.authentication)


@dataclass(frozen=True)
class RefusingRuntime(LocalWebRuntime):
    def apply_origins(self, origins):
        msg = "refused for the test"
        raise ValueError(msg)


def owned_intent(**changes):
    fields = {
        "enabled": True,
        "origin": MAPPING.origin,
        "backend_port": 8737,
        "https_port": 443,
        "added_origin": False,
        "phase": "owned",
    }
    return SharingIntent(**(fields | changes))


def service(settings, cli, *, owned=False, intent=None, web=None):
    """`web` is the (runtime, user) pair of a web owner; without it the call comes from a process with no listener."""
    intent = intent or (owned_intent() if owned else None)
    runtime, user = web or (LocalWebRuntime(), NoWebUser())
    return Sharing(settings, cli, MemoryConfig(settings, intent), SharingReadiness(runtime, user))


def test_missing_client_reports_action_without_starting_a_command():
    cli = FakeCli(found=False)
    result = service(Settings(), cli).status()
    assert result.state == "unavailable"
    assert not result.installed
    assert not cli.calls


def test_logged_out_state_never_attempts_to_enable_serve():
    cli = FakeCli(node={"BackendState": "NeedsLogin"})
    result = service(Settings(), cli).status()
    assert result.state == "login-required"
    assert result.installed
    assert not result.logged_in
    assert cli.calls == [("status", "--json", "--peers=false")]


def test_read_failures_are_errors_not_claims_of_success():
    result = service(Settings(), FakeCli(error=True)).status()
    assert result.state == "error"
    assert result.origin is None


def test_no_mapping_is_off_and_contains_the_exact_nonsecret_url():
    result = service(Settings(), FakeCli()).status()
    assert result.state == "off"
    assert result.logged_in
    assert not result.mapped
    assert result.origin == "https://workstation.tail-example.ts.net"
    assert result.target == "http://127.0.0.1:8737"
    assert "token" not in result.model_dump_json()


def test_https_consent_is_required_before_an_existing_mapping_can_be_ready():
    cli = FakeCli(node={"BackendState": "Running", "Self": {"DNSName": DNS}}, serve=MAPPING.enable({}))
    result = service(Settings(), cli).status()
    assert result.state == "blocked"
    assert "HTTPS certificates" in result.message


def test_existing_mapping_requires_loaded_origin_and_serving_instance_verification():
    cli = FakeCli(serve=MAPPING.enable({}))
    result = service(Settings(), cli, owned=True).status()
    assert result.state == "apply-required"
    assert result.mapped
    loaded = service(Settings(ui_allowed_origins={MAPPING.origin}), cli, owned=True).status()
    assert loaded.state == "apply-required"
    assert loaded.summary == "Turning on…"
    assert not loaded.problem
    assert not INTERNAL.search(loaded.message)


def test_a_web_owner_finishes_a_saved_request_on_one_status_read(caplog):
    """The two-step "saved; restart/apply" flow is gone: the web owner loads the configured origin itself."""
    runtime = LocalWebRuntime(port=8737, loaded_origins=frozenset({OTHER}))
    cli = FakeCli(serve=MAPPING.enable({}))
    sharing_service = service(
        Settings(ui_allowed_origins={MAPPING.origin, OTHER}), cli, owned=True, web=(runtime, WebUser())
    )
    with caplog.at_level(logging.INFO, logger="heinzel_tailscale._readiness"):
        result = sharing_service.status()
    assert result.state == "ready"
    assert result.summary is None
    assert not result.problem
    # Only the one configured origin is added; nothing loaded before is dropped, so no session is revoked.
    assert runtime.loaded_origins == frozenset({MAPPING.origin, OTHER})
    # The read changed neither Tailscale nor the configuration: only read-only CLI commands ran.
    assert set(cli.calls) == {("status", "--json", "--peers=false"), ("serve", "status", "--json")}
    events = [(record.getMessage(), record.phase, getattr(record, "outcome", None)) for record in caplog.records]
    assert events == [("tailscale.status.finish", "start", None), ("tailscale.status.finish", "end", "ok")]
    end = caplog.records[-1]
    assert end.operation == "status"
    assert end.step == "finish"
    assert end.plugin == "heinzel-tailscale"
    assert end.port == 8737
    assert isinstance(end.duration_ms, int)
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="heinzel_tailscale._readiness"):
        again = sharing_service.status()
    assert again.state == "ready"
    assert not caplog.records  # Idempotent: a second read has nothing to finish.


def test_a_failed_finish_is_logged_and_reported_without_raising(caplog):
    runtime = RefusingRuntime(port=8737)
    cli = FakeCli(serve=MAPPING.enable({}))
    sharing_service = service(Settings(ui_allowed_origins={MAPPING.origin}), cli, owned=True, web=(runtime, WebUser()))
    with caplog.at_level(logging.INFO, logger="heinzel_tailscale._readiness"):
        result = sharing_service.status()
    assert result.state == "apply-required"
    assert result.summary == "Could not finish turning it on. Try again."
    assert result.problem
    assert "tailscale.status.finish" in result.message
    assert runtime.loaded_origins == frozenset()
    end = caplog.records[-1]
    assert (end.getMessage(), end.phase, end.outcome, end.levelname) == (
        "tailscale.status.finish",
        "end",
        "error",
        "ERROR",
    )
    assert end.error_type == "ValueError"
    assert end.error == "refused for the test"
    assert (end.operation, end.step, end.plugin) == ("status", "finish", "heinzel-tailscale")


@pytest.mark.parametrize(
    ("case", "settings", "intent", "web"),
    [
        ("not configured", Settings(), owned_intent(), (LocalWebRuntime(port=8737), WebUser())),
        ("not owned yet", None, owned_intent(phase="enabling"), (LocalWebRuntime(port=8737), WebUser())),
        ("switched off", None, owned_intent(enabled=False), (LocalWebRuntime(port=8737), WebUser())),
        ("no web listener", None, owned_intent(), (LocalWebRuntime(), WebUser())),
        ("a bearer call", None, owned_intent(), (LocalWebRuntime(port=8737), WebUser("api-bearer"))),
        ("another port", None, owned_intent(), (LocalWebRuntime(port=9123), WebUser())),
    ],
)
def test_a_status_read_finishes_nothing_it_does_not_own(case, settings, intent, web, caplog):
    settings = settings or Settings(ui_allowed_origins={MAPPING.origin})
    runtime, user = web
    cli = FakeCli(serve=MAPPING.enable({}))
    with caplog.at_level(logging.INFO, logger="heinzel_tailscale._readiness"):
        result = service(settings, cli, intent=intent, web=(runtime, user)).status()
    assert result.state != "ready", case
    assert runtime.loaded_origins == frozenset(), case
    assert not caplog.records, case


def test_a_mapping_for_another_hz_port_says_so_in_plain_words():
    runtime = LocalWebRuntime(port=9123)
    cli = FakeCli(serve=MAPPING.enable({}))
    result = service(Settings(ui_allowed_origins={MAPPING.origin}), cli, owned=True, web=(runtime, WebUser())).status()
    assert result.state == "apply-required"
    assert result.summary == "Set up for another hz port. Try again to move it."
    assert result.problem
    assert "port 8737" in result.message
    assert "port 9123" in result.message


def test_sharing_that_tailscale_dropped_while_switched_on_asks_to_try_again():
    result = service(Settings(ui_allowed_origins={MAPPING.origin}), FakeCli(), owned=True).status()
    assert result.state == "off"
    assert result.desired_enabled
    assert result.summary == "Tailscale stopped sharing. Try again."
    assert result.problem
    plain = service(Settings(), FakeCli()).status()
    assert plain.summary is None
    assert not plain.problem


def every_state():
    foreign = service(Settings(ui_allowed_origins={MAPPING.origin}), FakeCli(serve=MAPPING.enable({})))
    return [
        service(Settings(), FakeCli(found=False)).status(),
        service(Settings(), FakeCli(error=True)).status(),
        service(Settings(), FakeCli(node={"BackendState": "NeedsLogin"})).status(),
        service(Settings(), FakeCli()).status(),
        service(Settings(), FakeCli(node={"BackendState": "Running", "Self": {"DNSName": DNS}})).status(),
        service(Settings(), FakeCli(node={"BackendState": "Running"})).status(),
        service(Settings(), FakeCli(serve={"AllowFunnel": {MAPPING.authority: True}})).status(),
        service(Settings(), FakeCli(serve={"TCP": {"443": {"TCPForward": "127.0.0.1:1"}}})).status(),
        service(Settings(), FakeCli(serve={"Foreground": {"x": {}}})).status(),
        service(
            Settings(), FakeCli(serve={"Web": {MAPPING.authority: {"Handlers": {"/": {"Text": "Other"}}}}})
        ).status(),
        foreign.status(),
        service(Settings(ui_allowed_origins={MAPPING.origin}), FakeCli(serve=MAPPING.enable({})), owned=True).status(),
        service(Settings(ui_allowed_origins={MAPPING.origin}), FakeCli(), owned=True).status(),
        service(
            Settings(ui_allowed_origins={MAPPING.origin}),
            FakeCli(serve=MAPPING.enable({})),
            owned=True,
            web=(LocalWebRuntime(port=9123), WebUser()),
        ).status(),
        service(
            Settings(ui_allowed_origins={MAPPING.origin}),
            FakeCli(serve=MAPPING.enable({})),
            owned=True,
            web=(LocalWebRuntime(port=8737), WebUser()),
        ).status(),
        service(
            Settings(ui_allowed_origins={MAPPING.origin}),
            FakeCli(serve=MAPPING.enable({})),
            owned=True,
            web=(RefusingRuntime(port=8737), WebUser()),
        ).status(),
    ]


def test_every_state_has_a_short_line_in_the_persons_words_or_none():
    states = every_state()
    assert {state.state for state in states} == {
        "unavailable",
        "error",
        "login-required",
        "off",
        "blocked",
        "apply-required",
        "ready",
    }
    for state in states:
        if state.summary is None:
            assert state.state in {"off", "ready"}, state
            assert not state.problem
            continue
        assert len(state.summary) <= 60, state.summary
        assert not INTERNAL.search(state.summary), state.summary
        assert "\n" not in state.summary
    lines = {state.summary for state in states}
    assert {
        "Install Tailscale and sign in first.",
        "Tailscale did not answer. Try again.",
        "Sign in to Tailscale, then try again.",
        "Turn on HTTPS certificates in Tailscale.",
        "Turn on MagicDNS in Tailscale, then try again.",
        "Port 443 is public (Funnel). Pick another port.",
        "Port 443 is taken. Pick another port in Settings.",
        "Stop tailscale serve in the terminal, then try again.",
        "hz did not set this up. Check Tailscale Serve.",
        "Turning on…",
        "Could not finish turning it on. Try again.",
        "Set up for another hz port. Try again to move it.",
        "Tailscale stopped sharing. Try again.",
    } <= lines


def test_preexisting_matching_manual_mapping_is_reported_as_unowned():
    result = service(Settings(ui_allowed_origins={MAPPING.origin}), FakeCli(serve=MAPPING.enable({}))).status()
    assert result.state == "blocked"
    assert result.mapped
    assert result.message == (
        "Tailscale already shares this app, and hz did not set that up.\n"
        "So hz left it alone. You can keep it as it is.\n"
        "To let hz manage sharing, delete that mapping with this command:\n"
        "tailscale serve --https=443 --set-path=/ off\n"
        "Then switch sharing on here."
    )
    for jargon in ("Inspect", "inspect", "not verified", "owned"):
        assert jargon not in result.message


def test_the_pane_shows_one_short_line_and_keeps_the_long_text_for_details():
    state = service(Settings(ui_allowed_origins={MAPPING.origin}), FakeCli(serve=MAPPING.enable({}))).status()
    item = sharing(state)
    # Whichever toggle contract the installed core has, the long explanation is never bulleted under the switch.
    if heinzel_tailscale._PANE_LINES:
        assert item.detail == []
        assert item.toggle.status == "hz did not set this up. Check Tailscale Serve."
        assert item.toggle.problem is None  # Not switched on yet: the switch is the action, not Try again.
        assert item.toggle.explanation.startswith("Tailscale already shares this app, and hz did not set that up.")
        assert "tailscale serve --https=443 --set-path=/ off" in item.toggle.explanation
    else:
        assert item.detail == [DetailLine(text="hz did not set this up. Check Tailscale Serve.")]


def test_a_cause_the_person_must_fix_offers_try_again_once_they_switched_it_on():
    state = service(Settings(), FakeCli(node={"BackendState": "NeedsLogin"}), owned=True).status()
    item = sharing(state)
    assert item.toggle.requested is True
    assert item.toggle.checked is False
    if heinzel_tailscale._PANE_LINES:
        assert item.toggle.problem == "Sign in to Tailscale, then try again."
        assert item.toggle.status is None
        assert item.toggle.explanation == "Open Tailscale and sign in, then try sharing again."
    else:
        assert [line.text for line in item.detail] == ["Sign in to Tailscale, then try again."]


def test_a_ready_pane_shows_the_url_and_no_status_line():
    runtime = LocalWebRuntime(port=8737)
    state = service(
        Settings(ui_allowed_origins={MAPPING.origin}),
        FakeCli(serve=MAPPING.enable({})),
        owned=True,
        web=(runtime, WebUser()),
    ).status()
    item = sharing(state)
    assert item.toggle.checked is True
    assert item.toggle.url == MAPPING.origin
    assert item.detail == []
    if heinzel_tailscale._PANE_LINES:
        assert item.toggle.status is None
        assert item.toggle.problem is None


def test_a_plain_off_pane_has_no_details_that_repeat_the_switch():
    state = service(Settings(), FakeCli()).status()
    assert state.state == "off"
    assert state.message == "Private web sharing is off."  # The CLI and JSON keep the message.
    item = sharing(state)
    assert item.toggle.checked is False
    assert item.toggle.requested is False
    assert item.detail == []
    if heinzel_tailscale._PANE_LINES:
        assert item.toggle.status is None
        assert item.toggle.problem is None
        assert item.toggle.explanation is None


def test_a_plain_on_pane_has_no_details_that_repeat_the_switch():
    runtime = LocalWebRuntime(port=8737)
    state = service(
        Settings(ui_allowed_origins={MAPPING.origin}),
        FakeCli(serve=MAPPING.enable({})),
        owned=True,
        web=(runtime, WebUser()),
    ).status()
    assert state.state == "ready"
    assert state.message  # The CLI and JSON keep the message.
    if heinzel_tailscale._PANE_LINES:
        assert sharing(state).toggle.explanation is None


@pytest.mark.parametrize(
    "changes",
    [
        {"state": "blocked", "problem": True, "summary": "Check Tailscale Serve."},
        {"state": "error", "problem": True, "summary": "Tailscale did not answer. Try again."},
        {"state": "apply-required", "mapped": True, "summary": "Turning on…"},
        {"desired_enabled": True, "problem": True, "summary": "Tailscale stopped sharing. Try again."},
        {"apply_settings": {"hz.ui_allowed_origins": []}},
        {"mapped": True},
        {"state": "ready", "desired_enabled": False, "mapped": True},
    ],
)
def test_states_to_act_on_or_wait_for_keep_details(changes):
    if not heinzel_tailscale._PANE_LINES:
        pytest.skip("Installed Core has no toggle explanation")
    state = service(Settings(), FakeCli()).status().model_copy(update=changes)
    assert sharing(state).toggle.explanation == heinzel_tailscale.shorten(state.message)


@pytest.mark.parametrize(
    "serve",
    [
        {"Web": {MAPPING.authority: {"Handlers": {"/": {"Text": "Other app"}}}}},
        {"AllowFunnel": {MAPPING.authority: True}},
        [],
    ],
)
def test_conflicts_and_public_or_unsupported_config_are_blocked(serve):
    result = service(Settings(), FakeCli(serve=serve)).status()
    assert result.state == "blocked"
    assert result.logged_in
    assert not result.mapped


@pytest.mark.parametrize(
    "node", [{"BackendState": "Running"}, {"BackendState": "Running", "Self": {"DNSName": "evil.test"}}]
)
def test_missing_or_invalid_node_dns_is_not_a_callable_url(node):
    cli = FakeCli(node=node)
    result = service(Settings(), cli).status()
    assert result.state == "blocked"
    assert result.origin is None
    assert cli.calls == [("status", "--json", "--peers=false")]


def test_process_environment_keeps_absolute_path_entries_and_drops_credential_and_debug_settings(monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin:.:relative:/opt/bin")
    monkeypatch.setenv("HZ_CREDENTIAL_EXAMPLE", "do-not-forward")
    monkeypatch.setenv("TS_DEBUG_FAKE_ENV", "do-not-forward")
    monkeypatch.setenv("HTTPS_PROXY", "http://example.invalid")
    env = TailscaleCli.environment()
    assert env["PATH"] == "/usr/bin:/opt/bin"
    assert not {"HZ_CREDENTIAL_EXAMPLE", "TS_DEBUG_FAKE_ENV", "HTTPS_PROXY"} & env.keys()


def test_json_reads_refuse_unapproved_commands_before_starting_the_client():
    with pytest.raises(HeinzelError, match="approved command"):
        TailscaleCli().json(("funnel", "8737"))


def test_pending_control_exposes_the_request_without_claiming_on_or_exposing_a_url():
    item = sharing(
        SharingState(
            state="apply-required",
            installed=True,
            logged_in=True,
            desired_enabled=True,
            mapped=True,
            origin=MAPPING.origin,
            summary="Turning on…",
            message="Sharing is set up in Tailscale.",
        )
    )
    assert item.toggle.requested is True
    assert item.toggle.checked is False
    assert item.toggle.url is None
    assert item.toggle.disable.operation == "disable"


def test_no_message_offers_a_port_wide_off_command():
    """A bare `--https=<port> off` also removes mappings that are not hz's; only the root path may be named."""
    incomplete = SharingIntent(
        enabled=True, origin=MAPPING.origin, backend_port=8737, https_port=443, added_origin=False, phase="enabling"
    )
    cli = FakeCli(serve=MAPPING.enable({}))
    texts = [
        service(Settings(ui_allowed_origins={MAPPING.origin}), cli).status().message,
        Sharing(
            Settings(),
            cli,
            MemoryConfig(Settings(), incomplete),
            SharingReadiness(LocalWebRuntime(), NoWebUser()),
        )
        .status()
        .message,
        MAPPING.clear_command,
    ]
    for text in texts:
        assert not re.search(r"--https=\d+ off", text)
    assert "--set-path=/ off" in texts[0]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Short and whole.", "Short and whole."),
        ("First sentence is here. " + "x" * 300, "First sentence is here. …"),
        ("One. " + "word " * 80, ("One. " + "word " * 80)[:278].rsplit(" ", 1)[0] + "…"),
        ("y" * 300, "y" * 279 + "…"),
    ],
)
def test_details_text_is_cut_at_a_sentence_or_word_with_an_ellipsis(text, expected):
    assert heinzel_tailscale.shorten(text) == expected
    assert len(heinzel_tailscale.shorten(text)) <= 280


def test_long_details_keep_whole_sentences():
    text = ("This sentence is about forty characters. " * 10).strip()
    cut = heinzel_tailscale.shorten(text)
    assert len(cut) <= 280
    assert cut.endswith("characters. …")
    assert text.startswith(cut.removesuffix(" …"))
