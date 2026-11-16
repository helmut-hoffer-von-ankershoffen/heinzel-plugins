"""Bind one host-authenticated principal to an Issues operation."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

from heinzel import CurrentUser

from heinzel_issues._contract import TrackerError

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(frozen=True, slots=True)
class Access:
    """Immutable caller for one operation; legacy history is installation-owner-only."""

    actor: str
    legacy_owner: bool
    can_write: bool


_access: ContextVar[Access | None] = ContextVar("issues_access", default=None)


def access() -> Access:
    """Never infer an authenticated caller from the server process or client input."""
    result = _access.get()
    if result is None:
        raise TrackerError("Issues requires an authenticated caller.")
    return result


@contextmanager
def authenticated(current: CurrentUser) -> "Iterator[None]":
    """Snapshot the authenticated host context for this call and restore it on exit."""
    context = current.context()
    legacy = context.principal == current.owner() and context.authentication in {
        "cli",
        "web-session",
        "web-device",
        "daemon",
    }
    token = _access.set(Access(context.principal.id, legacy, "private:write" in context.permissions))
    try:
        yield
    finally:
        _access.reset(token)
