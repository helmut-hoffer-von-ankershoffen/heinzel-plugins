"""The `chat` capability on a fake Slack Web API: mapping, pagination, threads, neutralising, rate limits."""

from datetime import UTC, datetime

import pytest
from heinzel import HeinzelError, Window

from heinzel_slack._chat import MAX_MESSAGES, SlackChat
from heinzel_slack._slack import SlackUnknown
from heinzel_slack._web import MAX_ATTEMPTS, RateLimited, Web
from tests.conftest import TEAM, FakeWeb

pytestmark = pytest.mark.integration
CHAN = "C0CHAN0001"
T = 1761912000  # 2025-10-31T12:00:00Z
WINDOW = Window(since=datetime.fromtimestamp(T, UTC), until=datetime.fromtimestamp(T + 3600, UTC))


def chat_on(fake: FakeWeb, sleeps: list[float] | None = None, team: str = TEAM) -> SlackChat:
    web = Web(fake, sleep=(sleeps.append if sleeps is not None else lambda _s: None))
    return SlackChat(lambda: web, team)


def history(*pages):
    """A paginated `conversations.history`: each page a list of messages."""

    def handler(params):
        index = int(params.get("cursor") or 0)
        more = index + 1 < len(pages)
        return {
            "ok": True,
            "messages": pages[index],
            "response_metadata": {"next_cursor": str(index + 1) if more else ""},
        }

    return handler


USERS = {
    "users.info": lambda p: {
        "ok": True,
        "user": {
            "name": "ada",
            "real_name": "Ada L",
            "profile": {"display_name": {"U0ADA0001": "Ada"}.get(p["user"], "")},
        },
    }
}


def test_messages_map_pages_threads_names_and_links():
    fake = FakeWeb({
        **USERS,
        "conversations.history": history(
            [{"ts": f"{T + 10}.000200", "user": "U0ADA0001", "text": "hi <@U0ADA0001> <!here>", "reply_count": 2,
              "thread_ts": f"{T + 10}.000200"}],
            [{"ts": f"{T - 5}.000000", "user": "U0ADA0001", "text": "before"},
             {"ts": f"{T + 20}.000000", "bot_profile": {"name": "CI‮bot"}, "text": "built", "subtype": "bot_message"},
             {"ts": f"{T + 30}.000000", "user": "U0ADA0001", "subtype": "channel_join", "text": "joined"}],
        ),
        "conversations.replies": lambda _p: {"ok": True, "messages": [
            {"ts": f"{T + 10}.000200", "user": "U0ADA0001", "text": "parent again", "thread_ts": f"{T + 10}.000200"},
            {"ts": f"{T + 15}.5", "user": "U0BOB0002", "text": "reply", "thread_ts": f"{T + 10}.000200"},
            {"ts": f"{T + 7200}.0", "user": "U0BOB0002", "text": "after the window", "thread_ts": f"{T + 10}.000200"},
        ]},
    })  # fmt: skip
    found = chat_on(fake).messages(CHAN, WINDOW)
    assert [m.text for m in found] == ["hi @Ada @here", "reply", "built"]
    parent, reply, bot = found
    assert (parent.thread, parent.reply_count, parent.author.name) == (None, 2, "Ada")
    assert parent.url == f"https://acme.slack.com/archives/{CHAN}/p{T + 10}000200"
    assert (reply.thread, reply.reply_count, reply.author.name) == (f"{T + 10}.000200", 0, "Ada L")
    assert reply.url == f"https://acme.slack.com/archives/{CHAN}/p{T + 15}500000?thread_ts={T + 10}.000200&cid={CHAN}"
    assert reply.posted_at == datetime.fromtimestamp(T + 15.5, UTC)
    assert bot.author.name == "CIbot" and bot.author.email is None
    assert [p.get("cursor") for p in fake.made("conversations.history")] == [None, "1"]
    first = fake.made("conversations.history")[0]
    assert (first["oldest"], first["latest"], first["limit"]) == (f"{T}.000000", f"{T + 3600}.000000", 200)


def test_a_channel_name_is_resolved_across_pages():
    pages = [[{"id": "C0OTHER001", "name": "random"}], [{"id": CHAN, "name": "general"}]]
    fake = FakeWeb({"conversations.list": history(*pages), "conversations.history": history([])})
    fake.handlers["conversations.list"] = lambda p: {
        "ok": True, "channels": pages[int(p.get("cursor") or 0)],
        "response_metadata": {"next_cursor": "" if p.get("cursor") else "1"},
    }  # fmt: skip
    assert chat_on(fake).messages("#general", WINDOW) == []
    assert fake.made("conversations.history")[0]["channel"] == CHAN
    with pytest.raises(HeinzelError, match="No public channel #missing"):
        chat_on(fake).messages("#missing", WINDOW)


@pytest.mark.parametrize("channel", ["D0DM000001", "G0PRIVATE1", "general", "#Bad Name", "U0ADA0001", ""])
def test_direct_messages_and_odd_names_are_refused_before_any_read(channel):
    fake = FakeWeb()
    with pytest.raises(HeinzelError, match="channel id"):
        chat_on(fake).messages(channel, WINDOW)
    assert [c[0] for c in fake.calls] == ["auth.test"]


def test_a_token_of_another_workspace_is_refused():
    fake = FakeWeb({"conversations.history": history([])})
    with pytest.raises(HeinzelError, match="another workspace"):
        chat_on(fake, team="T0ELSEWHE1").messages(CHAN, WINDOW)
    assert fake.made("conversations.history") == []


