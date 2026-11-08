"""Only an authenticated owning web instance can confirm its bound listener and loaded origin policy."""

import logging
import time

from heinzel import CurrentUser, HeinzelError, LocalWebRuntime

from heinzel_tailscale._mapping import Mapping

_LOG = logging.getLogger(__name__)
_EVENT = "tailscale.status.finish"


class SharingReadiness:
    """The existing call identity plus tokenless in-process facts; no new credential or discovery registry."""

    def __init__(self, runtime: LocalWebRuntime, user: CurrentUser) -> None:
        """Use only facts supplied by the trusted head and its current authenticated request."""
        self.runtime = runtime
        self.user = user

    def verifies(self, mapping: Mapping) -> bool:
        """Whether this authenticated web instance actually loaded this listener and exact external origin."""
        if mapping.origin not in self.runtime.loaded_origins:
            return False
        return self._owns(mapping)

    def _owns(self, mapping: Mapping) -> bool:
        """Whether an authenticated web call reached the very listener the mapping forwards to."""
        if self.runtime.port is None or self.runtime.port != mapping.backend_port:
            return False
        try:
            return self.user.context().authentication in {"web-session", "web-device"}
        except HeinzelError:
            return False

    def finish(self, mapping: Mapping, configured: frozenset[str]) -> bool | None:
        """Load the mapping's own origin when the saved request is complete but this web owner has not loaded it yet.

        A status read may call this: it changes neither Tailscale Serve nor the configuration, only adds the one
        origin the configuration already allows to this listener's policy, and keeps every origin already loaded, so
        no session is revoked. It is idempotent: once loaded it does nothing.

        Returns:
            True when it loaded the origin, False when loading failed, None when there was nothing for it to do.
        """
        loaded = self.runtime.loaded_origins
        if mapping.origin in loaded or mapping.origin not in configured or not self._owns(mapping):
            return None
        fields: dict[str, object] = {"operation": "status", "step": "finish", "plugin": "heinzel-tailscale"}
        fields["port"] = mapping.backend_port
        _LOG.info(_EVENT, extra={**fields, "phase": "start"})
        started = time.monotonic()
        try:
            self.runtime.apply_origins(loaded | {mapping.origin})
        except (HeinzelError, ValueError) as error:
            elapsed = round((time.monotonic() - started) * 1000)
            _LOG.error(
                _EVENT,
                extra={
                    **fields,
                    "phase": "end",
                    "outcome": "error",
                    "duration_ms": elapsed,
                    "error_type": type(error).__name__,
                    "error": str(error).splitlines()[0][:200],
                },
            )
            return False
        elapsed = round((time.monotonic() - started) * 1000)
        _LOG.info(_EVENT, extra={**fields, "phase": "end", "outcome": "ok", "duration_ms": elapsed})
        return True

    def apply_origins(self, origins: frozenset[str]) -> None:
        """Apply policy only in the process that owns the live web listener.

        CLI and MCP services have no bound listener and must only persist requested state. The web-owned service
        supplies its current validated origins here after each completed Serve transaction, before reporting status.
        """
        if self.runtime.port is not None:
            self.runtime.apply_origins(origins)
