"""Private web sharing through the installed Tailscale client, with the existing hz authentication boundary."""

import re
from textwrap import wrap

from heinzel import DetailLine, Module, NavSettings, RunOperation, StatusItem, ToggleControl

from heinzel_tailscale._cli import TailscaleCli
from heinzel_tailscale._localapi import ServeStore
from heinzel_tailscale._lock import SharingLock
from heinzel_tailscale._models import SharingState, TailscaleSettings
from heinzel_tailscale._readiness import SharingReadiness
from heinzel_tailscale._service import Sharing, SharingActions

module = Module("tailscale", "Private web sharing through Tailscale Serve.")
module.nav(title="Tailscale", icon="link", settings=NavSettings(sections=("tailscale",), group="computer"))
module.settings(TailscaleSettings)
module.service(TailscaleCli)
module.service(ServeStore)
module.service(SharingLock)
module.service(SharingReadiness)
module.service(Sharing)
module.service(SharingActions)


@module.operation(private=True)
def status(service: Sharing) -> SharingState:
    """Show private sharing readiness without changing Tailscale or configuration."""
    return service.status()


@module.operation(private=True, read_only=False)
def enable(service: SharingActions) -> SharingState:
    """Share hz privately over Tailscale, preserving existing services and requiring authenticated readiness.

    Raises:
        HeinzelError: If login, source ownership, conflicting mappings or uncertain outcomes require attention.
    """
    return service.enable()


@module.operation(private=True, read_only=False)
def disable(service: SharingActions) -> SharingState:
    """Stop only hz's private Serve mapping and remove only the origin permission this plugin added.

    Raises:
        HeinzelError: If changed ownership or a partial/uncertain outcome needs inspection.
    """
    return service.disable()


_WIDTH = 80


def sentences(message: str) -> list[str]:
    """Split a message into popup bullets: one per line break or sentence, wrapped only when a line is too long."""
    parts = [
        part for line in message.splitlines() for part in re.split(r"(?<=[.!?])\s+(?=[A-Z])", line.strip()) if part
    ]
    return [piece for part in parts for piece in (wrap(part, width=_WIDTH) if len(part) > _WIDTH else [part])]


@module.status(source="status", slots={"footer": True, "sidebar": False})
def sharing(state: SharingState) -> StatusItem:
    """A compact provider-owned status icon with the same explicit control as Settings."""
    ready = state.state == "ready"
    return StatusItem(
        text="Tailscale",
        icon="link",
        tone="ok" if ready else "warn" if state.state in {"error", "blocked"} else "neutral",
        detail=[DetailLine(text=line) for line in sentences(state.message)],
        toggle=ToggleControl(
            label="Share over Tailscale",
            checked=ready,
            requested=state.desired_enabled,
            enable=RunOperation(operation="enable"),
            disable=RunOperation(operation="disable"),
            url=state.origin if ready else None,
            apply_settings=state.apply_settings,
        ),
    )


__all__ = ["Sharing", "SharingActions", "SharingState", "TailscaleCli", "TailscaleSettings", "module"]
