"""Core's `chat` capability over the Slack Web API: read a channel's messages in a window, post to a channel.

Channels are public channels the app's bot user is a member of, named by id (`C…`) or `#name`; direct messages and
group chats are out of the capability's scope and refused. Everything read is untrusted: text, names and labels pass
through `readable` (Core's `clean_text` included), and mentions come back as names, never raw ids. Everything posted
is neutralised first, so a draft cannot page a channel.

Slack lists a channel's top-level messages by time and a thread's replies per thread. A reply in the window is found
when its thread's first message is in the window too; a reply to a thread started before the window is not, because
Slack's bot API offers no time-ordered list of replies.
"""

import re
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from heinzel import HeinzelError, Message, Participant, PostedMessage, Window, clean_text

from heinzel_slack._mrkdwn import MAX_TEXT, neutralise, readable
from heinzel_slack._slack import SlackUnknown
from heinzel_slack._web import Web, obj, text_of

MAX_MESSAGES = 5_000
"""Messages read for one window before asking for a narrower one."""
MAX_CHARS = 2_000_000
"""Characters of message text read for one window before asking for a narrower one."""
_CHANNEL_ID = re.compile(r"C[A-Z0-9]{6,20}")
_CHANNEL_NAME = re.compile(r"#[a-z0-9][a-z0-9_-]{0,79}")
_TS = re.compile(r"([0-9]{1,12})\.([0-9]{1,6})")
_WORKSPACE_URL = re.compile(r"https://[a-z0-9-]{1,63}(?:\.enterprise)?\.slack\.com/")
_SKIPPED_SUBTYPES = frozenset({"channel_join", "channel_leave", "channel_topic", "channel_purpose", "channel_name"})


def ts_key(ts: str) -> tuple[int, int]:
    """A Slack `ts` as a sortable pair of seconds and microseconds.

    Raises:
        HeinzelError: If it is not a Slack timestamp.
    """
    match = _TS.fullmatch(ts)
    if match is None:
        msg = "Slack returned an invalid message timestamp"
        raise HeinzelError(msg)
    return int(match.group(1)), int(match.group(2).ljust(6, "0"))


def thread_ts(thread: str | None) -> str | None:
    """A caller's thread handle as a Slack `ts`, or None.

    Raises:
        HeinzelError: If it is not a Slack message timestamp.
    """
    if thread is None:
        return None
    if _TS.fullmatch(thread.strip()) is None:
        msg = "A Slack thread is the timestamp id of its first message, like 1761912000.000100"
        raise HeinzelError(msg)
    return thread.strip()


def checked_ts(reply: dict[str, Any]) -> str:
    """The `ts` of a message Slack just posted.

    Raises:
        SlackUnknown: If the acknowledgement does not name one; the post may have happened.
    """
    ts = reply.get("ts")
    if not isinstance(ts, str) or _TS.fullmatch(ts) is None:
        msg = "Slack returned an ambiguous message acknowledgement; do not retry"
        raise SlackUnknown(msg)
    return ts


def _when(ts: str) -> datetime:
    seconds, micros = ts_key(ts)
    return datetime.fromtimestamp(seconds, UTC).replace(microsecond=micros)


