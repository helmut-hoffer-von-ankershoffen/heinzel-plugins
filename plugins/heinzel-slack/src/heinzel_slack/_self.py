"""The self channel over Slack (ADR 0160): tell the signed-in person something, or ask them, in their own DM.

`notify_self` posts to the direct message between the person's private app and them (`slack.owner`), as a reply in
`thread` when given. `ask_self` posts the question with one button per option and waits, up to `timeout`, for the
first of: a click on one of those buttons by the owner (Slack Socket Mode: no public address), or a message the owner
types in the question's thread or, for a top-level question, in the DM after it (read by polling the Web API). Core
runs it in a worker and sets `cancel` when the question was answered elsewhere; the wait then ends within a fraction
of a second. Every exit closes the socket and takes the buttons off the message, in the background.

Socket Mode spreads one app's events over all its open connections, so a click may reach another listener of this
app, such as the approval job. Every listener therefore hands self-channel clicks to the shared local store
(`SlackService.dispatch`), and the waiting question reads them from there: no click is lost to a neighbour.
"""

import secrets
import threading
import time
from collections.abc import Callable, Sequence
from typing import Any

from heinzel import HeinzelError, clean_text

from heinzel_slack._chat import SlackChat, checked_ts, thread_ts, ts_key, url_of
from heinzel_slack._compat import (
    SELF_CONTEXT_LENGTH,
    SELF_OPTION_LENGTH,
    SELF_OPTIONS,
    SelfAnswer,
    SelfMessage,
)
from heinzel_slack._mrkdwn import MAX_ANSWER, MAX_TEXT, neutralise, readable
from heinzel_slack._service import SELF_ACTION, SlackService
from heinzel_slack._slack import Listener
from heinzel_slack._web import RateLimited, Web, obj, objs, text_of

MAX_QUESTION = 3_000
"""Longest question: Slack's limit for one section of a message with buttons."""
TICK = 0.2
"""How often a waiting question looks at the local store, the clock and `cancel`, in seconds."""
POLL_REQUEST = 5.0
"""Time limit of one reply read while a question waits, so `cancel` and the timeout are late by at most this."""


def options_of(options: Sequence[str]) -> list[str]:
    """The offered options, checked against Core's limits: at most ten, each non-blank, short and unique.

    Raises:
        HeinzelError: If they break a limit.
    """
    offered = list(options)
    if len(offered) > SELF_OPTIONS:
        msg = f"A question offers at most {SELF_OPTIONS} options"
        raise HeinzelError(msg)
    if any(not o.strip() or len(o) > SELF_OPTION_LENGTH for o in offered):
        msg = f"Each option needs a label of 1 to {SELF_OPTION_LENGTH} characters"
        raise HeinzelError(msg)
    if len(set(offered)) != len(offered):
        msg = "Each option must be different"
        raise HeinzelError(msg)
    return offered


def label_of(context: str | None) -> str:
    """A context label as shown: cleaned, one line, at most Core's length."""
    return " ".join(clean_text(context or "").split())[:SELF_CONTEXT_LENGTH]


def matched(text: str, offered: Sequence[str]) -> str | None:
    """The offered option a typed reply names exactly (case and spacing aside), or None."""
    wanted = " ".join(text.split()).casefold()
    return next((o for o in offered if " ".join(o.split()).casefold() == wanted), None)


