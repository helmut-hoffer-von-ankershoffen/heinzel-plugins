"""Fixed credential and proxy boundaries for the plugin's SDK clients."""

import logging
from urllib.error import HTTPError
from urllib.parse import urlsplit

from heinzel import HeinzelError

from heinzel_slack._vendor.slack_sdk import WebClient
from heinzel_slack._vendor.slack_sdk.http_retry import RetryHandler, default_retry_handlers
from heinzel_slack._vendor.slack_sdk.http_retry.request import HttpRequest
from heinzel_slack._vendor.slack_sdk.http_retry.response import HttpResponse
from heinzel_slack._vendor.slack_sdk.http_retry.state import RetryState
from heinzel_slack._vendor.slack_sdk.proxy_env_variable_loader import load_http_proxy_from_env

# This unregistered logger cannot inherit host DEBUG handlers or configuration.
# SDK diagnostics may contain credentials; the owning adapter reports fixed errors.
SDK_LOGGER = logging.Logger("heinzel_slack.private_sdk", level=logging.CRITICAL + 1)
SDK_LOGGER.disabled = True
SDK_LOGGER.propagate = False
SDK_LOGGER.addHandler(logging.NullHandler())


class CloseHttpError(RetryHandler):
    """Never retries; closes the HTTP error response (a 429, a 5xx) the SDK has read but leaves open.

    The SDK asks every retry handler about an HTTP error after reading its body and never closes it, so each such
    answer would hold a socket until garbage collection. This handler runs first and only closes it.
    """

    def __init__(self) -> None:
        """Ask on the first attempt; the SDK skips a handler whose retry count is used up."""
        super().__init__(max_retry_count=1_000_000)

    def _can_retry(
        self,
        *,
        state: RetryState,
        request: HttpRequest,
        response: HttpResponse | None = None,
        error: Exception | None = None,
    ) -> bool:
        del state, request, response
        if isinstance(error, HTTPError):
            error.close()
        return False


def sdk_proxy() -> str | None:
    """Snapshot supported proxy configuration before constructing any SDK client."""
    value = load_http_proxy_from_env(SDK_LOGGER)
    if value is None:
        return None
    try:
        parsed = urlsplit(value)
        valid = (
            parsed.scheme == "http"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and parsed.path in {"", "/"}
            and not parsed.query
            and not parsed.fragment
            and (parsed.port is None or 1 <= parsed.port <= 65535)
            and not any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value)
        )
    except ValueError:
        valid = False
    if not valid:
        raise HeinzelError("Slack requires an unauthenticated HTTP proxy or a direct connection") from None
    return value


def sdk_web_client(
    *,
    proxy: str | None,
    token: str | None = None,
    timeout: int = 30,
    base_url: str = "https://slack.com/api/",
    retry: bool = False,
) -> WebClient:
    """Pin the validated proxy snapshot and isolate SDK diagnostics from host logging."""
    client = WebClient(
        token=token,
        timeout=timeout,
        base_url=base_url,
        retry_handlers=[CloseHttpError(), *(default_retry_handlers() if retry else [])],
        proxy=proxy,
        logger=SDK_LOGGER,
    )
    # The SDK constructor re-reads the environment for None; no I/O occurs there.
    # Restore the snapshot before any request, including a deliberately direct route.
    client.proxy = proxy
    return client
