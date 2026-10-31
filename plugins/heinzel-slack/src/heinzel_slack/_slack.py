# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# pyright: reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportUnnecessaryIsInstance=false
# slack-sdk's replies are loosely typed JSON; this file is the one boundary where that is read, and it reads ids only.
"""Slack itself, behind two small seams so everything else can be tested without it.

`SlackApi` is the Web API (post, update, open the owner's DM); `Listener` is Socket Mode, the websocket Slack
pushes button clicks down. Socket Mode needs no public address: nothing on this machine is reachable from outside.
Both use the official `slack-sdk`, never a browser session. A token is only ever handed to the SDK; errors carry
Slack's error code and nothing else.
"""

import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from heinzel import Credentials, HeinzelError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.client import BaseSocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

from heinzel_slack._module import module
from heinzel_slack._settings import SlackSettings

BOT_TOKEN = module.credential(
    "bot-token", purpose="bot token (xoxb-...) of your own Heinzelmännchen Slack app", service="slack"
)
APP_TOKEN = module.credential(
    "app-token", purpose="app-level token (xapp-..., scope connections:write) for button clicks", service="slack"
)


@dataclass(frozen=True, slots=True)
class Identity:
    """Who the bot token is: the workspace and the bot."""

    team_id: str
    team: str
    bot_user: str


class SlackApi(Protocol):
    """The few Web API calls this plugin makes."""

    def identity(self) -> Identity:
        """`auth.test`: the workspace this token belongs to."""
        ...

    def open_dm(self, user: str) -> str:
        """`conversations.open`: the id of the app's direct message with `user`."""
        ...

    def post(self, channel: str, text: str, blocks: list[dict[str, Any]]) -> str:
        """`chat.postMessage` without link unfurling; the new message's `ts`."""
        ...

    def update(self, channel: str, ts: str, text: str, blocks: list[dict[str, Any]]) -> None:
        """`chat.update`."""
        ...

    def display_name(self, user: str) -> str | None:
        """`users.info` name, or None when the app may not read it."""
        ...


class Listener(Protocol):
    """Something that hands interactive payloads to a handler until stopped."""

    def start(self, handler: Callable[[dict[str, Any]], None]) -> None:
        """Connect and call `handler` for every interactive payload."""
        ...

    def stop(self) -> None:
        """Disconnect."""
        ...


class SlackRefused(HeinzelError):
    """Slack answered and said no: nothing was posted, so trying again is safe."""


class SlackUnknown(HeinzelError):
    """The request may or may not have reached Slack (timeout, dropped connection): never retry on its own."""


def _fail(action: str, error: SlackApiError) -> SlackRefused:
    code = str(error.response.get("error", "unknown")) if error.response is not None else "unknown"
    hint = {
        "invalid_auth": " The bot token is not valid; store a new one with `hz system credential set bot-token`.",
        "token_revoked": " The token was revoked; reinstall the app and store the new token.",
        "missing_scope": " The app lacks a scope; reinstall it from the manifest in `hz slack manifest`.",
        "not_allowed_token_type": " That token type cannot do this.",
    }.get(code, "")
    return SlackRefused(f"Slack refused {action} ({code}).{hint}")


class WebApi:
    """`SlackApi` over `slack_sdk.WebClient`."""

    def __init__(self, token: str, timeout: float, base_url: str = "https://slack.com/api/") -> None:
        """Create the client; no request is made. `base_url` exists so tests can point at a local server."""
        self._client = WebClient(token=token, timeout=int(timeout), base_url=base_url)

    def identity(self) -> Identity:  # noqa: D102
        try:
            reply = self._client.auth_test()
        except SlackApiError as error:
            raise _fail("auth.test", error) from None
        return Identity(str(reply["team_id"]), str(reply.get("team", "")), str(reply.get("user_id", "")))

    def open_dm(self, user: str) -> str:  # noqa: D102
        try:
            reply = self._client.conversations_open(users=[user])
        except SlackApiError as error:
            raise _fail("opening the direct message", error) from None
        channel = str(reply["channel"]["id"])
        if not channel.startswith("D"):
            msg = "Slack did not open a direct message; refusing to post anywhere else"
            raise HeinzelError(msg)
        return channel

    def post(self, channel: str, text: str, blocks: list[dict[str, Any]]) -> str:  # noqa: D102
        try:
            reply = self._client.chat_postMessage(
                channel=channel, text=text, blocks=blocks, unfurl_links=False, unfurl_media=False, link_names=False
            )
        except SlackApiError as error:
            raise _fail("the message", error) from None
        except Exception as error:  # noqa: BLE001 - the SDK raises transport errors of several types
            msg = f"Slack did not answer the message ({type(error).__name__}); it may or may not have been posted"
            raise SlackUnknown(msg) from None
        return str(reply["ts"])

    def update(self, channel: str, ts: str, text: str, blocks: list[dict[str, Any]]) -> None:  # noqa: D102
        try:
            self._client.chat_update(channel=channel, ts=ts, text=text, blocks=blocks)
        except SlackApiError as error:
            raise _fail("the update", error) from None

    def display_name(self, user: str) -> str | None:  # noqa: D102
        try:
            reply = self._client.users_info(user=user)
        except SlackApiError:
            return None
        profile = reply["user"]
        return str(profile.get("real_name") or profile.get("name") or "") or None


class SocketListener:
    """`Listener` over Slack's Socket Mode. Every envelope is acknowledged at once; only button clicks are passed on."""

    def __init__(self, app_token: str) -> None:
        """Prepare the client; nothing connects until `start`."""
        self._token = app_token
        self._client: SocketModeClient | None = None
        self._lock = threading.Lock()

    def start(self, handler: Callable[[dict[str, Any]], None]) -> None:  # noqa: D102
        client = SocketModeClient(app_token=self._token)

        def on_request(socket: BaseSocketModeClient, request: SocketModeRequest) -> None:
            socket.send_socket_mode_response(SocketModeResponse(envelope_id=request.envelope_id))
            if request.type == "interactive" and isinstance(request.payload, dict):
                handler(request.payload)

        client.socket_mode_request_listeners.append(on_request)
        try:
            client.connect()
        except Exception as error:  # noqa: BLE001 - the SDK raises several types; none may carry the token
            msg = f"Could not open Slack's Socket Mode connection ({type(error).__name__}); check the app-level token"
            raise HeinzelError(msg) from None
        with self._lock:
            self._client = client

    def stop(self) -> None:  # noqa: D102
        with self._lock:
            client, self._client = self._client, None
        if client is not None:
            client.close()


class Transport:
    """Builds the Web API and the listener from the stored tokens; tests replace it."""

    def __init__(self, settings: SlackSettings, credentials: Credentials) -> None:
        """Read nothing yet; tokens are fetched when a call needs them."""
        self._settings = settings
        self._credentials = credentials

    def api(self) -> SlackApi:
        """The Web API with the bot token.

        Raises:
            HeinzelError: If the bot token is not stored.
        """
        return WebApi(self._credentials.require(BOT_TOKEN), self._settings.timeout)

    def listener(self) -> Listener:
        """A Socket Mode listener with the app-level token.

        Raises:
            HeinzelError: If the app-level token is not stored.
        """
        return SocketListener(self._credentials.require(APP_TOKEN))

    def has_tokens(self) -> tuple[bool, bool]:
        """Whether the bot token and the app-level token are stored."""
        return self._credentials.has(BOT_TOKEN), self._credentials.has(APP_TOKEN)