class SlackSelf:
    """`notify_self` and `ask_self` in the owner's own Slack direct message."""

    def __init__(  # noqa: PLR0913 - collaborators, all replaceable in tests
        self,
        service: SlackService,
        web: Callable[[], Web],
        chat: SlackChat,
        listener: Callable[[], Listener | None],
        poll_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        poll_web: Callable[[], Web] | None = None,
    ) -> None:
        """Wrap the collaborators; nothing is sent. `listener` returns None when no app-level token is stored.

        `poll_web` reads replies while a question waits, with a short time limit per call; it defaults to `web`.
        """
        self._service = service
        self._web = web
        self._poll_web = poll_web or web
        self._chat = chat
        self._listener = listener
        self._poll = poll_seconds
        self._clock = clock
        self.closing: list[threading.Thread] = []

    def notify_self(self, text: str, *, thread: str | None = None, context: str | None = None) -> SelfMessage:
        """Post `text` to the owner's DM, as a reply in `thread` when given.

        Raises:
            HeinzelError: If the text is empty or too long, the thread is invalid, or Slack is not set up or refuses.
            SlackUnknown: If the post may or may not have happened.
        """
        body = self._body(text, context, MAX_TEXT)
        parent = thread_ts(thread)
        web, dm, base = self._target()
        ts = self._post(web, dm, body, None, parent)
        root = parent or ts
        return SelfMessage(id=ts, thread=root, url=url_of(base, dm, ts, parent))

    def ask_self(  # noqa: PLR0913 - Core's signature
        self,
        question: str,
        *,
        options: Sequence[str] = (),
        timeout: float,
        thread: str | None = None,
        context: str | None = None,
        cancel: threading.Event | None = None,
    ) -> SelfAnswer:
        """Ask the owner, with one button per option, and wait up to `timeout` seconds for a click or a typed reply.

        Returns a timed-out answer when nobody answered in time or `cancel` was set; never raises for that. The
        timeout counts from the call, connecting and posting included; a Slack call already under way when it passes
        or `cancel` is set ends within its own time limit (`slack.timeout` to post, 5 s for a reply read).

        Raises:
            HeinzelError: If the question or options break a limit, or Slack is not set up or refuses the post.
            SlackUnknown: If the post may or may not have happened.
        """
        deadline = self._clock() + max(0.0, timeout)
        offered = options_of(options)
        body = self._body(question, context, MAX_QUESTION)
        parent = thread_ts(thread)
        web, dm, _ = self._target()
        nonce = secrets.token_hex(8)
        team, owner = self._service.settings.team, self._service.settings.owner
        # Connect before posting, so a quick click already finds someone listening.
        listener = self._listener() if offered else None
        ts = ""
        answer = SelfAnswer(timed_out=True)
        try:
            if listener is not None:
                try:
                    listener.start(self._service.dispatch)
                except HeinzelError:
                    listener = None  # Socket Mode unavailable: typed replies still answer
            blocks = _question_blocks(body, offered, nonce, buttons=listener is not None)
            ts = self._post(web, dm, body, blocks, parent)
            root = parent or ts
            answer = self._wait(
                self._poll_web(),
                _Asked(dm, ts, root, team, owner, nonce, offered, top_level=parent is None),
                deadline,
                cancel,
            )
        finally:
            if listener is not None:
                listener.stop()
            if ts:
                self._service.store.take_clicks(ts)
        if offered:
            self._close(web, dm, ts, body, answer)
        return answer

    # --- internals -------------------------------------------------------

    def _body(self, text: str, context: str | None, limit: int) -> str:
        if not text.strip():
            msg = "There is nothing to say"
            raise HeinzelError(msg)
        label = label_of(context)
        body = (f"*{neutralise(label)}*\n" if label else "") + neutralise(text.strip())
        if len(body) > limit:
            msg = f"The message is longer than {limit} characters; shorten it"
            raise HeinzelError(msg)
        return body

    def _target(self) -> tuple[Web, str, str | None]:
        owner, _team = self._service.require_owner()
        web = self._web()
        base = self._chat.workspace(web)
        dm = text_of(obj(web.write("conversations.open", {"users": owner}).get("channel")).get("id"))
        if dm is None or not dm.startswith("D"):
            msg = "Slack did not open a direct message with the owner; refusing to post anywhere else"
            raise HeinzelError(msg)
        return web, dm, base

    def _post(self, web: Web, dm: str, body: str, blocks: list[dict[str, Any]] | None, parent: str | None) -> str:
        params: dict[str, Any] = {
            "channel": dm, "text": body, "unfurl_links": False, "unfurl_media": False, "link_names": False,
        }  # fmt: skip
        if blocks:
            params["blocks"] = blocks
        if parent:
            params["thread_ts"] = parent
        return checked_ts(web.write("chat.postMessage", params))

    def _wait(self, web: Web, asked: "_Asked", deadline: float, cancel: threading.Event | None) -> SelfAnswer:
        next_poll = self._clock() + self._poll
        while True:
            if cancel is not None and cancel.is_set():
                return SelfAnswer(thread=asked.root, timed_out=True)
            for click in self._service.store.take_clicks(asked.ts):
                option = asked.option(click)
                if option is not None:
                    return SelfAnswer(thread=asked.root, text=option, option=option)
            now = self._clock()
            if now >= deadline:
                return SelfAnswer(thread=asked.root, timed_out=True)
            if now >= next_poll:
                try:
                    typed = self._typed(web, asked)
                except RateLimited as limited:
                    next_poll = now + max(self._poll, limited.retry_after)
                except HeinzelError:
                    next_poll = now + self._poll  # a failed read is retried; the timeout still bounds the wait
                else:
                    if typed:
                        option = matched(typed, asked.offered)
                        return SelfAnswer(thread=asked.root, text=option or typed, option=option)
                    next_poll = now + self._poll
            wait = min(TICK, max(0.0, deadline - now))
            if cancel is not None:
                cancel.wait(wait)
            else:
                time.sleep(wait)

    def _typed(self, web: Web, asked: "_Asked") -> str:
        """The owner's first typed message after the question, in its thread or (top level) in the DM; or ''."""
        found: list[dict[str, Any]] = []
        replies = web.read(
            "conversations.replies", {"channel": asked.dm, "ts": asked.root, "oldest": asked.ts}, wait=False
        )
        found.extend(objs(replies.get("messages")))
        if asked.top_level:
            later = web.read(
                "conversations.history", {"channel": asked.dm, "oldest": asked.ts, "limit": 50}, wait=False
            )
            found.extend(m for m in objs(later.get("messages")) if m.get("thread_ts") in {None, m.get("ts")})
        after = ts_key(asked.ts)
        for message in sorted((m for m in found if asked.by_owner(m, after)), key=lambda m: ts_key(str(m["ts"]))):
            text = readable(str(message.get("text", "")), lambda _user: None).strip()[:MAX_ANSWER]
            if text:
                return text
        return ""

    def _close(self, web: Web, dm: str, ts: str, body: str, answer: SelfAnswer) -> None:
        """Take the buttons off the question, in the background: a stale button must not look answerable."""
        if answer.timed_out:
            note = "No answer here in time, or it was answered elsewhere."
        elif answer.option is not None:
            note = f"Answered: {neutralise(answer.option)}"
        else:
            note = "Answered in a reply."

        def close() -> None:
            blocks = [
                {"type": "section", "text": {"type": "mrkdwn", "text": body}},
                {"type": "context", "elements": [{"type": "mrkdwn", "text": note}]},
            ]
            try:
                web.write("chat.update", {"channel": dm, "ts": ts, "text": body, "blocks": blocks})
            except Exception:  # noqa: BLE001, S110 - best effort by design; the answer is already returned
                pass

        self.closing = [thread for thread in self.closing if thread.is_alive()]
        thread = threading.Thread(target=close, name="slack-self-close", daemon=True)
        self.closing.append(thread)
        thread.start()


