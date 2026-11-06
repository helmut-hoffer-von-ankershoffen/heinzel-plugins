import json
from datetime import UTC, datetime

import pytest

from heinzel_slack._blocks import approval, notification, plain, settled

pytestmark = pytest.mark.unit
NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


def test_plain_defuses_mentions_links_and_hidden_characters():
    text = plain("<!channel> <@U123> <https://evil.example|click> ‮ & \x00done")
    assert "<" not in text
    assert "&lt;!channel&gt;" in text
    assert "‮" not in text
    assert "&amp;" in text


def test_plain_is_bounded():
    assert len(plain("x" * 1000, 50)) == 50


def test_notification_always_says_why():
    text, blocks = notification("Lotte", "Draft ready", "You asked for Fridays.", "/heinzel?chat=hz-1")
    dump = json.dumps(blocks)
    assert "Why you are seeing this" in dump
    assert "You asked for Fridays." in dump
    assert text == "Draft ready"


def test_approval_shows_the_draft_literally_and_binds_buttons_to_the_digest():
    draft = "Dear <!channel>, *bold* `code` ```fence```"
    digest = "ab" * 32
    _text, blocks = approval("0" * 32, digest, "Post the report", "Lotte", draft, None, NOW)
    pre = next(b for b in blocks if b["type"] == "rich_text")
    assert pre["elements"][0]["elements"][0]["text"] == draft  # literal, unescaped, unparsed
    buttons = next(b for b in blocks if b["type"] == "actions")["elements"]
    assert [b["action_id"] for b in buttons] == ["hz_approve", "hz_decline"]
    assert all(b["value"] == f"v1:{'0' * 32}:{digest}" for b in buttons)
    assert "Approve" == buttons[0]["text"]["text"]


@pytest.mark.parametrize("state", ["approved", "declined", "answered_approved", "expired", "superseded"])
def test_settled_messages_have_no_buttons(state):
    _text, blocks = settled(state, "Post the report", "draft", "cd" * 32, NOW)
    assert not any(b["type"] == "actions" for b in blocks)
