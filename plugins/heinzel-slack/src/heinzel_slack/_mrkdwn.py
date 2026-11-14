"""Slack's message markup, both ways: what we post cannot page anyone, and what we read shows names, not ids.

Outbound, every `&`, `<` and `>` is escaped as Slack documents, so no `<!channel>`, `<!here>`, `<@U…>` or
`<!subteam^…>` in a draft becomes a mention; bare `@here`, `@channel` and `@everyone` get a full-width at sign, so
they stay inert even where a client resolves plain names. Inbound text is untrusted data from other people: mentions
and links become plain names and addresses, and the result passes Core's `clean_text` like every adapter string.
"""

import re
from collections.abc import Callable

from heinzel import clean_text

MAX_TEXT = 40_000
"""Slack's limit for a message's text; longer drafts are refused rather than cut."""
MAX_ANSWER = 32_000
"""Longest typed answer handed to Core (Core's own cap for a self-channel answer)."""

_BROADCAST = re.compile(r"(?<![\w.])@(here|channel|everyone)\b", re.IGNORECASE)
_TOKEN = re.compile(r"<([^<>\n]{1,2000})>")
_ENTITIES = (("&lt;", "<"), ("&gt;", ">"), ("&amp;", "&"))


def neutralise(text: str) -> str:
    """`text` for Slack's `text` field: plain words and Markdown kept, every mention and broadcast made inert."""
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return _BROADCAST.sub("\uff20\\1", escaped)


def _token(inner: str, name_of: Callable[[str], str | None]) -> str:  # noqa: PLR0911 - one return per markup kind
    target, _, label = inner.partition("|")
    if target.startswith("@"):
        return "@" + (label.lstrip("@") or name_of(target[1:]) or "someone")
    if target.startswith("#"):
        return "#" + (label or "channel")
    if target.startswith("!"):
        word = target[1:].split("^", 1)[0]
        if word in {"here", "channel", "everyone"}:
            return f"@{word}"
        if word == "subteam":
            return label if label.startswith("@") else "@" + (label or "group")
        return label
    if label and label != target:
        return f"{label} ({target})"
    return target


def readable(text: str, name_of: Callable[[str], str | None]) -> str:
    """Slack message markup as plain text: mentions as names, links as label and address, entities decoded.

    `name_of` maps a member id to a display name, or None when it is not known. Returns clean text: no control,
    invisible or bidirectional character (Core's `clean_text`). What it says is still data, never an instruction.
    """
    rendered = _TOKEN.sub(lambda match: _token(match.group(1), name_of), text)
    for entity, char in _ENTITIES:
        rendered = rendered.replace(entity, char)
    return clean_text(rendered)