def test_a_backwards_window_is_refused():
    with pytest.raises(HeinzelError, match="after it ends"):
        chat_on(FakeWeb()).messages(CHAN, Window(since=WINDOW.until, until=WINDOW.since))


def test_too_many_messages_ask_for_a_narrower_window(monkeypatch):
    monkeypatch.setattr("heinzel_slack._chat.MAX_MESSAGES", 3)
    many = [{"ts": f"{T + i}.000000", "user": "U0ADA0001", "text": "x"} for i in range(5)]
    with pytest.raises(HeinzelError, match="narrower window"):
        chat_on(FakeWeb({**USERS, "conversations.history": history(many)})).messages(CHAN, WINDOW)
    assert MAX_MESSAGES > 3


def test_rate_limits_wait_for_retry_after_then_succeed():
    fake = FakeWeb({"conversations.history": history([])})
    fake.limited["conversations.history"] = [2.0, 3.0]
    sleeps: list[float] = []
    assert chat_on(fake, sleeps).messages(CHAN, WINDOW) == []
    assert sleeps == [2.0, 3.0]


@pytest.mark.parametrize("waits", [[31.0], [20.0, 20.0, 25.0], [0.0] * MAX_ATTEMPTS])
def test_rate_limits_give_up_when_too_long_or_endless(waits):
    fake = FakeWeb({"conversations.history": history([])})
    fake.limited["conversations.history"] = list(waits)
    with pytest.raises(RateLimited, match="try again"):
        chat_on(fake).messages(CHAN, WINDOW)


def test_post_neutralises_mentions_and_threads():
    fake = FakeWeb()
    posted = chat_on(fake).post(CHAN, "<!channel> @here ship <@U0OTHER02> & go", thread=f"{T}.000100")
    (sent,) = fake.made("chat.postMessage")
    assert sent["text"] == "&lt;!channel&gt; ＠here ship &lt;@U0OTHER02&gt; &amp; go"
    assert (sent["thread_ts"], sent["link_names"], sent["unfurl_links"]) == (f"{T}.000100", False, False)
    assert (posted.channel, posted.thread, posted.id) == (CHAN, f"{T}.000100", f"{T + 1}.000100")
    assert posted.url == f"https://acme.slack.com/archives/{CHAN}/p{T + 1}000100?thread_ts={T}.000100&cid={CHAN}"


def test_post_without_a_thread_is_top_level():
    fake = FakeWeb()
    posted = chat_on(fake).post(CHAN, "hello")
    assert "thread_ts" not in fake.made("chat.postMessage")[0]
    assert posted.thread is None


@pytest.mark.parametrize(
    ("text", "thread", "match"),
    [("  ", None, "nothing to post"), ("x" * 40_001, None, "longer than"), ("ok", "not-a-ts", "thread")],
)
def test_post_refuses_before_sending(text, thread, match):
    fake = FakeWeb()
    with pytest.raises(HeinzelError, match=match):
        chat_on(fake).post(CHAN, text, thread)
    assert fake.made("chat.postMessage") == []


def test_post_retries_a_rate_limit_since_nothing_was_posted():
    fake = FakeWeb()
    fake.limited["chat.postMessage"] = [1.0]
    sleeps: list[float] = []
    chat_on(fake, sleeps).post(CHAN, "hello")
    assert sleeps == [1.0]
    assert len(fake.made("chat.postMessage")) == 2


@pytest.mark.parametrize("reply", [{"ok": True, "channel": CHAN}, {"ok": True, "ts": "1.2", "channel": "C0ELSEWHE1"}])
def test_an_ambiguous_acknowledgement_is_unknown_not_retried(reply):
    fake = FakeWeb({"chat.postMessage": lambda _p: reply})
    with pytest.raises(SlackUnknown):
        chat_on(fake).post(CHAN, "hello")
    assert len(fake.made("chat.postMessage")) == 1


def test_a_message_with_an_invalid_timestamp_is_an_error():
    fake = FakeWeb({"conversations.history": history([{"ts": "yesterday", "text": "x"}])})
    with pytest.raises(HeinzelError, match="invalid message timestamp"):
        chat_on(fake).messages(CHAN, WINDOW)


def test_too_much_text_asks_for_a_narrower_window(monkeypatch):
    monkeypatch.setattr("heinzel_slack._chat.MAX_CHARS", 10)
    long = [{"ts": f"{T + 1}.000000", "user": "U0ADA0001", "text": "x" * 11}]
    with pytest.raises(HeinzelError, match="characters of messages"):
        chat_on(FakeWeb({**USERS, "conversations.history": history(long)})).messages(CHAN, WINDOW)


def test_unknown_names_and_odd_ids_stay_names_not_ids():
    def fail(_params):
        raise HeinzelError("Slack refused users.info (missing_scope)")

    fake = FakeWeb({
        "users.info": fail,
        "conversations.history": history([
            {"ts": f"{T + 1}.0", "user": "U0ADA0001", "text": "<@U0ADA0001>"},
            {"ts": f"{T + 2}.0", "user": "not-an-id", "text": "x"},
            {"ts": f"{T + 3}.0", "username": "webhook", "text": "y"},
        ]),
    })  # fmt: skip
    found = chat_on(fake).messages(CHAN, WINDOW)
    assert [(m.author.name, m.text) for m in found] == [(None, "@someone"), (None, "x"), ("webhook", "y")]
    assert len(fake.made("users.info")) == 1  # cached per read


def test_without_a_workspace_address_there_are_no_links():
    fake = FakeWeb({"auth.test": lambda _p: {"ok": True, "team_id": TEAM, "url": "http://evil.example/"}})
    assert chat_on(fake).post(CHAN, "hi").url is None
