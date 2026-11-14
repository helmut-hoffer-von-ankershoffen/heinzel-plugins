"""The self channel (ADR 0160) on a fake Web API and a fake Socket Mode: notify, ask, click, reply, timeout, cancel."""

import threading
import time
from typing import Any

import pytest
from heinzel import HeinzelError

from heinzel_slack import SlackSettings
from heinzel_slack._chat import SlackChat
from heinzel_slack._self import SlackSelf
from heinzel_slack._slack import SlackRefused
from heinzel_slack._web import Web
from tests.conftest import DM, OTHER, OWNER, TEAM, FakeSocket, FakeWeb

pytestmark = pytest.mark.integration
T = 1761912000


class Self:
    """A `SlackSelf` on the rig's service, a fake Web API and a fake socket (None: no app-level token)."""

    def __init__(self, rig, fake: FakeWeb | None = None, socket: FakeSocket | None = None, *, token: bool = True):
        self.rig, self.fake, self.socket = rig, fake or FakeWeb(), socket or FakeSocket()
        web = Web(self.fake, sleep=lambda _s: None)
        self.adapter = SlackSelf(
            rig.service, lambda: web, SlackChat(lambda: web, TEAM), lambda: self.socket if token else None, 0.05
        )

    def ask(self, question="Ship it?", **kw: Any):
        answer = self.adapter.ask_self(question, **{"timeout": 5.0, **kw})
        for thread in self.adapter.closing:
            thread.join(2)
        return answer

    def posted(self) -> dict[str, Any]:
        return self.fake.made("chat.postMessage")[-1]

    def value(self, index: int) -> str:
        return self.posted()["blocks"][1]["elements"][index]["value"]


def click(ts: str, value: str, *, user: str = OWNER, team: str = TEAM, channel: str = DM, action: str = "hz_self_0"):
    return {
        "type": "block_actions", "team": {"id": team}, "user": {"id": user},
        "container": {"type": "message", "message_ts": ts, "channel_id": channel},
        "actions": [{"type": "button", "action_id": action, "value": value}],
    }  # fmt: skip


def after_post(rig_self: Self, then):
    """Answer `chat.postMessage` like Slack, then run `then(ts)` on another thread, as a person would."""
    fake = rig_self.fake

    def post(params):
        fake.posted += 1
        ts = f"{T + fake.posted}.000100"
        threading.Timer(0.05, then, args=(ts,)).start()
        return {"ok": True, "ts": ts, "channel": params["channel"]}

    fake.handlers["chat.postMessage"] = post


def test_notify_self_posts_to_the_owners_dm_and_starts_a_thread(rig):
    s = Self(rig)
    first = s.adapter.notify_self("Build done <!here>", context="CI")
    sent = s.posted()
    assert sent["channel"] == DM and "thread_ts" not in sent
    assert sent["text"] == "*CI*\nBuild done &lt;!here&gt;"
    assert first.thread == first.id == f"{T + 1}.000100"
    assert first.url == f"https://acme.slack.com/archives/{DM}/p{T + 1}000100"
    assert s.fake.made("conversations.open") == [{"users": OWNER}]
    second = s.adapter.notify_self("And deployed", thread=first.thread)
    assert s.posted()["thread_ts"] == first.thread
    assert (second.thread, second.id) == (first.thread, f"{T + 2}.000100")


def test_notify_self_refuses_a_dm_that_is_no_dm(rig):
    s = Self(rig, FakeWeb({"conversations.open": lambda _p: {"ok": True, "channel": {"id": "C0PUBLIC01"}}}))
    with pytest.raises(HeinzelError, match="refusing to post anywhere else"):
        s.adapter.notify_self("hi")
    assert s.fake.made("chat.postMessage") == []


def test_notify_self_needs_an_owner(rig, monkeypatch):
    monkeypatch.setattr(rig.service, "_settings", SlackSettings(team=TEAM, bot_enabled=True))
    with pytest.raises(HeinzelError, match="hz setup slack"):
        Self(rig).adapter.notify_self("hi")


def test_a_button_click_by_the_owner_answers_and_nothing_else_does(rig):
    s = Self(rig)

    def clicks(ts):
        good = s.value(1)
        nonce = good.split(":")[1]
        s.socket.push(click(ts, good, user=OTHER))  # someone else
        s.socket.push(click(ts, good, team="T0ELSEWHE1"))  # another workspace
        s.socket.push(click(ts, good, channel="D0ELSEWHE1"))  # another conversation
        s.socket.push(click(f"{T}.000001", good))  # another message
        s.socket.push(click(ts, f"self1:{'0' * len(nonce)}:1"))  # a forged button
        s.socket.push(click(ts, f"self1:{nonce}:7"))  # no such option
        s.socket.push(click(ts, good, action="hz_self_1"))  # the owner's real click

    after_post(s, clicks)
    answer = s.ask("Ship <!channel> it?", options=["Yes", "No"], context="Release")
    assert (answer.option, answer.text, answer.timed_out) == ("No", "No", False)
    assert answer.thread == f"{T + 1}.000100"
    blocks = s.fake.made("chat.postMessage")[0]["blocks"]
    assert blocks[0]["text"]["text"] == "*Release*\nShip &lt;!channel&gt; it?"
    assert [b["text"]["text"] for b in blocks[1]["elements"]] == ["Yes", "No"]
    assert (s.socket.started, s.socket.stopped) == (1, 1)
    (update,) = s.fake.made("chat.update")
    assert not any(b["type"] == "actions" for b in update["blocks"])
    assert "Answered: No" in str(update["blocks"])
    assert rig.service.store.take_clicks(answer.thread or "") == []  # nothing left behind


