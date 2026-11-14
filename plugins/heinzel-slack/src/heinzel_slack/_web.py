# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# pyright: reportOptionalMemberAccess=false
"""Any Slack Web API method behind one small seam, with Slack's rate limits and pagination handled in one place.

`WebCall` is the seam: one method name and its arguments in, Slack's JSON reply out. `SdkWeb` implements it with the
official SDK and a pinned bot token, reads form-encoded and writes as JSON; tests replace it with a fake. `Web` adds the
policy every caller shares: a 429 waits for Slack's `Retry-After` (bounded), cursors are followed, and errors carry
Slack's error code and nothing else, never a token or a reply body.
"""

import math
import time
from collections.abc import Callable, Iterator
from typing import Any, Protocol, cast

from heinzel import HeinzelError

from heinzel_slack._sdk import sdk_proxy, sdk_web_client
from heinzel_slack._slack import SlackUnknown, refusal
from heinzel_slack._vendor.slack_sdk import WebClient
from heinzel_slack._vendor.slack_sdk.errors import SlackApiError

MAX_RETRY_AFTER = 30.0
"""Longest single wait Slack's `Retry-After` may ask for before the call gives up instead."""
MAX_RATE_WAIT = 60.0
"""Longest total wait for rate limits within one call."""
MAX_ATTEMPTS = 6
"""Most tries of one call, so a `Retry-After: 0` cannot loop."""
PAGE = 200
"""Items asked for per page; Slack recommends no more than 200."""


def obj(value: object) -> dict[str, Any]:
    """`value` as a JSON object from Slack, or an empty one when it is anything else."""
    return cast("dict[str, Any]", value) if isinstance(value, dict) else {}


def objs(value: object) -> list[dict[str, Any]]:
    """The JSON objects in `value` when it is a list; anything else in it is skipped."""
    items = cast("list[object]", value) if isinstance(value, list) else []
    return [cast("dict[str, Any]", item) for item in items if isinstance(item, dict)]


def text_of(value: object) -> str | None:
    """`value` when it is a non-empty string, else None."""
    return value if isinstance(value, str) and value else None


class RateLimited(HeinzelError):
    """Slack answered 429: nothing was done, and it may be tried again after `retry_after` seconds."""

    def __init__(self, retry_after: float) -> None:
        """Remember how long Slack asked to wait."""
        self.retry_after = retry_after
        super().__init__(f"Slack is rate limiting this app; try again in {retry_after:.0f} s")


class WebCall(Protocol):
    """One Slack Web API method call."""

    def call(self, method: str, params: dict[str, Any], *, write: bool) -> dict[str, Any]:
        """Call `method` with `params`; Slack's reply when `ok`.

        Raises:
            RateLimited: On 429.
            SlackRefused: If Slack definitely refused (nothing changed).
            SlackUnknown: If a write may or may not have happened.
            HeinzelError: If a read failed.
        """
        ...


def _retry_after(error: SlackApiError) -> float | None:
    response = error.response
    if response is None or response.status_code != 429:  # noqa: PLR2004 - HTTP 429 Too Many Requests
        return None
    raw = (response.headers or {}).get("Retry-After") or (response.headers or {}).get("retry-after")
    try:
        return max(0.0, float(raw)) if raw is not None else 1.0
    except (TypeError, ValueError):
        return 1.0


class SdkWeb:
    """`WebCall` over the official SDK with one pinned bot token: reads form-encoded, writes with a JSON body.

    The SDK sends every method as POST, as Slack accepts; the token travels in the Authorization header only.
    """

    def __init__(self, token: str, timeout: float, base_url: str = "https://slack.com/api/") -> None:
        """Create the client; nothing is sent. `base_url` exists so tests can point at a local server."""
        self._token = token.strip()
        self._client: WebClient = sdk_web_client(
            token=self._token, timeout=max(1, math.ceil(timeout)), base_url=base_url, proxy=sdk_proxy()
        )

    def __repr__(self) -> str:
        """Never show the token."""
        return "SdkWeb()"

    def call(self, method: str, params: dict[str, Any], *, write: bool) -> dict[str, Any]:  # noqa: D102
        # The SDK moves a `token` argument into the Authorization header, never into the URL or the body.
        try:
            if write:
                reply = self._client.api_call(method, json={**params, "token": self._token})
            else:
                reply = self._client.api_call(method, params={**params, "token": self._token})
        except SlackApiError as error:
            wait = _retry_after(error)
            if wait is not None:
                raise RateLimited(wait) from None
            if write:
                raise refusal(method, error) from None
            code = str(error.response.get("error", "unknown")) if error.response is not None else "unknown"
            raise HeinzelError(f"Slack refused {method} ({code})") from None
        except Exception as error:  # noqa: BLE001 - never expose SDK or token-bearing transport errors
            if write:
                msg = f"Slack did not answer {method} ({type(error).__name__}); it may or may not have happened"
                raise SlackUnknown(msg) from None
            raise HeinzelError(f"Slack did not answer {method} ({type(error).__name__})") from None
        data = reply.data
        if not isinstance(data, dict):
            raise HeinzelError(f"Slack returned an invalid reply to {method}")
        return data


class Web:
    """The policy over a `WebCall`: bounded waits for rate limits, followed cursors."""

    def __init__(self, raw: WebCall, sleep: Callable[[float], None] = time.sleep) -> None:
        """Wrap `raw`; `sleep` is replaceable so tests need not wait."""
        self.raw = raw
        self._sleep = sleep

    def read(self, method: str, params: dict[str, Any], *, wait: bool = True) -> dict[str, Any]:
        """A read, waiting out rate limits up to `MAX_RATE_WAIT` in total; with `wait=False`, one attempt.

        A caller with its own deadline (a waiting question) reads with `wait=False` and handles `RateLimited` itself,
        so no sleep in here can outlast its timeout or its `cancel`.

        Raises:
            RateLimited: If `wait` is False and Slack answered 429, or Slack keeps rate limiting.
            HeinzelError: If Slack fails.
        """
        if not wait:
            return self.raw.call(method, params, write=False)
        return self._with_limits(method, params, write=False)

    def write(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """A write. A 429 is a definite refusal (nothing was done), so it is retried like a read.

        Raises:
            SlackRefused: If Slack refused.
            SlackUnknown: If it may or may not have happened; never retried.
            HeinzelError: If Slack keeps rate limiting.
        """
        return self._with_limits(method, params, write=True)

    def pages(self, method: str, params: dict[str, Any], key: str) -> Iterator[dict[str, Any]]:
        """Every item under `key` across all pages of a cursor-paginated read.

        Raises:
            HeinzelError: As `read`, or if a page is malformed.
        """
        cursor = ""
        while True:
            page = self.read(method, {**params, "limit": PAGE, **({"cursor": cursor} if cursor else {})})
            if not isinstance(page.get(key, []), list):
                raise HeinzelError(f"Slack returned an invalid page from {method}")
            yield from objs(page.get(key, []))
            cursor = text_of(obj(page.get("response_metadata")).get("next_cursor")) or ""
            if not cursor:
                return

    def _with_limits(self, method: str, params: dict[str, Any], *, write: bool) -> dict[str, Any]:
        waited = 0.0
        for attempt in range(MAX_ATTEMPTS):
            try:
                return self.raw.call(method, params, write=write)
            except RateLimited as limited:
                wait = limited.retry_after
                if attempt == MAX_ATTEMPTS - 1 or wait > MAX_RETRY_AFTER or waited + wait > MAX_RATE_WAIT:
                    raise
                self._sleep(wait)
                waited += wait
        raise AssertionError  # pragma: no cover - the last attempt returns or raises
