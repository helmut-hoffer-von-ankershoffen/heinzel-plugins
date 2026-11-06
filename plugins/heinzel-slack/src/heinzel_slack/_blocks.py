"""What the messages say and look like: short, a little characterful, never softer than the facts (U2, U4).

Everything that is not ours is untrusted text. `plain` makes it safe for Slack's mrkdwn (no mention, link or channel
syntax survives, no control or hidden characters); the draft itself is shown in a preformatted rich-text block whose
text is literal, so what the person reads is the bytes that are approved.
"""

from datetime import datetime
from typing import Any

from heinzel import clean_text

from heinzel_slack._decide import APPROVE, DECLINE, button_value

Block = dict[str, Any]


def plain(text: str, limit: int = 300) -> str:
    """`text` as one safe, bounded piece of mrkdwn: cleaned, escaped, and cut with an ellipsis."""
    cleaned = clean_text(text).strip()
    escaped = cleaned.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return escaped if len(escaped) <= limit else escaped[: limit - 1].rstrip() + "…"


def _who(helper: str) -> str:
    return plain(helper, 40) or "Your Heinzelmännchen"


def _clock(moment: datetime) -> str:
    return moment.astimezone().strftime("%H:%M")


def notification(  # noqa: PLR0913 - the parts of one message
    helper: str, title: str, body: str, route: str = "", *, urgent: bool = False
) -> tuple[str, list[Block]]:
    """A notice: what happened, and why the person is being told (the body is the why, in the helper's words)."""
    headline = plain(title, 150)
    lines = [f"*{headline}*", f":mag: _Why you are seeing this:_ {plain(body, 500)}"]
    blocks: list[Block] = [{"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines)}}]
    foot = _who(helper) + (f" · open it at `{plain(route, 80)}`" if route else "")
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": foot}]})
    prefix = ":rotating_light: " if urgent else ""
    return f"{prefix}{headline}", blocks


def _preview(draft: str) -> Block:
    # rich_text_preformatted text is literal: no mention, link or markup in it is interpreted.
    return {
        "type": "rich_text",
        "elements": [{"type": "rich_text_preformatted", "elements": [{"type": "text", "text": draft}]}],
    }


def approval(  # noqa: PLR0913 - the parts of one message
    request_id: str, bound: str, action: str, helper: str, draft: str, link: str | None, expires_at: datetime
) -> tuple[str, list[Block]]:
    """A draft with Approve and Decline, bound to the digest of the exact arguments."""
    who = _who(helper)
    why = f"{who[:40]} will not do this until you say yes."
    blocks: list[Block] = [
        {"type": "header", "text": {"type": "plain_text", "text": f"{who[:60]} has a draft for you"}},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{plain(action, 150)}*\n:mag: _Why you are seeing this:_ {why}"},
        },
        _preview(draft),
    ]
    if link:
        blocks.append(
            {"type": "context", "elements": [{"type": "mrkdwn", "text": f"Full draft: `{plain(link, 200)}`"}]}
        )
    blocks += [
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Nothing goes out until you say so. Fingerprint `{bound[:12]}` · "
                    f"answer by {_clock(expires_at)} · only your click counts, not a reply or a reaction.",
                }
            ],
        },
        {
            "type": "actions",
            "block_id": f"hz-{request_id}",
            "elements": [
                {
                    "type": "button",
                    "action_id": APPROVE,
                    "style": "primary",
                    "text": {"type": "plain_text", "text": "Approve"},
                    "value": button_value(request_id, bound),
                },
                {
                    "type": "button",
                    "action_id": DECLINE,
                    "style": "danger",
                    "text": {"type": "plain_text", "text": "Decline"},
                    "value": button_value(request_id, bound),
                },
            ],
        },
    ]
    return f"{who[:60]} has a draft for you: {plain(action, 120)}", blocks


_ENDINGS = {
    "answered_approved": ":white_check_mark: *Approve* pressed at {at}, fingerprint `{fp}`. Handed to your helper.",
    "answered_declined": ":no_entry_sign: *Decline* pressed at {at}. The draft is shelved; nothing was sent.",
    "approved": ":white_check_mark: *Approved* at {at}. These exact words, fingerprint `{fp}`. Carrying on.",
    "declined": ":no_entry_sign: *Declined* at {at}. The draft is shelved; nothing was sent.",
    "expired": ":hourglass: *Expired* unanswered. Nothing was sent; ask again if it still matters.",
    "superseded": ":arrows_counterclockwise: *Replaced* by a newer draft. This one can no longer be approved.",
}


def settled(state: str, action: str, draft: str, bound: str, at: datetime) -> tuple[str, list[Block]]:
    """The same message once answered, expired or replaced: the draft stays, the buttons go."""
    ending = _ENDINGS[state].format(at=_clock(at), fp=bound[:12])
    blocks: list[Block] = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*{plain(action, 150)}*"}},
        _preview(draft),
        {"type": "context", "elements": [{"type": "mrkdwn", "text": ending}]},
    ]
    return f"{state.split('_')[-1].capitalize()}: {plain(action, 120)}", blocks