class _Asked:
    """One posted question: where it is, whose click counts, and which buttons it carries."""

    def __init__(  # noqa: PLR0913 - one value object
        self, dm: str, ts: str, root: str, team: str, owner: str, nonce: str, offered: list[str], *, top_level: bool
    ) -> None:
        self.dm, self.ts, self.root, self.team, self.owner = dm, ts, root, team, owner
        self.nonce, self.offered, self.top_level = nonce, offered, top_level

    def option(self, click: tuple[str, str, str, str]) -> str | None:
        """The option a stored click chose, if it is the owner's click on this very message; otherwise None."""
        team, user, channel, value = click
        if (team, user, channel) != (self.team, self.owner, self.dm):
            return None
        version, _, rest = value.partition(":")
        nonce, _, index = rest.partition(":")
        if version != "self1" or not secrets.compare_digest(nonce, self.nonce) or not index.isdigit():
            return None
        number = int(index)
        return self.offered[number] if number < len(self.offered) else None

    def by_owner(self, message: dict[str, Any], after: tuple[int, int]) -> bool:
        """Whether a listed message is something the owner typed after the question."""
        ts = message.get("ts")
        return (
            isinstance(ts, str)
            and message.get("user") == self.owner
            and not message.get("bot_id")
            and message.get("subtype") is None
            and ts_key(ts) > after
        )


def _question_blocks(body: str, offered: list[str], nonce: str, *, buttons: bool) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = [{"type": "section", "text": {"type": "mrkdwn", "text": body}}]
    if offered and buttons:
        blocks.append(
            {
                "type": "actions",
                "block_id": f"hz_self_{nonce}",
                "elements": [
                    {
                        "type": "button",
                        "action_id": f"{SELF_ACTION}{index}",
                        "text": {"type": "plain_text", "text": clean_text(option), "emoji": False},
                        "value": f"self1:{nonce}:{index}",
                    }
                    for index, option in enumerate(offered)
                ],
            }
        )
        hint = "Or reply in this thread."
    elif offered:
        hint = "Reply in this thread with one of: " + ", ".join(neutralise(o) for o in offered)
    else:
        hint = "Reply in this thread."
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": hint}]})
    return blocks
