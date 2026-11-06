"""Notices: always the why, only the owner's DM, at most once per key, honest receipts."""

import pytest
from heinzel import ChannelNotice

pytestmark = pytest.mark.integration


def notice(key="k1", **kw):
    fields = {"key": key, "helper": "Lotte", "title": "Draft ready", "body": "You asked for Fridays.", "route": "/x"}
    fields.update(kw)
    return ChannelNotice(**fields)


def test_a_notice_goes_to_the_owners_dm_with_its_why(rig):
    receipt = rig.channel.deliver(notice())
    assert receipt.status == "delivered"
    assert receipt.channel == "slack"
    assert rig.slack.opened == "U0OWNER01"
    dump = str(rig.slack.posts[0]["blocks"])
    assert "Why you are seeing this" in dump
    assert "You asked for Fridays." in dump


def test_the_same_key_is_sent_once(rig):
    first = rig.channel.deliver(notice())
    again = rig.channel.deliver(notice())
    assert (first.status, again.status) == ("delivered", "delivered")
    assert first.reference == again.reference
    assert len(rig.slack.posts) == 1


def test_a_refusal_is_safe_to_retry_but_a_lost_answer_is_unknown_and_never_retried(rig):
    rig.slack.fail_post = True
    assert rig.channel.deliver(notice("a")).status == "refused"
    rig.slack.fail_post = False
    assert rig.channel.deliver(notice("a")).status == "delivered"  # refused means not sent
    rig.slack.lose_post = True
    assert rig.channel.deliver(notice("b")).status == "unknown"
    rig.slack.lose_post = False
    assert rig.channel.deliver(notice("b")).status == "unknown"  # may have been sent: not again
    assert len(rig.slack.posts) == 1


def test_untrusted_text_cannot_ping_or_link(rig):
    rig.channel.deliver(notice(title="<!channel> now", body="<@U123> <https://evil.example|click>"))
    dump = str(rig.slack.posts[0])
    assert "<!channel>" not in dump
    assert "<@U123>" not in dump
    assert "<https://evil" not in dump


def test_a_notice_is_refused_not_raised_when_slack_is_not_set_up(rig):
    rig.service._settings = rig.service._settings.model_copy(update={"owner": ""})
    receipt = rig.channel.deliver(notice())
    assert receipt.status == "refused"
    assert "owner" in (receipt.detail or "")
