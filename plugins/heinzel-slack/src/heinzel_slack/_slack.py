# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# pyright: reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportUnnecessaryIsInstance=false
# slack-sdk's replies are loosely typed JSON; this file is the one boundary where that is read, and it reads ids only.
"""Slack itself, behind two small seams so everything else can be tested without it.

`SlackApi` is the Web API (post, update, open the owner's DM); `Listener` is Socket Mode, the websocket Slack
pushes button clicks down. Socket Mode needs no public address: nothing on this machine is reachable from outside.
Both use the official `slack-sdk`, never a browser session. A token is only ever handed to the SDK; errors carry
Slack's error code and nothing else.
"""

import re
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from heinzel import ChannelTarget, Credentials, HeinzelError

from heinzel_slack._module import module
from heinzel_slack._settings import SlackSettings
from heinzel_slack._vendor.slack_sdk import WebClient
from heinzel_slack._vendor.slack_sdk.errors import SlackApiError
from heinzel_slack._vendor.slack_sdk.socket_mode import SocketModeClient
from heinzel_slack._vendor.slack_sdk.socket_mode.client import BaseSocketModeClient
from heinzel_slack._vendor.slack_sdk.socket_mode.request import SocketModeRequest
from heinzel_slack._vendor.slack_sdk.socket_mode.response import SocketModeResponse

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

    def delivery_target(self, owner: str, team: str) -> ChannelTarget:
        """Observe this client's authenticated workspace/account and the configured owner's DM and write scope."""
        ...

    def post_reviewed(
        self, target: ChannelTarget, owner: str, team: str, text: str, blocks: list[dict[str, Any]]
    ) -> str:
        """Verify the exact target and post through the same credential-pinned client, or refuse without posting."""
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
    if code not in {
        "invalid_auth",
        "token_revoked",
        "missing_scope",
        "not_allowed_token_type",
        "channel_not_found",
        "not_in_channel",
        "is_archived",
        "msg_too_long",
        "no_text",
    }:
        raise SlackUnknown("Slack did not provide a definite refusal; do not retry") from None
    hint = {
        "invalid_auth": " The bot token is not valid; store a new one with `hz system credential set bot-token`.",
        "token_revoked": " The token was revoked; reinstall the app and store the new token.",
        "missing_scope": " The app lacks a scope; reinstall it from the manifest in `hz slack manifest`.",
        "not_allowed_token_type": " That token type cannot do this.",
    }.get(code, "")
    return SlackRefused(f"Slack refused {action} ({code}).{hint}")


def posting_target(identity: Identity, owner: str, channel: str) -> ChannelTarget:
    """The exact workspace/bot account, physical DM and owner-bound posting scope observed by one client."""
    return ChannelTarget(
        account=f"slack:{identity.team_id}:{identity.bot_user}",
        destination=channel,
        scope=f"slack:owner-dm:{owner}:chat.write:v1",
    )


@dataclass(frozen=True, slots=True, init=False)
class WebApi:
    """`SlackApi` over one immutable credential selection; every SDK call explicitly uses that pinned token."""

    _client: WebClient = field(repr=False)
    _token: str = field(repr=False)

    def __init__(self, token: str, timeout: float, base_url: str = "https://slack.com/api/") -> None:
        """Create the client; no request is made. `base_url` exists so tests can point at a local server."""
        object.__setattr__(self, "_token", token.strip())
        object.__setattr__(
            self, "_client", WebClient(token=token, timeout=int(timeout), base_url=base_url, retry_handlers=[])
        )

    def identity(self) -> Identity:  # noqa: D102
        try:
            reply = self._client.auth_test(token=self._token)
        except SlackApiError as error:
            raise _fail("auth.test", error) from None
        except Exception:  # noqa: BLE001 - never expose SDK or token-bearing transport errors
            raise HeinzelError("Slack identity could not be verified") from None
        team = reply.get("team_id")
        if not isinstance(team, str) or not re.fullmatch(r"T[A-Z0-9]{6,20}", team):
            raise HeinzelError("Slack returned an invalid workspace identity")
        user = reply.get("user_id")
        if not isinstance(user, str) or not re.fullmatch(r"[UW][A-Z0-9]{6,20}", user):
            raise HeinzelError("Slack returned an invalid posting account identity")
        return Identity(team, str(reply.get("team", "")), user)

    def open_dm(self, user: str) -> str:  # noqa: D102
        try:
            reply = self._client.conversations_open(users=[user], token=self._token)
        except SlackApiError as error:
            raise _fail("opening the direct message", error) from None
        except Exception:  # noqa: BLE001 - never expose SDK or token-bearing transport errors
            raise HeinzelError("Slack direct message could not be verified") from None
        data = reply.get("channel")
        channel = data.get("id") if isinstance(data, dict) else None
        if not isinstance(channel, str) or not re.fullmatch(r"D[A-Z0-9]{6,20}", channel):
            msg = "Slack did not open a direct message; refusing to post anywhere else"
            raise HeinzelError(msg)
        return channel

    def post(self, channel: str, text: str, blocks: list[dict[str, Any]]) -> str:  # noqa: D102
        try:
            reply = self._client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks,
                unfurl_links=False,
                unfurl_media=False,
                link_names=False,
                token=self._token,
            )
        except SlackApiError as error:
            raise _fail("the message", error) from None
        except Exception as error:  # noqa: BLE001 - the SDK raises transport errors of several types
            msg = f"Slack did not answer the message ({type(error).__name__}); it may or may not have been posted"
            raise SlackUnknown(msg) from None
        ts = reply.get("ts")
        if not isinstance(ts, str) or not re.fullmatch(r"[0-9]+\.[0-9]{1,6}", ts) or reply.get("channel") != channel:
            raise SlackUnknown("Slack returned an ambiguous message acknowledgement; do not retry")
        return ts

    def delivery_target(self, owner: str, team: str) -> ChannelTarget:  # noqa: D102
        if not owner or not team:
            raise SlackRefused("A Slack owner and workspace are required before selecting a posting target")
        who = self.identity()
        if who.team_id != team:
            raise SlackRefused("The bot token does not match slack.team; refusing to select a posting target")
        return posting_target(who, owner, self.open_dm(owner))

    def post_reviewed(
        self, target: ChannelTarget, owner: str, team: str, text: str, blocks: list[dict[str, Any]]
    ) -> str:  # noqa: D102
        # No credential read or fresh client follows verification: the exact client/token performs the mutation.
        if self.delivery_target(owner, team) != target:
            raise SlackRefused("Slack posting account, destination or scope changed; review the target again")
        return self.post(target.destination, text, blocks)

    def update(self, channel: str, ts: str, text: str, blocks: list[dict[str, Any]]) -> None:  # noqa: D102
        try:
            self._client.chat_update(channel=channel, ts=ts, text=text, blocks=blocks, token=self._token)
        except SlackApiError as error:
            raise _fail("the update", error) from None
        except Exception:  # noqa: BLE001 - never expose SDK or token-bearing transport errors
            raise HeinzelError("Slack did not confirm the message update") from None

    def display_name(self, user: str) -> str | None:  # noqa: D102
        try:
            reply = self._client.users_info(user=user, token=self._token)
        except SlackApiError:
            return None
        except Exception:  # noqa: BLE001 - never expose SDK or token-bearing transport errors
            raise HeinzelError("Slack display name could not be read") from None
        profile = reply.get("user")
        if not isinstance(profile, dict):
            raise HeinzelError("Slack returned an invalid display name response")
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
