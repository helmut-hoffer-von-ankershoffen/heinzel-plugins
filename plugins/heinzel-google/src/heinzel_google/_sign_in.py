"""Sign in to Google from the app: `gws auth login` asking for exactly the grants Heinzel needs (ADR 0136).

`gws` owns the sign-in and its secrets: this provider only starts `gws auth login --scopes <list>`, hands Core the
consent page gws prints, and says how it ended. It never reads gws's credentials, never runs `gws auth status` (its
output is not known to be free of secrets) and never asks for `cloud-platform` or `--full`. gws sends the browser back
to a local address on the computer Heinzel runs on, so the page must be opened there (`finish_on="host"`).

Which grants hold is unknown: gws keeps no record of its scopes that Heinzel may read. So every grant is `unknown`,
and Core's choice (`wanted`) asks for the default reads, what the bound capabilities need, and what the person allows.
"""

import re
import threading
from collections.abc import Callable, Iterable

from heinzel import HeinzelError
from heinzel.kernel import (
    CapabilityView,
    Grant,
    GrantStatus,
    SignInOutcome,
    SignInProgress,
    SignInStatus,
)

from heinzel_google._gws import (
    CALENDAR_WRITE_SCOPE,
    CLIENT,
    DOCUMENTS_WRITE_SCOPE,
    INSTALL,
    MAIL_SCOPE,
    MAIL_WRITE_SCOPE,
    SCOPES,
    SETUP,
    GoogleSession,
    Gws,
    GwsSignInError,
    redact,
)
from heinzel_google._module import module

CALENDAR_READ_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
DOCUMENT_READ_SCOPES = tuple(scope for scope in SCOPES if scope != CALENDAR_READ_SCOPE)
GRANTS = (
    Grant(
        id="docs-read",
        title="Read your Docs, Sheets and Slides",
        explanation=(
            "Heinzel can read the Google Docs, Sheets and Slides you give it and see the names of your Drive files; "
            "it can't change them."
        ),
        capability="documents",
        modes=["read"],
        scopes=list(DOCUMENT_READ_SCOPES),
        default=True,
    ),
    Grant(
        id="calendar-read",
        title="Read your calendar",
        explanation="Heinzel can see the events in your Google Calendar; it can't change them.",
        capability="calendar",
        modes=["read"],
        scopes=[CALENDAR_READ_SCOPE],
        default=True,
    ),
    Grant(
        id="mail-read",
        title="Read your mail",
        explanation="Heinzel can read all of your Gmail; it can't send, change or delete anything.",
        capability="mail",
        modes=["read"],
        scopes=[MAIL_SCOPE],
    ),
    Grant(
        id="calendar-write",
        title="Change your calendar",
        explanation="Heinzel can create, move, cancel and answer events, each only after you confirm it.",
        capability="calendar",
        modes=["write"],
        scopes=[CALENDAR_WRITE_SCOPE],
    ),
    Grant(
        id="docs-write",
        title="Add to your Docs",
        explanation="Heinzel can add to your Google Docs, each change only after you confirm it.",
        capability="documents",
        modes=["write"],
        scopes=[DOCUMENTS_WRITE_SCOPE],
    ),
    Grant(
        id="mail-write",
        title="Draft, send and file your mail",
        explanation=(
            "Heinzel can keep drafts, send the ones you confirm and file conversations; it never deletes mail. "
            "It can read your mail too."
        ),
        capability="mail",
        modes=["read", "write"],
        scopes=[MAIL_WRITE_SCOPE],
    ),
)
"""What the sign-in can ask Google for. Reads of Docs and the calendar are asked for first; mail only when the person
reads mail from Google or allows it, a write only when the person allows it."""
FORBIDDEN = ("cloud-platform",)
"""Scope words never asked for: Heinzel has no use for the person's Google Cloud projects."""
CONSENT = re.compile(r"https://accounts\.google\.com/\S+")
"""Google's consent page, as `gws auth login` prints it."""
NO_CLIENT = f"gws has no OAuth client yet, so it can't sign in. Give it one first: {CLIENT}."
LIVE = 15.0
"""Seconds the live status's one read may take."""
LOGIN_TIMEOUT = 900.0
"""Seconds a sign-in may wait for the person's consent; Core stops it at the same limit."""


def scopes(grants: Iterable[str]) -> list[str]:
    """The scopes of `grants`, in the order they are declared, each once.

    Gmail's modify scope covers reading, so with `mail-write` the read-only Gmail scope is left out.

    Raises:
        ValueError: If a scope would reach Google Cloud (never asked for).
    """
    chosen = set(grants)
    found = [scope for grant in GRANTS if grant.id in chosen for scope in grant.scopes]
    if "mail-write" in chosen:
        found = [scope for scope in found if scope != MAIL_SCOPE]
    if any(word in scope for scope in found for word in FORBIDDEN):  # pragma: no cover - the grants above never do
        msg = "A Google sign-in never asks for Google Cloud access"
        raise ValueError(msg)
    return list(dict.fromkeys(found))


