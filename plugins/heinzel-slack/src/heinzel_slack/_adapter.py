"""The `chat` capability adapter (ADR 0028) with the self channel (ADR 0160), over the person's own Slack app.

`messages` and `post` serve public channels the app's bot user was invited to; `notify_self` and `ask_self` reach the
person in their own direct message with the app (`slack.owner`). Reviewed helper notices and draft approvals stay on
`SlackChannel` (ADR 0120); this adapter neither replaces nor uses them.
"""

import threading
from collections.abc import Sequence

from heinzel import Message, PostedMessage, Window

from heinzel_slack._chat import SlackChat
from heinzel_slack._compat import SelfAnswer, SelfMessage
from heinzel_slack._self import POLL_REQUEST, SlackSelf
from heinzel_slack._service import SlackService
from heinzel_slack._settings import SlackSettings
from heinzel_slack._slack import Listener, Transport
from heinzel_slack._web import Web

HOSTS = ("slack.com", "wss-primary.slack.com")
"""Where the adapter sends data: Slack's Web API and its Socket Mode endpoint."""


class SlackChatAdapter:
    """Slack as Core's `chat` capability: channels, and the signed-in person's own direct message."""

    def __init__(self, settings: SlackSettings, service: SlackService, transport: Transport) -> None:
        """Wire the Web API and Socket Mode seams; nothing is sent and no token is read yet."""

        def web() -> Web:
            return Web(transport.web())

        def poll_web() -> Web:
            return Web(transport.web(timeout=POLL_REQUEST))

        def listener() -> Listener | None:
            return transport.listener() if transport.has_tokens()[1] else None

        self.chat = SlackChat(web, settings.team)
        self.self_channel = SlackSelf(service, web, self.chat, listener, settings.poll_seconds, poll_web=poll_web)

    def messages(self, channel: str, window: Window) -> list[Message]:
        """Messages posted in `channel` within `window`, top-level or reply, oldest first. Mode: read.

        Raises:
            HeinzelError: If the window, the channel or Slack fails.
        """
        return self.chat.messages(channel, window)

    def post(self, channel: str, text: str, thread: str | None = None) -> PostedMessage:
        """Post `text` to `channel`, as a reply in `thread` when given, mentions neutralised. Mode: write.

        Raises:
            HeinzelError: If the text, the channel or Slack fails.
        """
        return self.chat.post(channel, text, thread)

    def notify_self(self, text: str, *, thread: str | None = None, context: str | None = None) -> SelfMessage:
        """Tell the signed-in person `text` in their own DM, in `thread` when given. Mode: write.

        Raises:
            HeinzelError: If Slack is not set up or refuses.
        """
        return self.self_channel.notify_self(text, thread=thread, context=context)

    def ask_self(  # noqa: PLR0913 - Core's signature
        self,
        question: str,
        *,
        options: Sequence[str] = (),
        timeout: float,
        thread: str | None = None,
        context: str | None = None,
        cancel: threading.Event | None = None,
    ) -> SelfAnswer:
        """Ask the signed-in person, options as buttons, and wait up to `timeout` seconds. Mode: write.

        A timeout or `cancel` gives a timed-out answer, never an error.

        Raises:
            HeinzelError: If the question breaks a limit, or Slack is not set up or refuses the post.
        """
        return self.self_channel.ask_self(
            question, options=options, timeout=timeout, thread=thread, context=context, cancel=cancel
        )
