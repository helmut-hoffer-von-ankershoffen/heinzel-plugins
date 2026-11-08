"""The one status of the sign-in the connector shows: not installed, not connected, needs attention or connected.

Read from acli's own status commands, which print local state: `acli auth status` (the global OAuth profile, which
serves Rovo and Admin) and `acli <product> auth status` for each product the adapters serve. A product counts as
authorised only when its own status says so: the global profile being signed in is not enough. Signing in is the
owner's: this only names the command; nothing here runs a login or sees a secret.
"""

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, Field

from heinzel_atlassian._acli import Acli, AcliTimeoutError
from heinzel_atlassian._auth import PRODUCTS, AuthState, parse
from heinzel_atlassian._client import INSTALL_COMMAND, LOGIN, Product

STATUS_TIMEOUT = 10.0
type State = Literal["not-installed", "not-connected", "needs-attention", "connected"]
COPY_SIGN_IN = "Copy sign-in command"
COPY_INSTALL = "Copy install command"
CHECK_AGAIN = "Check again"
BROWSER = "Opens your browser to authorise {product}. Run it in a terminal, then check again."


class ProductAuth(BaseModel):
    """Whether acli is authorised for one product."""

    product: str = Field(description="`Jira` or `Confluence`.")
    authorised: bool | None = Field(description="True, False, or none when acli's answer was not understood.")


class AtlassianStatus(BaseModel):
    """The sign-in status a connector page shows; `state` drives the status dot, the rest is its text and button."""

    state: State = Field(
        description="not-installed (grey), not-connected (grey), needs-attention (amber), connected (green)."
    )
    identity: str = Field(description="Who acli is signed in as; empty if not signed in. Never a secret.")
    site: str = Field(description="The site acli is signed in to, such as acme.atlassian.net; empty if unknown.")
    cause: str = Field(description="One line, state first, no jargon.")
    products: list[ProductAuth] = Field(description="Each product the adapters serve, and whether it is authorised.")
    command: str = Field(description="The one command to copy for the next step, run by the owner; empty if none.")
    action: str = Field(description="Label of the button that copies `command`; empty if there is none.")
    explanation: str = Field(description="What the command does, for a tooltip; empty if there is none.")
    refresh: str = Field(default=CHECK_AGAIN, description="Label of the icon button that reads the status again.")


def _names(products: Sequence[str]) -> str:
    return " and ".join(products)


def _are(products: Sequence[str]) -> str:
    return "is" if len(products) == 1 else "are"


def read(acli: Acli, timeout: float, products: list[Product]) -> AtlassianStatus:
    """Read acli's sign-in state for `products` (Jira if none); runs only status commands, within `timeout`."""
    wanted: list[Product] = products or ["Jira"]
    if acli.path() is None:
        return AtlassianStatus(
            state="not-installed",
            identity="",
            site="",
            cause="acli is not installed.",
            products=[],
            command=INSTALL_COMMAND,
            action=COPY_INSTALL,
            explanation="Installs Atlassian's command line tool with Homebrew.",
        )

    def ask(args: list[str]) -> AuthState | None:
        try:
            done = acli.run(args, min(STATUS_TIMEOUT, timeout))
        except (AcliTimeoutError, OSError, RuntimeError):
            return None
        return parse((done.stdout + b"\n" + done.stderr).decode("utf-8", errors="replace"), done.returncode)

    overall = ask(["auth", "status"])
    each = {product: ask([product.lower(), "auth", "status"]) for product in wanted}
    states = [ProductAuth(product=p, authorised=s.signed_in if s else None) for p, s in each.items()]
    working = [s for s in each.values() if s is not None and s.signed_in]
    source = working[0] if working else (overall if overall is not None and overall.signed_in else None)
    email = source.email if source else ""
    site = (source.site if source else "") or (overall.site if overall else "")
    if all(s.authorised for s in states):
        who, where = f" as {email}" if email else "", f" at {site}" if site else ""
        return AtlassianStatus(
            state="connected", identity=email, site=site, cause=f"Signed in{who}{where}.", products=states,
            command="", action="", explanation="",
        )  # fmt: skip
    pending = [p for p in wanted if each[p] is None or each[p].signed_in is not True]  # type: ignore[union-attr]
    command = f"{LOGIN[pending[0]]} --web"
    explanation = BROWSER.format(product=pending[0])

    def result(state: State, cause: str) -> AtlassianStatus:
        return AtlassianStatus(
            state=state, identity=email, site=site, cause=cause, products=states,
            command=command, action=COPY_SIGN_IN, explanation=explanation,
        )  # fmt: skip

    if not any(s.authorised is False for s in states):
        return result("needs-attention", f"Could not read the {_names(pending)} status from acli.")
    if working:
        return result("needs-attention", f"{_names(pending)} {_are(pending)} not authorised yet.")
    if overall is not None and overall.signed_in:
        named = [p for p in PRODUCTS if p in pending or p in overall.missing]
        who, where = f" as {email}" if email else "", f" at {site}" if site else ""
        cause = f"Signed in to acli{who}{where}. {_names(named)} {_are(named)} not authorised yet."
        return result("needs-attention", cause)
    return AtlassianStatus(
        state="not-connected", identity="", site="", cause="Not signed in to acli.", products=states,
        command=command, action=COPY_SIGN_IN, explanation=explanation,
    )  # fmt: skip
