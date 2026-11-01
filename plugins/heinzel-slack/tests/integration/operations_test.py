"""The operations, the doctor checks and the listening job, on the in-memory Slack."""

import pytest
from heinzel import HeinzelError, Status

import heinzel_slack as plugin

pytestmark = pytest.mark.integration


class Prompter:
    def __init__(self):
        self.said = []

    def text(self, question, default=""):
        return " U0OWNER01 "

    def say(self, line):
        self.said.append(line)


class Editor:
    def __init__(self):
        self.written = {}

    def write(self, key, value):
        self.written[key] = value
        return "/config.toml"


def test_notify_gives_the_reason_as_the_why(rig):
    receipt = plugin.notify(rig.channel, "Build done", "You asked to know.", helper="Otto")
    assert receipt.status == "delivered"
    assert "You asked to know." in str(rig.slack.posts[0]["blocks"])
    with pytest.raises(HeinzelError, match="reason"):
        plugin.notify(rig.channel, "Build done", "  ")


def test_ask_status_and_wait_round_trip(rig):
    shared = plugin.ask(rig.service, rig.channel, "Send the report", "Weekly report\n- done\n", helper="Lotte")
    assert shared.state == "pending"
    assert shared.digest == plugin.draft_digest("Weekly report\n- done\n")
    assert plugin.status(rig.service, shared.request_id).state == "pending"
    rig.transport.queued.append(rig.click(plugin.slot(shared.request_id)))
    done = plugin.wait(rig.service, shared.request_id, 2)
    assert done.state == "approved"
    assert done.approves("Weekly report\n- done\n")


def test_ask_says_why_it_was_not_shared(rig):
    with pytest.raises(HeinzelError, match="hide text"):
        plugin.ask(rig.service, rig.channel, "x", "bad‮text")
    rig.slack.fail_post = True
    with pytest.raises(HeinzelError, match="refused"):
        plugin.ask(rig.service, rig.channel, "x", "fine text")


def test_the_listening_job_does_nothing_unless_a_draft_waits(rig):
    assert plugin.listen_job(rig.service) == {"listened": False}
    ref = rig.post().reference
    rig.transport.queued.append(rig.click(ref))
    out = plugin.listen_job(rig.service)
    assert out["listened"] is True
    assert out["approved"] == 1


def test_info_manifest_and_checks(rig):
    assert plugin.info(rig.service).owner == "U0OWNER01"
    assert "socket_mode_enabled" in plugin.manifest()
    assert all(c.status == Status.UP for c in plugin.ready(rig.service))
    live = plugin.live(rig.service)
    assert [c.name for c in live] == ["auth.test", "drafts go to"]
    assert "Ada" in live[1].detail


def test_checks_say_what_is_missing(rig):
    rig.transport.has_tokens = lambda: (False, False)
    rig.service._settings = rig.service._settings.model_copy(update={"owner": ""})
    checks = plugin.ready(rig.service)
    assert [c.status for c in checks] == [Status.DEGRADED] * 3
    assert all(c.fix for c in checks)
    assert not rig.channel.available()
    assert rig.channel.owner_actor() is None


def test_live_check_reports_a_slack_failure(rig):
    def boom():
        raise HeinzelError("Slack refused auth.test (invalid_auth).")

    rig.slack.identity = boom
    assert plugin.live(rig.service)[0].status == Status.DOWN


def test_setup_saves_only_the_owner_and_explains_the_tokens(rig):
    prompter, editor = Prompter(), Editor()
    plugin.setup(plugin.SlackSettings(), prompter, editor)
    assert editor.written == {"slack.owner": "U0OWNER01"}
    assert any("credential set bot-token" in line for line in prompter.said)