class SlackChat:
    """`Chat.messages` and `Chat.post` for channels the bot user is in."""

    def __init__(self, web: Callable[[], Web], team: str) -> None:
        """Wrap a Web API factory (called per operation, so a replaced token is used); nothing is sent."""
        self._web = web
        self._team = team
        self._lock = threading.Lock()
        self._base: str | None = None

    def messages(self, channel: str, window: Window) -> list[Message]:
        """Messages in `channel` within `window`, top-level or reply, oldest first.

        Raises:
            HeinzelError: If the window is backwards or too full, the channel is unknown, or Slack fails.
        """
        if window.since > window.until:
            msg = f"The window starts ({window.since.isoformat()}) after it ends ({window.until.isoformat()})."
            raise HeinzelError(msg)
        web = self._web()
        base = self.workspace(web)
        cid = self._resolve(web, channel)
        names: dict[str, str | None] = {}
        found: dict[str, Message] = {}
        budget = [MAX_CHARS]
        since, until = window.since.timestamp(), window.until.timestamp()
        history = {"channel": cid, "oldest": f"{since:.6f}", "latest": f"{until:.6f}", "inclusive": "true"}
        for item in web.pages("conversations.history", history, "messages"):
            message = self._message(web, cid, item, base, names, window, budget)
            if message is None:
                continue
            found[message.id] = message
            if message.reply_count:
                replies = {"channel": cid, "ts": message.id, "oldest": f"{since:.6f}", "inclusive": "true"}
                for reply in web.pages("conversations.replies", replies, "messages"):
                    answer = self._message(web, cid, reply, base, names, window, budget)
                    if answer is not None and answer.id != message.id:
                        found[answer.id] = answer
            if len(found) > MAX_MESSAGES:
                break
        if len(found) > MAX_MESSAGES:
            msg = f"{cid} has more than {MAX_MESSAGES} messages in this window; ask for a narrower window."
            raise HeinzelError(msg)
        return sorted(found.values(), key=lambda m: ts_key(m.id))

    def post(self, channel: str, text: str, thread: str | None = None) -> PostedMessage:
        """Post `text` to `channel`, in `thread` when given, with every mention neutralised.

        Raises:
            HeinzelError: If the text is empty or too long, the channel or thread is invalid, or Slack refuses.
            SlackUnknown: If the post may or may not have happened; never retry it blindly.
        """
        if not text.strip():
            msg = "There is nothing to post"
            raise HeinzelError(msg)
        body = neutralise(text)
        if len(body) > MAX_TEXT:
            msg = f"The message is longer than Slack's {MAX_TEXT} characters; shorten it"
            raise HeinzelError(msg)
        parent = thread_ts(thread)
        web = self._web()
        base = self.workspace(web)
        cid = self._resolve(web, channel)
        params: dict[str, Any] = {
            "channel": cid, "text": body, "unfurl_links": False, "unfurl_media": False, "link_names": False,
        }  # fmt: skip
        if parent:
            params["thread_ts"] = parent
        reply = web.write("chat.postMessage", params)
        ts = checked_ts(reply)
        if reply.get("channel") != cid:
            msg = "Slack acknowledged the message for another channel; do not retry"
            raise SlackUnknown(msg)
        return PostedMessage(channel=cid, id=ts, thread=parent, url=url_of(base, cid, ts, parent))

    def workspace(self, web: Web) -> str | None:
        """The workspace's web address (from `auth.test`) once its id matched `slack.team`; cached per adapter.

        Raises:
            HeinzelError: If the token belongs to another workspace.
        """
        with self._lock:
            if self._base is not None:
                return self._base or None
        who = web.read("auth.test", {})
        if self._team and who.get("team_id") != self._team:
            msg = "The bot token belongs to another workspace than slack.team; refusing to use it"
            raise HeinzelError(msg)
        url = who.get("url")
        base = url if isinstance(url, str) and _WORKSPACE_URL.fullmatch(url) else ""
        with self._lock:
            self._base = base
        return base or None

    def _resolve(self, web: Web, channel: str) -> str:
        wanted = channel.strip()
        if _CHANNEL_ID.fullmatch(wanted):
            return wanted
        if not _CHANNEL_NAME.fullmatch(wanted):
            msg = (
                "A channel is a public channel id like C01ABCDEF or a #name; private channels and DMs are out of scope"
            )
            raise HeinzelError(msg)
        listing = {"types": "public_channel", "exclude_archived": "true"}
        for item in web.pages("conversations.list", listing, "channels"):
            cid = item.get("id")
            if item.get("name") == wanted[1:] and isinstance(cid, str) and _CHANNEL_ID.fullmatch(cid):
                return cid
        msg = f"No public channel {wanted} in this workspace"
        raise HeinzelError(msg)

    def _message(  # noqa: PLR0913 - one mapping, every input independent
        self,
        web: Web,
        cid: str,
        item: dict[str, Any],
        base: str | None,
        names: dict[str, str | None],
        window: Window,
        budget: list[int],
    ) -> Message | None:
        ts = item.get("ts")
        if not isinstance(ts, str) or item.get("subtype") in _SKIPPED_SUBTYPES:
            return None
        posted = _when(ts)
        if not window.since <= posted < window.until:
            return None
        raw = item.get("text")
        text = readable(raw if isinstance(raw, str) else "", lambda user: self._name(web, user, names))
        budget[0] -= len(text)
        if budget[0] < 0:
            msg = f"{cid} has more than {MAX_CHARS} characters of messages in this window; ask for a narrower window."
            raise HeinzelError(msg)
        parent = item.get("thread_ts")
        thread = parent if isinstance(parent, str) and parent != ts and _TS.fullmatch(parent) else None
        count = item.get("reply_count")
        return Message(
            channel=cid,
            id=ts,
            author=Participant(name=self._author(web, item, names)),
            posted_at=posted,
            text=text,
            thread=thread,
            reply_count=count if isinstance(count, int) and count > 0 and thread is None else 0,
            url=url_of(base, cid, ts, thread),
        )

    def _author(self, web: Web, item: dict[str, Any], names: dict[str, str | None]) -> str | None:
        user = item.get("user")
        if isinstance(user, str) and user:
            return self._name(web, user, names)
        label = text_of(obj(item.get("bot_profile")).get("name")) or text_of(item.get("username"))
        return (clean_text(label)[:200] or None) if label else None

    def _name(self, web: Web, user: str, names: dict[str, str | None]) -> str | None:
        if not re.fullmatch(r"[UWB][A-Z0-9]{6,20}", user):
            return None
        if user not in names:
            try:
                profile = obj(web.read("users.info", {"user": user}).get("user"))
            except HeinzelError:
                profile = {}
            label = (
                text_of(obj(profile.get("profile")).get("display_name"))
                or text_of(profile.get("real_name"))
                or text_of(profile.get("name"))
            )
            names[user] = (clean_text(label)[:200] or None) if label else None
        return names[user]


def url_of(base: str | None, cid: str, ts: str, thread: str | None) -> str | None:
    """Where people open a message, from the workspace address; None when that is unknown."""
    if not base:
        return None
    seconds, micros = ts_key(ts)
    link = f"{base}archives/{cid}/p{seconds}{micros:06d}"
    return f"{link}?thread_ts={thread}&cid={cid}" if thread else link
