"""The approval guarantees on an in-memory Slack: exact arguments, the owner only, and nothing else counts."""

import copy

import pytest
from heinzel import ApprovalChannel, HeinzelError, NotificationChannel

from heinzel_slack import draft_digest, slot
from heinzel_slack._decide import Decided, Denied

pytestmark = pytest.mark.integration
OWNER, OTHER, TEAM = "U0OWNER01", "U0OTHER02", "T0TEAM001"
DRAFT = "Weekly report\n\n- shipped the Slack channel\n"
ID = slot("req-1")


def posted(rig, **kw):
    receipt = rig.post(**kw)
    assert receipt.status == "delivered", receipt
    return receipt.reference


def test_the_channel_implements_both_core_ports(rig):
    assert isinstance(rig.channel, NotificationChannel)
    assert isinstance(rig.channel, ApprovalChannel)
    assert rig.channel.name == "slack"
    assert rig.channel.available()
    assert rig.channel.owner_actor() == OWNER


def test_the_owner_pressing_approve_on_the_exact_request_becomes_one_reply(rig):
    ref = posted(rig, preview=DRAFT)
    assert rig.slack.opened == OWNER  # only ever the owner's direct message
    assert rig.slack.posts[0]["channel"] == "D0DM000001"
    assert rig.channel.replies([ref]) == []  # nothing pressed yet: nothing claimed
    assert rig.service.handle(rig.click(ref)) == Decided(ref, "approved", f"slack:{TEAM}:{OWNER}")
    (reply,) = rig.channel.replies([ref])
    assert (reply.request_id, reply.decision, reply.actor) == ("req-1", "approve", OWNER)
    assert reply.arguments_sha256 == draft_digest(DRAFT)
    assert rig.service.outcome("req-1").approves(DRAFT)
    assert not rig.service.outcome("req-1").approves(DRAFT + " ")  # one byte different: not what was approved
    assert not any(b["type"] == "actions" for b in rig.slack.updates[-1]["blocks"])


def test_replies_are_for_the_references_asked_about_only(rig):
    first = posted(rig, request_id="a")
    second = posted(rig, request_id="b")
    rig.service.handle(rig.click(first))
    rig.service.handle(rig.click(second, action="hz_decline"))
    assert [r.decision for r in rig.channel.replies([second])] == ["decline"]
    assert [r.request_id for r in rig.channel.replies([first, second])] == ["a", "b"]
    assert rig.channel.replies(["not-a-reference"]) == []


def test_posting_twice_is_one_message(rig):
    first = rig.post()
    again = rig.post()
    assert (first.status, again.status) == ("delivered", "delivered")
    assert first.reference == again.reference
    assert len(rig.slack.posts) == 1


def test_a_request_id_cannot_be_reused_for_other_arguments(rig):
    rig.post()
    other = rig.post(preview="Something else entirely")
    assert other.status == "refused"
    assert len(rig.slack.posts) == 1


def test_decline_is_a_reply_but_never_an_approval(rig):
    ref = posted(rig)
    assert rig.service.handle(rig.click(ref, action="hz_decline")).state == "declined"
    assert [r.decision for r in rig.channel.replies([ref])] == ["decline"]
    assert not rig.service.outcome("req-1").approves(DRAFT)


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"user": {"id": OTHER}}, "not_the_owner"),
        ({"user": {}}, "not_the_owner"),
        ({"team": {"id": "T0EVIL000"}}, "wrong_workspace"),
        ({"channel": {"id": "C0PUBLIC01"}}, "wrong_conversation"),
        ({"container": {"message_ts": "1.1"}}, "wrong_message"),
        ({"message": {"ts": "1.1"}}, "wrong_message"),
        ({"type": "view_submission"}, "not_a_button"),
        ({"actions": []}, "not_one_action"),
    ],
)
def test_a_click_that_is_not_the_owners_on_this_message_changes_nothing(rig, override, reason):
    ref = posted(rig)
    result = rig.service.handle(rig.click(ref, **override))
    assert isinstance(result, Denied)
    assert result.reason == reason
    assert rig.channel.replies([ref]) == []
    assert rig.service.outcome("req-1").state == "pending"
    assert ("denied", reason) in rig.service.store.audit(result.request_id or "-")


def test_the_owner_can_still_approve_after_someone_else_tried(rig):
    ref = posted(rig)
    rig.service.handle(rig.click(ref, user={"id": OTHER}))
    assert rig.service.handle(rig.click(ref)).state == "approved"


def test_replay_is_denied_and_the_first_decision_stands(rig):
    ref = posted(rig)
    payload = rig.click(ref)
    assert isinstance(rig.service.handle(payload), Decided)
    assert rig.service.handle(copy.deepcopy(payload)) == Denied("already_approved", ref)  # Slack retry, or a capture
    assert isinstance(rig.service.handle(rig.click(ref, action="hz_decline")), Denied)
    assert [r.decision for r in rig.channel.replies([ref])] == ["approve"]


def test_a_button_for_other_arguments_is_stale_and_denied(rig):
    ref = posted(rig)
    payload = rig.click(ref)
    payload["actions"][0]["value"] = f"v1:{ref}:{draft_digest('different draft')}"
    assert rig.service.handle(payload) == Denied("stale_draft", ref)
    assert rig.channel.replies([ref]) == []


