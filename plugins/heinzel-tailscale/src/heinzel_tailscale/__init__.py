"""Private web sharing through the installed Tailscale client, with the existing hz authentication boundary."""

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


# A core whose ToggleControl has `status`, `problem` and `explanation` shows the short line and a Details text; older
# cores get the short line as the only detail line, so the pane never shows the long explanation inline either way.
_PANE_LINES = {"status", "problem", "explanation"} <= ToggleControl.model_fields.keys()


@module.status(source="status", slots={"footer": True, "sidebar": False})
def sharing(state: SharingState) -> StatusItem:
    """A compact provider-owned status icon with the same explicit control as Settings.

    The switch shows the person's choice (`requested`); `checked` says it is live. One short line says what is going
    on, and the full message is only the Details text.
    """
    ready = state.state == "ready"
    # A cause the person must fix gets Try again only once they asked for sharing; before that the switch is the way.
    problem = state.summary if state.problem and state.desired_enabled else None
    status = None if problem else state.summary
    lines = {"status": status, "problem": problem, "explanation": state.message[:280]} if _PANE_LINES else {}
    return StatusItem(
        text="Tailscale",
        icon="link",
        tone="ok" if ready else "warn" if state.state in {"error", "blocked"} else "neutral",
        detail=[] if _PANE_LINES or not state.summary else [DetailLine(text=state.summary)],
        toggle=ToggleControl(
            label="Share over Tailscale",
            checked=ready,
            requested=state.desired_enabled,
            enable=RunOperation(operation="enable"),
            disable=RunOperation(operation="disable"),
            url=state.origin if ready else None,
            apply_settings=state.apply_settings,
            **lines,
        ),
    )


__all__ = ["Sharing", "SharingActions", "SharingState", "TailscaleCli", "TailscaleSettings", "module"]