def ended(code: int | None, *, stopped: bool) -> SignInOutcome:
    """How a `gws auth login` that exited with `code` (None: stopped, `stopped` by whom) ended, in plain words."""
    if code is None and stopped:
        return SignInOutcome(state="cancelled", message="The Google sign-in was stopped.")
    if code is None:
        message = "Google's consent page was not answered in time. Sign in to Google again."
        return SignInOutcome(state="timed-out", message=message)
    if code != 0:
        message = (
            f"The Google sign-in did not finish (gws stopped with exit {code}). "
            f"Sign in to Google again, or run {SETUP} in a terminal to see why."
        )
        return SignInOutcome(state="failed", message=message)
    return SignInOutcome(state="succeeded", message="Signed in to Google.")


class GoogleSignIn:
    """Runs gws's own sign-in for the person; the kernel injects the session, gws and the capability bindings."""

    def __init__(self, session: GoogleSession, gws: Gws, view: CapabilityView) -> None:
        """Sign in with the gws the session selects."""
        self._session = session
        self._gws = gws
        self._view = view

    def _needed(self) -> set[str]:
        """The grants what is bound to Google reads with; mail only when the person chose Google for it."""
        needed = {"docs-read"} if self._view.bound("documents") == "google" else set()
        if self._view.bound("calendar") == "google":
            needed.add("calendar-read")
        provider, how = self._view.binding("mail")
        if provider == "google" and how != "automatic":
            needed.add("mail-read")
        return needed

    def status(self, *, live: bool) -> SignInStatus:
        """Whether gws has a sign-in, from its files alone; with `live`, Google is asked who it is (Drive's about).

        Every grant is `unknown`: gws keeps no record of its scopes that Heinzel may read.
        """
        needed = self._needed()
        grants = [GrantStatus(grant=grant, state="unknown", needed=grant.id in needed) for grant in GRANTS]
        local = self._local(grants)
        if not live or local.signed_in is not True:
            return local
        return self._live(grants)

    def _local(self, grants: list[GrantStatus]) -> SignInStatus:
        """The status from gws's version and files: whether it is installed, new enough, and has a sign-in."""
        try:
            self._session.executable()
        except HeinzelError as exc:
            return SignInStatus(signed_in=None, grants=grants, tool="missing", install=INSTALL, problem=str(exc))
        try:
            signed_in, detail = self._session.signed_in()
        except HeinzelError as exc:
            return SignInStatus(signed_in=None, grants=grants, tool="unsupported", install=INSTALL, problem=str(exc))
        problem = NO_CLIENT if not signed_in and "OAuth client" in detail else ""
        return SignInStatus(signed_in=signed_in, grants=grants, problem=problem)

    def _live(self, grants: list[GrantStatus]) -> SignInStatus:
        """Ask Google who gws is signed in as: Drive's `about.get`, the account's address only."""
        try:
            about, _ = self._session.get(
                "Google Drive", ("drive", "about", "get"), {"fields": "user(emailAddress)"}, "your account", LIVE
            )
        except GwsSignInError:
            problem = "Google no longer accepts this sign-in. Sign in to Google again."
            return SignInStatus(signed_in=False, grants=grants, problem=problem, live=True)
        except HeinzelError as exc:
            return SignInStatus(signed_in=True, grants=grants, problem=str(exc), live=True)
        user = about.get("user")
        email = user.get("emailAddress") if isinstance(user, dict) else None
        account = redact(email) if isinstance(email, str) else ""
        return SignInStatus(signed_in=True, account=account, grants=grants, live=True)

    def sign_in(
        self, grants: frozenset[str], progress: Callable[[SignInProgress], None], stop: threading.Event
    ) -> SignInOutcome:
        """Run `gws auth login --scopes <exactly grants' scopes>`, report Google's consent page, and how it ended."""
        asked = scopes(grants)
        executable, refused = self._ready(asked)
        if executable is None:
            return SignInOutcome(state="failed", message=refused)
        shown = threading.Event()

        def line(text: str) -> None:
            found = CONSENT.search(text)
            if found is None or shown.is_set():
                return
            try:  # an address Core refuses is left out, never printed in a thread's error
                page = SignInProgress(url=found.group(0), finish_on="host")
            except ValueError:
                return
            shown.set()
            progress(page)

        try:
            code = self._gws.sign_in(
                executable, ["auth", "login", "--scopes", ",".join(asked)], line, stop, LOGIN_TIMEOUT
            )
        except OSError as exc:
            message = f"gws could not be started ({type(exc).__name__}). Check it with {SETUP}."
            return SignInOutcome(state="failed", message=message)
        return ended(code, stopped=stop.is_set())

    def _ready(self, asked: list[str]) -> tuple[str | None, str]:
        """Gws's path, or None and why it can't sign in: nothing asked, gws missing or old, or no OAuth client."""
        if not asked:
            return None, "Choose at least one thing Heinzel may do with Google."
        try:
            executable = self._session.executable()
            signed_in, detail = self._session.signed_in()
        except HeinzelError as exc:
            return None, str(exc)
        if not signed_in and "OAuth client" in detail:
            return None, NO_CLIENT
        return executable, ""

    def sign_out(self) -> str:
        """`gws auth logout`, which removes gws's sign-in; what happened."""
        try:
            done = self._gws.run(self._session.executable(), ["auth", "logout"], 30.0)
        except HeinzelError as exc:
            return str(exc)
        except OSError as exc:
            return f"gws could not be started ({type(exc).__name__}), so it is still signed in."
        if done.exit_code == 0:
            return "Signed out of Google: gws removed its sign-in."
        return f"gws could not sign out (exit {done.exit_code}), so it may still be signed in."


module.sign_in(grants=GRANTS)(GoogleSignIn)
