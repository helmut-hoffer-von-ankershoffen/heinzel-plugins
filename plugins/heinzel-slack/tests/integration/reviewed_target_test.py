"""The exact reviewed posting account, owner DM and scope remain preconditions at the transport mutation."""

import pytest
from heinzel import ChannelNotice

pytestmark = pytest.mark.integration


def notice():
    return ChannelNotice(key="notice-one", helper="Lotte", title="Ready", body="You asked to know.", route="")


def send(rig, kind, target):
    if kind == "approval":
        return rig.channel.post_reviewed(rig.request(), target)
    return rig.channel.deliver_reviewed(notice(), target)


@pytest.mark.parametrize("kind", ["approval", "notice"])
@pytest.mark.parametrize("field", ["account", "destination", "scope"])
def test_wrong_reviewed_target_refuses_before_intent_or_any_post(rig, kind, field):
    target = rig.channel.delivery_target()
    assert target is not None
    receipt = send(rig, kind, target.model_copy(update={field: "a-different-target"}))
    assert receipt.status == "refused"
    assert rig.slack.posts == []
    assert rig.service._store is None


@pytest.mark.parametrize("kind", ["approval", "notice"])
@pytest.mark.parametrize("drift", ["workspace", "posting-account", "owner", "dm"])
def test_target_drift_before_client_acquisition_refuses_zero_posts(rig, kind, drift):
    target = rig.channel.delivery_target()
    if drift == "workspace":
        rig.slack.team = "T0OTHER01"
    elif drift == "posting-account":
        rig.slack.bot_user = "U0OTHER01"
    elif drift == "owner":
        rig.service._settings = rig.service.settings.model_copy(update={"owner": "U0OTHER01"})
    else:
        rig.slack.dm = "D0OTHER01"
    assert send(rig, kind, target).status == "refused"
    assert rig.slack.posts == []


@pytest.mark.parametrize("kind", ["approval", "notice"])
@pytest.mark.parametrize("drift", ["workspace", "posting-account", "dm", "scope"])
def test_precheck_does_not_replace_transport_mutation_check(rig, monkeypatch, kind, drift):
    target = rig.channel.delivery_target()
    store = rig.service.store
    original = store.insert if kind == "approval" else store.begin_delivery

    def after_intent(*args):
        result = original(*args)
        if drift == "workspace":
            rig.slack.team = "T0OTHER01"
        elif drift == "posting-account":
            rig.slack.bot_user = "U0OTHER01"
        elif drift == "dm":
            rig.slack.dm = "D0OTHER01"
        else:
            observed = rig.slack.delivery_target
            rig.slack.delivery_target = lambda owner, team: observed(owner, team).model_copy(update={"scope": "other"})
        return result

    monkeypatch.setattr(store, "insert" if kind == "approval" else "begin_delivery", after_intent)
    assert send(rig, kind, target).status == "refused"
    assert rig.slack.posts == []


@pytest.mark.parametrize("kind", ["approval", "notice"])
def test_one_pinned_client_survives_later_credential_selection_without_redirecting(rig, kind):
    from dataclasses import replace

    target = rig.channel.delivery_target()
    foreign = replace(rig.slack, team="T0OTHER01", posts=[], updates=[])
    acquired = []

    def changing_credentials():
        selected = rig.slack if not acquired else foreign
        acquired.append(selected)
        return selected

    rig.transport.api = changing_credentials
    receipt = send(rig, kind, target)
    assert receipt.status == "delivered"
    assert acquired == [rig.slack]
    assert len(rig.slack.posts) == 1
    assert foreign.posts == []
    assert rig.slack.posts[0]["channel"] == target.destination


@pytest.mark.parametrize("kind", ["approval", "notice"])
def test_unknown_reviewed_post_keeps_intent_and_never_reposts_on_retry(rig, kind):
    target = rig.channel.delivery_target()
    rig.slack.lose_post = True
    assert send(rig, kind, target).status == "unknown"
    rig.slack.lose_post = False
    assert send(rig, kind, target).status == "unknown"
    assert rig.slack.posts == []


def test_unavailable_observed_target_disables_reviewed_delivery(rig):
    rig.service._settings = rig.service.settings.model_copy(update={"team": ""})
    assert rig.channel.delivery_target() is None
    rig.service._settings = rig.service.settings.model_copy(update={"team": "T0OTHER01"})
    assert rig.channel.delivery_target() is None
    assert rig.slack.posts == []
