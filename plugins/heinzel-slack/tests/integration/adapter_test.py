"""The `chat` adapter: registered for Core, matching the protocol, wired to the Slack seams."""

import pytest
from heinzel import ProviderLet, Settings
from heinzel.testing import assert_adapter

from heinzel_slack import SlackChatAdapter, SlackService, SlackSettings, module
from heinzel_slack._adapter import HOSTS
from tests.conftest import DM, OWNER, TEAM, FakeSlack, FakeSocket, FakeTransport, FakeWeb

pytestmark = pytest.mark.integration


def test_the_adapter_is_registered_for_chat_read_and_write():
    (provider,) = [let for let in module.lets if isinstance(let, ProviderLet)]
    assert (provider.capability, provider.factory) == ("chat", SlackChatAdapter)
    assert set(provider.modes) == {"read", "write"}
    assert HOSTS == ("slack.com", "wss-primary.slack.com")


def test_the_adapter_matches_cores_chat_protocol():
    assert_adapter(SlackChatAdapter, "chat", modes={"read", "write"})


class Wired(FakeTransport):
    def __init__(self, web: FakeWeb, socket: FakeSocket, *, app_token: bool) -> None:
        super().__init__(FakeSlack())
        self.fake_web, self.socket, self.app_token = web, socket, app_token
        self.timeouts: list[float | None] = []

    def web(self, timeout=None):
        self.timeouts.append(timeout)
        return self.fake_web

    def listener(self):
        return self.socket

    def has_tokens(self):
        return True, self.app_token


@pytest.mark.parametrize("app_token", [True, False])
def test_the_adapter_uses_the_bot_token_web_api_and_socket_mode_only_with_an_app_token(tmp_path, app_token):
    settings = SlackSettings(owner=OWNER, team=TEAM, poll_seconds=1)
    web, socket = FakeWeb(), FakeSocket()
    transport = Wired(web, socket, app_token=app_token)
    service = SlackService(settings, transport, Settings(state_dir=tmp_path / "state"))  # type: ignore[arg-type]
    chat = SlackChatAdapter(settings, service, transport)  # type: ignore[arg-type]
    assert chat.notify_self("hi").thread == f"{1761912000 + 1}.000100"
    assert chat.post("C0CHAN0001", "hello").channel == "C0CHAN0001"
    assert chat.ask_self("Ship?", options=["Yes"], timeout=0.2).timed_out
    for thread in chat.self_channel.closing:
        thread.join(2)
    assert socket.started == (1 if app_token else 0)
    assert socket.stopped == socket.started
    assert web.made("chat.postMessage")[0]["channel"] == DM
    assert 5.0 in transport.timeouts  # reply reads while a question waits have a short time limit