def test_a_tampered_store_cannot_be_approved(rig):
    ref = posted(rig)
    with rig.service.store._connect() as db:
        db.execute("UPDATE requests SET draft=? WHERE id=?", ("something else entirely", ref))
    assert rig.service.handle(rig.click(ref)) == Denied("lost_race", ref)
    assert rig.channel.replies([ref]) == []


def test_the_host_settling_a_request_as_superseded_voids_its_buttons(rig):
    old = posted(rig, request_id="old")
    new = posted(rig, request_id="new", preview="Weekly report v2")
    rig.channel.settle(old, "superseded")
    assert rig.service.handle(rig.click(old)) == Denied("already_superseded", old)
    assert "Replaced" in rig.slack.updates[-1]["blocks"][-1]["elements"][0]["text"]
    assert rig.service.handle(rig.click(new)).state == "approved"


def test_settling_an_answered_request_updates_the_message_and_changes_no_decision(rig):
    ref = posted(rig)
    rig.service.handle(rig.click(ref))
    rig.channel.settle(ref, "approved")
    assert rig.service.outcome("req-1").state == "approved"
    rig.channel.settle("unknown-reference", "approved")  # best effort: never raises


def test_requests_expire_and_an_expired_one_cannot_be_approved(rig):
    ref = posted(rig)
    rig.advance(minutes=61)
    assert rig.service.handle(rig.click(ref)) == Denied("expired", ref)
    assert rig.service.outcome("req-1").state == "expired"
    assert rig.channel.replies([ref]) == []
    assert "Expired" in rig.slack.updates[-1]["text"]


def test_an_already_expired_request_is_refused_and_posts_nothing(rig):
    receipt = rig.post(expires_at=rig.now[0])
    assert receipt.status == "refused"
    assert rig.slack.posts == []


@pytest.mark.parametrize("skew", [-3600, 3600])
def test_a_click_with_an_implausible_time_is_denied(rig, skew):
    ref = posted(rig)
    payload = rig.click(ref)
    payload["actions"][0]["action_ts"] = f"{rig.now[0].timestamp() + skew:.6f}"
    assert rig.service.handle(payload) == Denied("bad_time", ref)


@pytest.mark.parametrize("value", ["", "approve", "v1:x:y", "v1:" + "0" * 32 + ":" + "0" * 64])
def test_a_forged_button_value_is_denied(rig, value):
    ref = posted(rig)
    payload = rig.click(ref)
    payload["actions"][0]["value"] = value
    assert isinstance(rig.service.handle(payload), Denied)
    assert rig.channel.replies([ref]) == []


@pytest.mark.parametrize(
    "payload", [None, "approve", [], {}, {"type": "block_actions"}, {"type": "block_actions", "actions": ["x"]}]
)
def test_garbage_never_raises_and_never_approves(rig, payload):
    posted(rig)
    assert isinstance(rig.service.handle(payload), Denied)


def test_text_in_a_message_or_username_is_data_not_an_answer(rig):
    ref = posted(rig)
    for event in (
        {"type": "message", "user": OWNER, "text": "approve"},
        {"type": "reaction_added", "user": OWNER, "reaction": "white_check_mark"},
        {"type": "slash_commands", "command": "/approve", "user_id": OWNER},
    ):
        assert isinstance(rig.service.handle(event), Denied)
    assert rig.channel.replies([ref]) == []


def test_a_preview_that_hides_text_is_refused_and_never_posted(rig):
    receipt = rig.post(preview="looks fine‮ txt.exe")
    assert receipt.status == "refused"
    assert rig.slack.posts == []


def test_a_refused_post_can_never_be_approved(rig):
    rig.slack.fail_post = True
    receipt = rig.post()
    assert receipt.status == "refused"
    assert isinstance(rig.service.handle(rig.click(ID)), Denied)
    assert rig.service.outcome("req-1").state == "failed"


def test_a_lost_post_is_unknown_and_is_never_retried_by_itself(rig):
    rig.slack.lose_post = True
    assert rig.post().status == "unknown"
    rig.slack.lose_post = False
    assert rig.post().status == "unknown"  # the same id is not posted again behind the host's back
    assert rig.slack.posts == []
    assert isinstance(rig.service.handle(rig.click(ID)), Denied)


def test_the_wrong_workspace_token_is_refused_before_anything_is_posted(rig):
    rig.slack.team = "T0OTHER00"
    receipt = rig.post()
    assert receipt.status == "refused"
    assert "another workspace" in (receipt.detail or "")
    assert rig.slack.posts == []


def test_wait_returns_the_owners_answer_from_the_listener(rig):
    ref = posted(rig)
    rig.transport.queued.append(rig.click(ref))
    assert rig.service.wait("req-1", 2).state == "approved"
    assert rig.transport.listeners[0].stopped


def test_wait_times_out_honestly(rig):
    posted(rig)
    assert rig.service.wait("req-1", 0).state == "pending"


def test_listen_counts_answers_and_refusals(rig):
    ref = posted(rig)
    rig.transport.queued.extend([rig.click(ref, user={"id": OTHER}), rig.click(ref)])
    done = rig.service.listen(0.3)
    assert (done.approved, done.declined, done.refused) == (1, 0, 1)


def test_an_unknown_request_id_is_an_error_not_a_guess(rig):
    with pytest.raises(HeinzelError, match="no such"):
        rig.service.outcome("nope")
