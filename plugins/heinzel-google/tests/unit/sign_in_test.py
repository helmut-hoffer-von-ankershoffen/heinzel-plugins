"""The Google sign-in Core runs from the app (ADR 0136), against the fake gws: grants, scopes, progress, outcomes."""

import json
import threading
from dataclasses import dataclass, field

import pytest
from heinzel.kernel import SignInLet, SignInProgress

from heinzel_google import GRANTS, GoogleSession, GoogleSettings, GoogleSignIn, Process
from heinzel_google._gws import (
    CALENDAR_WRITE_SCOPE,
    DOCUMENTS_WRITE_SCOPE,
    MAIL_SCOPE,
    MAIL_WRITE_SCOPE,
    SCOPES,
)
from heinzel_google._sign_in import scopes

pytestmark = pytest.mark.unit

CONSENT = "https://accounts.google.com/o/oauth2/auth?client_id=example.apps.googleusercontent.com&scope=x"
DEFAULTS = frozenset({"docs-read", "calendar-read"})


def output(body: object, exit_code: int = 0) -> Process:
    return Process(exit_code, json.dumps(body).encode())


@dataclass
class View:
    """The bindings the sign-in reads: capability -> (provider, how it was chosen)."""

    bindings: dict[str, tuple[str | None, str]] = field(default_factory=dict)

    def bound(self, capability: str) -> str | None:
        return self.bindings.get(capability, (None, "none"))[0]

    def binding(self, capability: str) -> tuple[str | None, str]:
        return self.bindings.get(capability, (None, "none"))


def provider(session, fake_gws, **bindings: tuple[str | None, str]) -> GoogleSignIn:
    return GoogleSignIn(session, fake_gws, View(dict(bindings)))  # type: ignore[arg-type]


def run(sign_in: GoogleSignIn, grants: frozenset[str], stop: threading.Event | None = None):
    seen: list[SignInProgress] = []
    outcome = sign_in.sign_in(grants, seen.append, stop or threading.Event())
    return outcome, seen


def test_a_first_sign_in_asks_for_the_document_and_calendar_reads_only():
    assert {grant.id for grant in GRANTS if grant.default} == DEFAULTS
    assert scopes(DEFAULTS) == list(SCOPES)


def test_no_grant_reaches_google_cloud_or_everything():
    every = scopes(grant.id for grant in GRANTS)
    assert not [scope for scope in every if "cloud-platform" in scope]
    assert "https://www.googleapis.com/auth/drive" not in every  # never all of Drive's contents
    assert set(every) == {*SCOPES, CALENDAR_WRITE_SCOPE, DOCUMENTS_WRITE_SCOPE, MAIL_WRITE_SCOPE}


@pytest.mark.parametrize(
    ("grants", "expected"),
    [
        ({"mail-read"}, [MAIL_SCOPE]),
        ({"mail-read", "mail-write"}, [MAIL_WRITE_SCOPE]),
        (
            {"calendar-read", "calendar-write"},
            ["https://www.googleapis.com/auth/calendar.readonly", CALENDAR_WRITE_SCOPE],
        ),
        ({"docs-write"}, [DOCUMENTS_WRITE_SCOPE]),
        (set(), []),
    ],
    ids=["mail read", "mail write replaces mail read", "calendar write", "docs write", "nothing"],
)
def test_the_scopes_are_exactly_those_of_the_grants(grants, expected):
    assert scopes(grants) == expected


def test_the_module_declares_one_sign_in_with_every_grant(google_kernel):
    lets = [let for record, let in google_kernel().lets(SignInLet) if record.qualname == "google"]
    assert [let.grants for let in lets] == [GRANTS]


def test_signed_in_is_read_from_gws_files_and_every_grant_is_unknown(session, fake_gws):
    status = provider(session, fake_gws).status(live=False)
    assert (status.signed_in, status.tool, status.live, status.problem) == (True, "ready", False, "")
    assert {s.state for s in status.grants} == {"unknown"}
    assert [r.command for r in fake_gws.runs] == [("--version",)]  # never `gws auth status`


@pytest.mark.parametrize(
    ("bindings", "needed"),
    [
        ({}, set()),
        ({"documents": ("google", "automatic"), "calendar": ("google", "configured")}, DEFAULTS),
        ({"mail": ("google", "automatic")}, set()),
        ({"mail": ("google", "configured")}, {"mail-read"}),
        ({"mail": ("google", "default")}, {"mail-read"}),
        ({"calendar": ("other", "configured")}, set()),
    ],
    ids=["nothing bound", "reads bound", "mail only automatic", "mail chosen", "mail as default", "another calendar"],
)
def test_what_is_bound_to_google_is_needed_and_no_write_ever_is(session, fake_gws, bindings, needed):
    status = provider(session, fake_gws, **bindings).status(live=False)
    assert {s.grant.id for s in status.grants if s.needed} == needed


