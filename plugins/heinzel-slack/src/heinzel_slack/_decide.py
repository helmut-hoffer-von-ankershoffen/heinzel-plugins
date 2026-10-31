"""Is this click an approval? The one place Slack's answer becomes a decision (T3).

A payload from Slack is untrusted data. Only identifiers in it are read, never its text, and every one is compared
with what this machine recorded before it posted. The answer is "yes" only when all of these hold:

- it is a button click (not a reaction, a typed reply or a slash command) on one of our two buttons;
- the workspace, the person who clicked, the conversation and the message are exactly the recorded ones;
- the digest the button carries is the digest on record, and the stored draft still hashes to it;
- the request is still pending and not expired, and the click is not older than the request or from the future;
- the transition from pending wins: a second click, a retry or a replay finds it already taken.

Anything else is `Denied` with a code of ours, kept in the audit trail, and changes nothing.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, cast

from heinzel_slack._store import Store

APPROVE = "hz_approve"
DECLINE = "hz_decline"
_VALUE = re.compile(r"v1:(?P<id>[0-9a-f]{32}):(?P<digest>[0-9a-f]{64})\Z")
_SKEW = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class Decided:
    """A click that is the owner's answer to the exact draft."""

    request_id: str
    state: Literal["approved", "declined"]
    approver: str


@dataclass(frozen=True, slots=True)
class Denied:
    """A click that is not an answer; `reason` is one of our codes."""

    reason: str
    request_id: str = ""


def button_value(request_id: str, bound: str) -> str:
    """What a button carries: the request and the digest of the arguments it is for."""
    return f"v1:{request_id}:{bound}"


def _get(node: object, *path: str) -> object:
    for step in path:
        if not isinstance(node, dict):
            return None
        node = cast("dict[str, object]", node).get(step)
    return node


def _text(node: object, *path: str) -> str:
    value = _get(node, *path)
    return value if isinstance(value, str) else ""


def decide(store: Store, payload: object, now: datetime) -> Decided | Denied:  # noqa: PLR0911, C901 - a flat list of refusals
    """Turn an interactive payload into a decision, or refuse it."""
    if _get(payload, "type") != "block_actions":
        return Denied("not_a_button")
    actions = _get(payload, "actions")
    if not isinstance(actions, list) or len(cast("list[object]", actions)) != 1:
        return Denied("not_one_action")
    action = cast("list[object]", actions)[0]
    action_id = _text(action, "action_id")
    if action_id not in {APPROVE, DECLINE} or _text(action, "type") != "button":
        return Denied("not_our_button")
    match = _VALUE.fullmatch(_text(action, "value"))
    if not match:
        return Denied("bad_value")
    request_id, claimed = match["id"], match["digest"]
    row = store.get(request_id)
    if row is None:
        return Denied("unknown_request")
    checks = (
        (_text(payload, "team", "id") != row.team, "wrong_workspace"),
        (_text(payload, "user", "id") != row.owner or not row.owner, "not_the_owner"),
        (_text(payload, "channel", "id") != row.channel, "wrong_conversation"),
        (_text(payload, "container", "message_ts") != row.message_ts, "wrong_message"),
        (_text(payload, "message", "ts") != row.message_ts or not row.message_ts, "wrong_message"),
        (claimed != row.bound, "stale_draft"),
    )
    for failed, reason in checks:
        if failed:
            return Denied(reason, request_id)
    if row.state != "pending":
        return Denied(f"already_{row.state}", request_id)
    if now >= row.expires_at:
        return Denied("expired", request_id)
    try:
        clicked = datetime.fromtimestamp(float(_text(action, "action_ts")), UTC)
    except (ValueError, OverflowError, OSError):
        return Denied("bad_time", request_id)
    if clicked < row.created_at - _SKEW or clicked > now + _SKEW:
        return Denied("bad_time", request_id)
    state: Literal["approved", "declined"] = "approved" if action_id == APPROVE else "declined"
    approver = f"slack:{row.team}:{row.owner}"
    if not store.decide(request_id, state, approver, row.bound, now):
        return Denied("lost_race", request_id)
    return Decided(request_id, state, approver)
