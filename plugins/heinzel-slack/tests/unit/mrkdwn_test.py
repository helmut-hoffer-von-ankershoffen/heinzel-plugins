"""Outbound text cannot page anyone; inbound text shows names, not ids, and nothing invisible."""

import pytest

from heinzel_slack._mrkdwn import neutralise, readable

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "raw",
    ["<!channel> ship it", "<!here>", "<!everyone>", "hi <@U0OTHER02>", "<!subteam^S0TEAM|@devs> look", "<#C0CHAN001>"],
)
def test_no_mention_markup_survives_neutralising(raw):
    out = neutralise(raw)
    assert "<" not in out and ">" not in out
    assert "&lt;" in out


@pytest.mark.parametrize("word", ["@here", "@channel", "@Everyone"])
def test_bare_broadcast_words_get_an_inert_at_sign(word):
    assert neutralise(f"ping {word} now") == f"ping \uff20{word[1:]} now"


def test_neutralising_keeps_words_and_markdown():
    assert neutralise("*bold* _it_ & `code`\n- item") == "*bold* _it_ &amp; `code`\n- item"
    assert neutralise("@heresy and mail@channel.example") == "@heresy and mail@channel.example"


def test_inbound_mentions_become_names_never_ids():
    names = {"U0ADA0001": "Ada"}
    text = readable("<@U0ADA0001> and <@U0NOBODY1> in <#C0CHAN001|general>: <!here>", names.get)
    assert text == "@Ada and @someone in #general: @here"
    assert "U0" not in text


def test_inbound_links_groups_and_dates_read_as_text():
    text = readable(
        "<https://example.com|the doc> <https://example.com> <!subteam^S0X|@devs> <!date^1|Friday> &lt;b&gt; &amp;",
        lambda _u: None,
    )
    assert text == "the doc (https://example.com) https://example.com @devs Friday <b> &"


def test_inbound_text_loses_invisible_and_bidirectional_characters():
    assert readable("ok‮evil​\U000e0041", lambda _u: None) == "okevil"
