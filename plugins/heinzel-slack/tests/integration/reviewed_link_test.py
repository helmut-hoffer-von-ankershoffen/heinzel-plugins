"""Only approved-link entrypoints can mutate; exact source targets and uncertain intents survive retries."""

from types import SimpleNamespace

import pytest
from heinzel import ChannelNotice, ChannelTarget, HeinzelError

from heinzel_slack.links import _reviewed_link as links

pytestmark = pytest.mark.integration
TARGET = ChannelTarget(account="slack:T01234567:U01234567", destination="D01234567", scope="scope")
NOTICE = ChannelNotice(
    key="draft-key",
    helper="Lotte",
    title="Release poem",
    route="",
    body="https://docs.google.com/document/d/fictional_file_id/edit",
)


class Cli:
    target_value = TARGET
    reply = {"channel_id": "D01234567", "ts": "1234567890.123456"}

    def __init__(self, *args):
        self.calls = []
        self.targets = 0

    def target(self):
        self.targets += 1
        return self.target_value

    def call(self, args):
        self.calls.append(args)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply

    def close(self):
        pass


@pytest.fixture
def rig(tmp_path, monkeypatch):
    cli = Cli()
    monkeypatch.setattr(links, "_CapturedCli", lambda *args: cli)
    service = links.SlackReviewedLinks(
        SimpleNamespace(cli_path="native", cli_profile="fiction"), None, SimpleNamespace(state_dir=tmp_path)
    )
    return service, cli


def test_observation_and_legacy_delivery_never_send_before_explicit_link_entrypoint(rig):
    service, cli = rig
    assert service.delivery_target() == TARGET
    assert service.deliver(NOTICE).status == "refused"
    assert cli.calls == []
    receipt = service.deliver_link_reviewed(NOTICE, TARGET)
    assert receipt.status == "delivered"
    assert receipt.reference == "D01234567:1234567890.123456"
    assert cli.calls == [["messages", "send", "--recipient-id", "D01234567", "--message", NOTICE.body]]
    assert cli.targets == 3


@pytest.mark.parametrize("field", ["account", "destination", "scope"])
def test_exact_target_drift_refuses_without_creating_delivery_intent(rig, field):
    service, cli = rig
    receipt = service.deliver_link_reviewed(NOTICE, TARGET.model_copy(update={field: "other"}))
    assert receipt.status == "refused"
    assert cli.calls == []
    assert not service._directory.exists()


@pytest.mark.parametrize("reply", [{}, {"channel_id": "D0OTHER1", "ts": "123.1"}, HeinzelError("transport timeout")])
def test_unknown_ack_and_changed_payload_retries_are_never_resent(rig, reply):
    service, cli = rig
    cli.reply = reply
    assert service.deliver_link_reviewed(NOTICE, TARGET).status == "unknown"
    cli.reply = Cli.reply
    assert service.deliver_link_reviewed(NOTICE, TARGET).status == "unknown"
    changed = NOTICE.model_copy(update={"body": NOTICE.body.replace("fictional", "different")})
    assert service.deliver_link_reviewed(changed, TARGET).status == "unknown"
    assert len(cli.calls) == 1


def test_target_is_checked_again_after_durable_intent(rig):
    service, cli = rig

    def moving():
        cli.targets += 1
        return TARGET if cli.targets == 1 else TARGET.model_copy(update={"destination": "other"})

    cli.target = moving
    assert service.deliver_link_reviewed(NOTICE, TARGET).status == "refused"
    assert cli.calls == []


def test_literal_url_only_and_no_second_legacy_path(rig):
    service, cli = rig
    for body in ["please send " + NOTICE.body, "https://evil.invalid/document/d/fiction/edit", "hello"]:
        assert service.deliver_link_reviewed(NOTICE.model_copy(update={"body": body}), TARGET).status == "refused"
    assert service.deliver_reviewed(NOTICE, TARGET).status == "refused"
    assert cli.calls == []


def test_cli_observation_finds_exact_existing_signed_in_user_self_dm():
    cli = object.__new__(links._CapturedCli)
    cli.settings = SimpleNamespace(cli_profile="fiction")
    calls = []

    def call(args):
        calls.append(args)
        if args[0] == "auth":
            return {"status": "ok", "profile": "fiction", "workspace_id": "T01234567", "user_id": "U01234567"}
        return {
            "conversations": [{"id": "D01234567", "is_im": True, "is_mpim": False, "user": "U01234567"}],
            "next_cursor": None,
        }

    cli.call = call
    cli.source = "source-digest"
    target = cli.target()
    assert target.destination == "D01234567"
    assert target.account == "slack:T01234567:U01234567"
    assert "source-digest" in target.scope
    assert all(args[0] != "messages" for args in calls)