def test_a_typed_reply_in_the_thread_answers(rig):
    replies: list[dict[str, Any]] = []
    fake = FakeWeb(
        {
            "conversations.replies": lambda _p: {"ok": True, "messages": list(replies)},
            "conversations.history": lambda _p: {"ok": True, "messages": []},
        }
    )
    s = Self(rig, fake)

    def reply(ts):
        replies.extend(
            [
                {"ts": ts, "user": "U0BOT0001", "bot_id": "B0BOT", "text": "Ship it?"},
                {"ts": f"{T + 1}.000200", "user": OTHER, "text": "not me"},
                {"ts": f"{T + 1}.000300", "user": OWNER, "bot_id": "B0X", "text": "a bot as me"},
                {"ts": f"{T + 1}.000400", "user": OWNER, "subtype": "message_changed", "text": "edited"},
                {"ts": f"{T + 1}.000500", "user": OWNER, "text": "Later, <@U0ADA0001>‮ please"},
            ]
        )

    after_post(s, reply)
    answer = s.ask(options=["Yes", "No"])
    assert (answer.text, answer.option, answer.timed_out) == ("Later, @someone please", None, False)
    assert fake.made("conversations.replies")[0] == {
        "channel": DM,
        "ts": f"{T + 1}.000100",
        "oldest": f"{T + 1}.000100",
    }
    assert s.socket.stopped == 1


def test_a_typed_reply_naming_an_option_chooses_it_and_a_top_level_dm_message_counts(rig):
    later: list[dict[str, Any]] = []
    fake = FakeWeb(
        {
            "conversations.replies": lambda _p: {"ok": True, "messages": []},
            "conversations.history": lambda _p: {"ok": True, "messages": list(later)},
        }
    )
    s = Self(rig, fake)
    after_post(s, lambda ts: later.append({"ts": f"{T + 2}.0", "user": OWNER, "text": "  no  "}))
    answer = s.ask(options=["Yes", "No"])
    assert (answer.text, answer.option) == ("No", "No")


def test_in_a_thread_only_the_thread_is_read(rig):
    fake = FakeWeb({"conversations.replies": lambda _p: {"ok": True, "messages": []}})
    s = Self(rig, fake)
    answer = s.ask(thread=f"{T}.000100", timeout=0.3)
    assert answer.timed_out and answer.thread == f"{T}.000100"
    assert s.posted()["thread_ts"] == f"{T}.000100"
    assert {p["ts"] for p in fake.made("conversations.replies")} == {f"{T}.000100"}
    assert fake.made("conversations.history") == []


def test_no_answer_in_time_is_a_timed_out_answer(rig):
    fake = FakeWeb({"conversations.replies": lambda _p: {"ok": True, "messages": []},
                    "conversations.history": lambda _p: {"ok": True, "messages": []}})  # fmt: skip
    s = Self(rig, fake)
    started = time.monotonic()
    answer = s.ask(options=["Yes"], timeout=0.4)
    assert answer.timed_out and answer.text == "" and answer.option is None
    assert answer.thread == f"{T + 1}.000100"
    assert 0.4 <= time.monotonic() - started < 3
    assert (s.socket.started, s.socket.stopped) == (1, 1)
    assert "No answer here in time" in str(fake.made("chat.update")[0]["blocks"])


def test_cancel_ends_the_wait_promptly_and_closes_the_socket(rig):
    fake = FakeWeb({"conversations.replies": lambda _p: {"ok": True, "messages": []},
                    "conversations.history": lambda _p: {"ok": True, "messages": []}})  # fmt: skip
    s = Self(rig, fake)
    cancel = threading.Event()
    threading.Timer(0.2, cancel.set).start()
    started = time.monotonic()
    answer = s.ask(options=["Yes"], timeout=60, cancel=cancel)
    assert answer.timed_out
    assert time.monotonic() - started < 2
    assert (s.socket.started, s.socket.stopped) == (1, 1)


def test_a_failed_post_still_closes_the_socket(rig):
    def refuse(_params):
        raise SlackRefused("Slack refused chat.postMessage (channel_not_found).")

    s = Self(rig, FakeWeb({"chat.postMessage": refuse}))
    with pytest.raises(SlackRefused):
        s.ask(options=["Yes"])
    assert (s.socket.started, s.socket.stopped) == (1, 1)


def test_rate_limited_polling_keeps_waiting_within_the_timeout(rig):
    fake = FakeWeb({"conversations.replies": lambda _p: {"ok": True, "messages": []},
                    "conversations.history": lambda _p: {"ok": True, "messages": []}})  # fmt: skip
    fake.limited["conversations.replies"] = [0.1] * 50
    assert Self(rig, fake).ask(timeout=0.3).timed_out


