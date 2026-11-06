"""Fixed credential and proxy boundaries for the plugin's SDK clients."""

import logging
from urllib.parse import urlsplit

from heinzel import HeinzelError

from heinzel_slack._vendor.slack_sdk import WebClient
from heinzel_slack._vendor.slack_sdk.proxy_env_variable_loader import load_http_proxy_from_env

# This unregistered logger cannot inherit host DEBUG handlers or configuration.
# SDK diagnostics may contain credentials; the owning adapter reports fixed errors.
SDK_LOGGER = logging.Logger("heinzel_slack.private_sdk", level=logging.CRITICAL + 1)
SDK_LOGGER.disabled = True
SDK_LOGGER.propagate = False
SDK_LOGGER.addHandler(logging.NullHandler())


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
        retry_handlers=None if retry else [],
        proxy=proxy,
        logger=SDK_LOGGER,
    )
    # The SDK constructor re-reads the environment for None; no I/O occurs there.
    # Restore the snapshot before any request, including a deliberately direct route.
    client.proxy = proxy
    return client
