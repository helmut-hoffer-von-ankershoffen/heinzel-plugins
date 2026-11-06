"""Optional bot activation never weakens either delivery transport's boundaries."""

from pathlib import Path

import pytest
from heinzel import ChannelNotice, HeinzelError, Status

import heinzel_slack as plugin

pytestmark = pytest.mark.integration


def configured(rig, *, tokens=(False, False), **settings):
    rig.service._settings = plugin.SlackSettings(**settings)
    rig.transport.has_tokens = lambda: tokens


def no_transport(*args):
    raise AssertionError("inactive bot accessed Slack")


@pytest.mark.parametrize("enabled", [None, False])
def test_unconfigured_optional_bot_has_neutral_local_and_live_health(rig, enabled):
    configured(rig, bot_enabled=enabled)
    rig.transport.api = no_transport
    rig.transport.listener = no_transport
    assert all(c.status == Status.UP for c in plugin.ready(rig.service))
    assert all(c.status == Status.UP for c in plugin.live(rig.service))
    assert not rig.channel.available()
    assert plugin.listen_job(rig.service) == {"listened": False}


def test_links_only_identity_is_not_a_bot_prerequisite_when_explicitly_disabled(rig):
    configured(
        rig,
        bot_enabled=False,
        owner="U0OWNER01",
        team="T0TEAM001",
        cli_path=Path("/fiction/slackcli"),
        cli_profile="fiction",
    )
    rig.transport.has_tokens = no_transport
    rig.transport.api = no_transport
    assert all(c.status == Status.UP for c in plugin.ready(rig.service))
    assert all(c.status == Status.UP for c in plugin.live(rig.service))
    assert not rig.channel.available()
    assert rig.channel.owner_actor() is None
    assert rig.channel.delivery_target() is None


@pytest.mark.parametrize(
    "settings,tokens",
    [
        ({"bot_enabled": True}, (False, False)),
        ({"owner": "U0OWNER01"}, (False, False)),
        ({"team": "T0TEAM001"}, (False, False)),
        ({}, (True, False)),
        ({}, (False, True)),
        (
            {
                "owner": "U0OWNER01",
                "team": "T0TEAM001",
                "cli_path": Path("/fiction/slackcli"),
                "cli_profile": "fiction",
            },
            (False, False),
        ),
    ],
)
def test_enabled_or_partial_bot_reports_missing_prerequisites_even_with_cli(rig, settings, tokens):
    configured(rig, tokens=tokens, **settings)
    checks = plugin.ready(rig.service)
    assert len(checks) == 4
    assert any(c.status == Status.DEGRADED for c in checks)
    assert all(c.fix for c in checks if c.status == Status.DEGRADED)
    assert not rig.channel.available()


def test_explicit_disable_blocks_all_bot_mutations_with_existing_tokens_and_pending_approval(rig):
    ref = rig.post().reference
    payload = rig.click(ref)
    request = rig.request(request_id="new-request")
    target = rig.channel.delivery_target()
    rig.service._settings = rig.service.settings.model_copy(update={"bot_enabled": False})
    rig.transport.api = no_transport
    rig.transport.listener = no_transport
    rig.transport.has_tokens = no_transport
    notice = ChannelNotice(key="notice", helper="Heinzel", title="Title", body="Body", route="")
    assert rig.channel.deliver(notice).status == "refused"
    assert rig.channel.deliver_reviewed(notice, target).status == "refused"
    assert rig.channel.post(request).status == "refused"
    assert rig.channel.post_reviewed(request, target).status == "refused"
    assert rig.service.handle(payload).reason == "bot_disabled"
    assert rig.channel.replies([ref]) == []
    for operation in (
        lambda: rig.service.wait("req-1", 0),
        lambda: rig.service.listen(0),
        lambda: rig.channel.settle(ref, "superseded"),
    ):
        with pytest.raises(HeinzelError, match="disabled"):
            operation()
    assert plugin.listen_job(rig.service) == {"listened": False}
    assert rig.service.store.get(ref).state == "pending"
    rig.advance(minutes=61)
    assert rig.service.outcome("req-1").state == "expired"
    assert len(rig.slack.posts) == 1
    assert rig.slack.updates == []


def test_unconfigured_inference_does_not_hide_credential_store_errors(rig):
    configured(rig)

    def corrupt():
        raise HeinzelError("credential store corrupt")

    rig.transport.has_tokens = corrupt
    with pytest.raises(HeinzelError, match="corrupt"):
        plugin.ready(rig.service)
    with pytest.raises(HeinzelError, match="corrupt"):
        plugin.live(rig.service)


def test_bot_activation_is_ignored_in_project_configuration():
    assert "bot_enabled" in plugin.SlackSettings.ignored_in_project