def test_failing_reads_keep_waiting_within_the_timeout(rig):
    def broken(_params):
        raise HeinzelError("Slack did not answer conversations.replies (TimeoutError)")

    assert Self(rig, FakeWeb({"conversations.replies": broken})).ask(timeout=0.3).timed_out


def test_without_an_app_token_options_are_listed_and_a_reply_names_one(rig):
    replies: list[dict[str, Any]] = []
    fake = FakeWeb({"conversations.replies": lambda _p: {"ok": True, "messages": list(replies)},
                    "conversations.history": lambda _p: {"ok": True, "messages": []}})  # fmt: skip
    s = Self(rig, fake, token=False)
    after_post(s, lambda _ts: replies.append({"ts": f"{T + 3}.0", "user": OWNER, "text": "yes"}))
    answer = s.ask(options=["Yes", "No"])
    assert (answer.option, answer.text) == ("Yes", "Yes")
    blocks = fake.made("chat.postMessage")[0]["blocks"]
    assert not any(b["type"] == "actions" for b in blocks)
    assert "one of: Yes, No" in str(blocks)
    assert s.socket.started == 0


def test_a_socket_that_cannot_connect_falls_back_to_replies(rig):
    fake = FakeWeb({"conversations.replies": lambda _p: {"ok": True, "messages": []},
                    "conversations.history": lambda _p: {"ok": True, "messages": []}})  # fmt: skip
    s = Self(rig, fake, FakeSocket(fail=True))
    assert s.ask(options=["Yes"], timeout=0.2).timed_out
    assert not any(b["type"] == "actions" for b in fake.made("chat.postMessage")[0]["blocks"])


def test_a_click_that_reached_another_listener_still_answers(rig):
    """Socket Mode spreads events over an app's connections: the approval job may get the click."""
    s = Self(rig)
    after_post(s, lambda ts: rig.service.dispatch(click(ts, s.value(0))))
    assert s.ask(options=["Yes", "No"]).option == "Yes"


def test_an_approval_click_on_the_questions_socket_still_decides_the_draft(rig):
    ref = rig.post().reference
    s = Self(rig)
    after_post(s, lambda _ts: s.socket.push(rig.click(ref)))
    assert s.ask(timeout=0.5, options=["Yes"]).timed_out
    assert rig.service.outcome("req-1").state == "approved"


@pytest.mark.parametrize(
    ("options", "match"),
    [
        ([str(i) for i in range(11)], "at most"),
        (["Yes", "Yes"], "different"),
        (["x" * 76], "characters"),
        ([" "], "1 to"),
    ],
)
def test_options_beyond_cores_limits_are_refused_before_posting(rig, options, match):
    s = Self(rig)
    with pytest.raises(HeinzelError, match=match):
        s.ask(options=options)
    assert s.fake.calls == [] and s.socket.started == 0


def slow_slack(rig, retry_after: float) -> SlackSelf:
    """A self channel whose reply reads are always rate limited, with the real sleep the adapter wires."""
    fake = FakeWeb()
    fake.limited["conversations.replies"] = [retry_after] * 50
    web = Web(fake)  # real time.sleep
    return SlackSelf(rig.service, lambda: web, SlackChat(lambda: web, TEAM), FakeSocket, 0.05)


def test_the_timeout_bounds_the_wait_even_when_slack_rate_limits_with_the_real_sleep(rig):
    started = time.monotonic()
    assert slow_slack(rig, 4.0).ask_self("Ship it?", options=["Yes"], timeout=0.5).timed_out
    assert time.monotonic() - started < 1.5


def test_cancel_ends_the_wait_even_when_slack_rate_limits_with_the_real_sleep(rig):
    cancel = threading.Event()
    threading.Timer(0.3, cancel.set).start()
    started = time.monotonic()
    assert slow_slack(rig, 4.0).ask_self("Ship it?", options=["Yes"], timeout=30, cancel=cancel).timed_out
    assert time.monotonic() - started < 1.5


def test_a_cancel_before_the_post_still_posts_once_and_returns_at_once(rig):
    cancel = threading.Event()
    cancel.set()
    s = Self(rig)
    started = time.monotonic()
    assert s.ask(options=["Yes"], timeout=30, cancel=cancel).timed_out
    assert time.monotonic() - started < 1.5
    assert len(s.fake.made("chat.postMessage")) == 1


@pytest.mark.parametrize("action", ["hz_self_0", "hz_self_approve", "hz_selfx"])
def test_a_draft_click_relabelled_as_a_self_button_never_approves(rig, action):
    ref = rig.post().reference
    rig.service.dispatch(rig.click(ref, action=action))
    forged = rig.click(ref)
    forged["actions"][0]["value"] = "self1:abcd:0"
    rig.service.dispatch(forged)
    mixed = rig.click(ref)
    mixed["actions"] = [dict(mixed["actions"][0], action_id=action), mixed["actions"][0]]
    rig.service.dispatch(mixed)
    assert rig.service.outcome("req-1").state == "pending"
    assert rig.channel.replies([ref]) == []
