"""The operations, the doctor checks and the listening job, on the in-memory Slack."""

import pytest
from heinzel import HeinzelError, Status

import heinzel_slack as plugin

pytestmark = pytest.mark.integration


class Prompter:
    def __init__(self):
        self.said = []

    def text(self, question, default=""):
        return " T0TEAM001 " if "workspace" in question else " U0OWNER01 "

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


def test_actual_public_system_info_api_contains_only_static_slack_metadata(rig, tmp_path):
    from fastapi.testclient import TestClient
    from heinzel import Kernel, Settings
    from heinzel.heads import api
    from heinzel.kernel import discover

    rig.post()
    records, errors = discover()
    assert not errors
    kernel = Kernel(Settings(state_dir=tmp_path / "public-state"), records, errors)
    kernel.bind(plugin.SlackService, rig.service)
    public = TestClient(api.build(kernel), base_url="http://localhost")
    response = public.get("/system/info")
    assert response.status_code == 200, response.text
    section = response.json()["sections"]["slack"]
    assert set(section) == {"plugin", "version", "heinzel_version"}
    assert section["plugin"] == "heinzel-slack"
    assert "U0OWNER01" not in response.text
    assert all(key not in section for key in ("owner", "bot_token", "app_token", "pending"))
    assert public.get("/slack/info").status_code == 404

    # The aggregate must not even consult private setup, token presence or stored drafts.
    def private_access():
        raise AssertionError("public aggregate read private Slack setup")

    rig.service.about = private_access
    rig.transport.has_tokens = private_access
    assert public.get("/system/info").json()["sections"]["slack"] == section


def test_checks_say_what_is_missing(rig):
    rig.transport.has_tokens = lambda: (False, False)
    rig.service._settings = rig.service._settings.model_copy(update={"owner": "", "team": "", "bot_enabled": True})
    checks = plugin.ready(rig.service)
    assert [c.status for c in checks] == [Status.DEGRADED] * 4
    assert all(c.fix for c in checks)
    assert not rig.channel.available()
    assert rig.channel.owner_actor() is None


def test_local_checks_report_missing_workspace_with_owner_and_tokens_set(rig):
    rig.service._settings = rig.service.settings.model_copy(update={"team": ""})

    def no_network():
        raise AssertionError("local readiness asked Slack")

    rig.transport.api = no_network
    checks = {check.name: check for check in plugin.ready(rig.service)}
    assert checks["workspace"].status == Status.DEGRADED
    assert checks["workspace"].fix == "hz system config set slack.team T01ABCDEF"
    assert all(checks[key].status == Status.UP for key in ("owner", "bot token", "app token"))
    assert not rig.channel.available()


@pytest.mark.parametrize("binding", [{"team": ""}, {"owner": ""}, {"team": "", "owner": ""}])
def test_live_check_fails_closed_without_complete_target_binding(rig, binding):
    rig.service._settings = rig.service.settings.model_copy(update=binding)

    def no_credentials_or_network():
        raise AssertionError("missing binding must fail before credentials or network")

    rig.transport.api = no_credentials_or_network
    checks = plugin.live(rig.service)
    assert [check.status for check in checks] == [Status.DOWN]
    assert all(check.fix == "hz setup slack" for check in checks)
    assert rig.slack.posts == rig.slack.updates == []


def test_live_check_rejects_wrong_workspace_before_reading_owner_profile(rig):
    rig.slack.team = "T0OTHER01"

    def no_foreign_profile(_owner):
        raise AssertionError("must not query the owner's ID in another workspace")

    rig.slack.display_name = no_foreign_profile
    checks = plugin.live(rig.service)
    assert [check.status for check in checks] == [Status.DOWN]
    assert "does not match slack.team" in checks[0].detail
    assert checks[0].fix == "hz setup slack"
    assert "T0OTHER01" not in str(checks)
    assert "U0OWNER01" not in str(checks)
    assert rig.slack.posts == rig.slack.updates == []


def test_correct_workspace_binding_is_up_locally_and_live(rig):
    assert all(check.status == Status.UP for check in plugin.ready(rig.service))
    assert all(check.status == Status.UP for check in plugin.live(rig.service))
    assert rig.channel.available()
    assert rig.slack.posts == rig.slack.updates == []


def test_live_check_reports_a_slack_failure(rig):
    def boom():
        raise HeinzelError("Slack refused auth.test (invalid_auth).")

    rig.slack.identity = boom
    assert plugin.live(rig.service)[0].status == Status.DOWN


def test_setup_saves_only_the_owner_and_explains_the_tokens(rig):
    prompter, editor = Prompter(), Editor()
    plugin.setup(plugin.SlackSettings(), prompter, editor)
    assert editor.written == {"slack.owner": "U0OWNER01", "slack.team": "T0TEAM001", "slack.bot_enabled": True}
    assert any("credential set bot-token" in line for line in prompter.said)
