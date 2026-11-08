"""Reading what `acli auth status` and `acli <product> auth status` print; tolerant, and never keeps a secret.

Seen in acli 1.3.39 (a made-up person; samples are in `tests/fixtures/auth`):

    ✓ Authenticated
      Site: acme.atlassian.net
      Email: ada@example.com
      Authentication Type: oauth
    Following apps are not authenticated with your global profile: Jira, Confluence

and, signed out, `✗ Error: unauthorized: use 'acli auth login' to authenticate`. The words around the fields may
change between releases, so only the fields are looked for, line by line, and anything else is ignored.
"""

import re
from dataclasses import dataclass

_CLEAN = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|[@-Z\\-_])")
_SITE_HOST = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.atlassian\.net")
_EMAIL = re.compile(r"[^\s@<>]{1,64}@[A-Za-z0-9.-]{1,255}")
_SIGNED_IN = re.compile(r"(?im)^\W*(?:authenticated|logged in|signed in)\b")
_SIGNED_OUT = re.compile(r"(?i)\bunauthori[sz]ed\b|\bnot (?:logged in|authenticated|signed in)\b|\bauth login\b")
_MISSING = re.compile(r"(?im)\bnot (?:yet )?authenticated\b[^:\n]*:\s*(?P<apps>[^\n]+)")
_FIELD = r"(?im)^\W*{}\s*:\s*(?P<value>[^\n]+)"
PRODUCTS = ("Jira", "Confluence")


@dataclass(frozen=True, slots=True)
class AuthState:
    """What one status command said. `signed_in` is None when the words are not understood."""

    signed_in: bool | None
    site: str = ""
    """The bare host, such as `acme.atlassian.net`; empty if there is none or it is not an Atlassian Cloud site."""
    email: str = ""
    kind: str = ""
    missing: tuple[str, ...] = ()
    """Products acli lists as not authenticated with the global profile, `Jira` and `Confluence` only."""


def _field(name: str, text: str) -> str:
    found = re.search(_FIELD.format(name), text)
    return found["value"].strip() if found else ""


def parse(text: str, returncode: int) -> AuthState:
    """Read a status answer; the exit status counts only when the words say nothing."""
    words = _CLEAN.sub("", text)
    host = _field("Site", words).lower().removeprefix("https://").split("/")[0]
    mail = _field("Email", words).split()
    email = mail[0] if mail else ""
    apps = _MISSING.search(words)
    missing = tuple(p for p in PRODUCTS if apps and re.search(rf"(?i)\b{p}\b", apps["apps"]))
    signed_in: bool | None
    if _SIGNED_IN.search(words):
        signed_in = True
    elif _SIGNED_OUT.search(words):
        signed_in = False
    else:
        signed_in = False if returncode != 0 and words.strip() else None
    return AuthState(
        signed_in=signed_in,
        site=host if _SITE_HOST.fullmatch(host) else "",
        email=email if _EMAIL.fullmatch(email) else "",
        kind=_field("Authentication Type", words)[:20],
        missing=missing,
    )