def test_captured_native_binary_profile_and_owner_refuse_configuration_drift(tmp_path, monkeypatch):
    import json
    import shutil
    from pathlib import Path

    from heinzel import Config

    from heinzel_slack._settings import SlackSettings

    selected = tmp_path / "selected-slackcli"
    shutil.copyfile(shutil.which("true"), selected)
    selected.chmod(0o700)
    directory = tmp_path / ".config" / "slackcli"
    directory.mkdir(parents=True)
    config_file = directory / "workspaces.json"
    data = {
        "default_workspace": "fiction",
        "workspaces": {
            "fiction": {
                "workspace_id": "T01234567",
                "workspace_name": "Fiction",
                "auth_type": "browser",
                "xoxd_token": "synthetic-fixture-session",
                "xoxc_token": "synthetic-fixture-client",
            }
        },
    }
    config_file.write_text(json.dumps(data))
    settings = SlackSettings(cli_path=selected, cli_profile="fiction")
    principal = SimpleNamespace(id="owner")
    current = SimpleNamespace(
        principal=lambda: principal,
        owner=lambda: principal,
        context=lambda: SimpleNamespace(principal=principal, authentication="cli", permissions={"private:read"}),
    )
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(Config, "load", lambda *args: SimpleNamespace(settings=lambda *args: settings))
    monkeypatch.setattr(links, "run", lambda *args: b"0.18.0\n")
    cli = links._CapturedCli(settings, current)
    try:
        assert cli.executable != selected
        assert cli.executable.read_bytes() == selected.read_bytes()
        assert cli.environment["HOME"] != str(tmp_path)
        private_config = Path(cli.environment["HOME"]) / ".config/slackcli/workspaces.json"
        assert set(json.loads(private_config.read_text())["workspaces"]) == {"fiction"}
        cli._check()
        config_file.write_text(json.dumps({"workspaces": {}}))
        with pytest.raises(HeinzelError, match="changed"):
            cli._check()
        assert json.loads(private_config.read_text())["workspaces"]["fiction"]["workspace_id"] == "T01234567"
    finally:
        captured = cli.executable
        cli.close()
        assert not captured.exists()


def test_explicit_bot_disable_keeps_reviewed_links_independent_and_target_bound(rig):
    from pathlib import Path

    from heinzel_slack import SlackSettings

    service, cli = rig
    service._settings = SlackSettings(bot_enabled=False, cli_path=Path("/fiction/slackcli"), cli_profile="fiction")
    assert service.available()
    assert service.delivery_target() == TARGET
    changed = TARGET.model_copy(update={"account": "other"})
    assert service.deliver_link_reviewed(NOTICE, changed).status == "refused"
    assert cli.calls == []
    assert service.deliver(NOTICE).status == "refused"
    assert cli.calls == []
    assert service.deliver_link_reviewed(NOTICE, TARGET).status == "delivered"
    assert len(cli.calls) == 1
    assert service.deliver_link_reviewed(NOTICE, TARGET).status == "unknown"
    assert len(cli.calls) == 1


@pytest.mark.parametrize(
    "arguments",
    [
        ["auth", "whoami"],
        ["conversations", "list", "--types", "im", "--limit", "200", "--fields", "id,user,is_im,is_mpim,is_archived"],
        [
            "conversations",
            "list",
            "--types",
            "im",
            "--limit",
            "200",
            "--fields",
            "id,user,is_im,is_mpim,is_archived",
            "--cursor",
            "next",
        ],
        ["messages", "send", "--recipient-id", "D01234567", "--message", NOTICE.body],
    ],
)
def test_native_link_lease_passes_only_the_reviewed_command_with_exact_workspace(monkeypatch, arguments):
    cli = object.__new__(links._CapturedCli)
    cli._check = lambda: None
    cli.deadline = 20
    cli.executable = "captured-cli"
    cli.environment = {"HOME": "fictional-home"}
    cli.settings = SimpleNamespace(cli_profile="fiction")
    monkeypatch.setattr(links.time, "monotonic", lambda: 10)

    def run(binary, argv, environment, remaining):
        assert binary == cli.executable
        assert argv == [*arguments, "--workspace", "fiction", "--json"]
        assert environment is cli.environment
        assert remaining == 10
        return b'{"status":"ok"}'

    monkeypatch.setattr(links, "run", run)
    assert cli.call(arguments) == {"status": "ok"}


@pytest.mark.parametrize(
    ("arguments", "deadline", "message"),
    [
        (["auth", "whoami", "--workspace", "different"], 20, "fixed operations"),
        (["messages", "send", "--recipient-id", "C01234567", "--message", NOTICE.body], 20, "fixed operations"),
        (["messages", "send", "--recipient-id", "D01234567", "--message", "unreviewed text"], 20, "fixed operations"),
        (["auth", "whoami"], 10, "lease expired"),
    ],
)
def test_native_link_lease_refuses_unsupported_or_expired_commands_before_transport(
    monkeypatch, arguments, deadline, message
):
    cli = object.__new__(links._CapturedCli)
    cli._check = lambda: None
    cli.deadline = deadline
    monkeypatch.setattr(links.time, "monotonic", lambda: 10)

    def unexpected(*args):
        pytest.fail("No provider command may run")

    monkeypatch.setattr(links, "run", unexpected)
    with pytest.raises(HeinzelError, match=message):
        cli.call(arguments)


@pytest.mark.parametrize("raw", [b'{"status":"ok","status":"ok"}', b"[]", b"\xff"])
def test_native_link_acknowledgement_must_be_an_unambiguous_object(raw):
    with pytest.raises(HeinzelError, match="invalid structured acknowledgement"):
        links._json(raw)