def test_without_gws_the_tool_is_missing_with_its_install(fake_gws, tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    status = provider(GoogleSession(GoogleSettings(), fake_gws), fake_gws).status(live=False)
    assert (status.tool, status.signed_in) == ("missing", None)
    assert status.install.startswith("npm install -g @googleworkspace/cli")
    assert fake_gws.runs == []


def test_an_old_gws_is_unsupported(session, fake_gws):
    fake_gws.version = Process(0, b"gws 0.21.0\n")
    assert provider(session, fake_gws).status(live=False).tool == "unsupported"


def test_without_an_oauth_client_it_says_to_add_one(session, fake_gws, gws_config):
    (gws_config / "credentials.enc").unlink()
    (gws_config / "client_secret.json").unlink()
    status = provider(session, fake_gws).status(live=False)
    assert status.signed_in is False
    assert status.problem.startswith("gws has no OAuth client yet, so it can't sign in.")
    outcome, seen = run(provider(session, fake_gws), DEFAULTS)
    assert (outcome.state, seen, fake_gws.sign_ins) == ("failed", [], [])


def test_live_asks_google_who_is_signed_in(session, fake_gws):
    fake_gws.json(("drive", "about", "get"), {"user": {"emailAddress": "mira@example.com"}})
    status = provider(session, fake_gws).status(live=True)
    assert (status.signed_in, status.account, status.live) == (True, "mira@example.com", True)


def test_live_with_a_sign_in_google_refuses_says_to_sign_in_again(session, fake_gws):
    fake_gws.on(("drive", "about", "get"), output({"error": {"code": 401, "reason": "authError"}}, 2))
    status = provider(session, fake_gws).status(live=True)
    assert (status.signed_in, status.problem) == (
        False,
        "Google no longer accepts this sign-in. Sign in to Google again.",
    )


def test_a_sign_in_runs_gws_auth_login_with_exactly_the_scopes_and_reports_the_page(session, fake_gws):
    fake_gws.sign_in_lines = ["Open this URL in your browser to authenticate:", "", f"  {CONSENT}  ", CONSENT]
    outcome, seen = run(provider(session, fake_gws), DEFAULTS | {"calendar-write"})
    assert fake_gws.sign_ins == [["auth", "login", "--scopes", ",".join([*SCOPES, CALENDAR_WRITE_SCOPE])]]
    assert seen == [SignInProgress(url=CONSENT, finish_on="host")]  # once, and only on the computer Heinzel runs on
    assert (outcome.state, outcome.message, outcome.account) == ("succeeded", "Signed in to Google.", "")


def test_a_page_elsewhere_than_google_is_never_reported(session, fake_gws):
    fake_gws.sign_in_lines = ["https://evil.example/o/oauth2/auth?x", "http://accounts.google.com/plain"]
    outcome, seen = run(provider(session, fake_gws), DEFAULTS)
    assert (outcome.state, seen) == ("succeeded", [])


FAILED = (
    "The Google sign-in did not finish (gws stopped with exit 1). "
    "Sign in to Google again, or run hz setup google in a terminal to see why."
)


@pytest.mark.parametrize(
    ("code", "stopped", "ending"),
    [
        (None, True, ("cancelled", "The Google sign-in was stopped.")),
        (None, False, ("timed-out", "Google's consent page was not answered in time. Sign in to Google again.")),
        (1, False, ("failed", FAILED)),
    ],
    ids=["stopped", "timed out", "gws failed"],
)
def test_how_a_sign_in_ended_is_said_plainly(session, fake_gws, code, stopped, ending):
    fake_gws.sign_in_code = code
    stop = threading.Event()
    if stopped:
        stop.set()
    outcome, _ = run(provider(session, fake_gws), DEFAULTS, stop)
    assert (outcome.state, outcome.message) == ending
    assert "googleapis" not in outcome.message


def test_nothing_to_ask_for_starts_nothing(session, fake_gws):
    outcome, _ = run(provider(session, fake_gws), frozenset())
    assert (outcome.state, fake_gws.sign_ins) == ("failed", [])


def test_gws_that_cannot_start_is_a_plain_failure(session, fake_gws, monkeypatch):
    def broken(*args, **kwargs):
        raise PermissionError

    monkeypatch.setattr(fake_gws, "sign_in", broken)
    outcome, _ = run(provider(session, fake_gws), DEFAULTS)
    assert (outcome.state, outcome.message) == (
        "failed",
        "gws could not be started (PermissionError). Check it with hz setup google.",
    )


@pytest.mark.parametrize(
    ("answer", "said"),
    [
        (output({}, 0), "Signed out of Google: gws removed its sign-in."),
        (output({}, 1), "gws could not sign out (exit 1), so it may still be signed in."),
    ],
)
def test_sign_out_is_gws_auth_logout(session, fake_gws, answer, said):
    fake_gws.on(("auth", "logout"), answer)
    assert provider(session, fake_gws).sign_out() == said
    assert fake_gws.runs[-1].arguments == ["auth", "logout"]


def test_a_page_core_refuses_is_left_out_and_the_next_is_shown(session, fake_gws):
    fake_gws.sign_in_lines = ["https://accounts.google.com/" + "x" * 5000, CONSENT]
    outcome, seen = run(provider(session, fake_gws), DEFAULTS)
    assert (outcome.state, seen) == ("succeeded", [SignInProgress(url=CONSENT, finish_on="host")])
