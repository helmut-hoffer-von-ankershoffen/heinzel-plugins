"""Read actual sharing state and compose one explicit action from existing configuration and conditional Serve APIs."""

import logging
from typing import TYPE_CHECKING, cast
from urllib.parse import urlsplit

from heinzel import Config, ConfigEditor, HeinzelError, Settings

from heinzel_tailscale._cli import TailscaleCli
from heinzel_tailscale._localapi import Connection, ServeStore
from heinzel_tailscale._lock import SharingLock
from heinzel_tailscale._mapping import Mapping, SharingProblemError
from heinzel_tailscale._models import SharingIntent, SharingState, TailscaleSettings
from heinzel_tailscale._readiness import SharingReadiness

if TYPE_CHECKING:
    from pydantic import JsonValue


_LOG = logging.getLogger(__name__)
SIGN_IN = "Sign in to Tailscale, then try again."


class Sharing:
    """Private sharing facts; reading them never replays a persisted request."""

    def __init__(self, settings: Settings, cli: TailscaleCli, config: Config, readiness: SharingReadiness) -> None:
        """Use the existing profile, CLI and trusted runtime-facts services."""
        self.settings = settings
        self.cli = cli
        self.config = config
        self.readiness = readiness

    def choices(self) -> TailscaleSettings:
        """Read the latest explicit sharing intent without executing it."""
        return self.config.reread().settings(TailscaleSettings, "tailscale")

    def origins(self) -> frozenset[str]:
        """Read the effective origin setting; the head separately reports what it actually loaded."""
        return self.config.reread().settings(Settings, "hz").ui_allowed_origins

    def mapping(self) -> Mapping:
        """Plan only the observed node's own private origin and actual or configured backend port.

        Raises:
            HeinzelError: If the installed client is unavailable or reports unsafe facts.
            SharingProblemError: If the client is signed out or lacks MagicDNS or HTTPS certificates.
        """
        node = _node(self.cli.json(("status", "--json", "--peers=false")))
        if node.get("BackendState") != "Running":
            msg = "Open Tailscale and sign in, then try sharing again."
            raise SharingProblemError(msg, SIGN_IN)
        return self._mapping(node)

    def _mapping(self, node: dict[str, object]) -> Mapping:
        own = node.get("Self")
        name = cast("dict[str, object]", own).get("DNSName") if isinstance(own, dict) else None
        if not isinstance(name, str):
            msg = "Tailscale did not report a node DNS name; check MagicDNS in the Tailscale app."
            raise SharingProblemError(msg, "Turn on MagicDNS in Tailscale, then try again.")
        choices = self.choices()
        # A separate CLI/MCP process cannot prove a new override; preserve the explicit previous target until a web
        # owner binds real facts, rather than silently moving an existing mapping back to the configured default.
        old = choices.intent
        port = self.readiness.runtime.port or (old.backend_port if old and old.enabled else self.settings.ui_port)
        mapping = Mapping.for_node(name, port, choices.https_port)
        certificates = node.get("CertDomains")
        if not isinstance(certificates, list) or mapping.hostname not in certificates:
            msg = "Enable HTTPS certificates for this node in Tailscale's own consent flow, then try sharing again."
            raise SharingProblemError(msg, "Turn on HTTPS certificates in Tailscale.")
        return mapping

    def status(self) -> SharingState:
        """Report actual state without logging in, changing configuration or replaying the last requested action."""
        choices = self.choices()
        desired = choices.intent.enabled if choices.intent else False
        if self.cli.executable() is None:
            return SharingState(
                state="unavailable",
                installed=False,
                logged_in=False,
                desired_enabled=desired,
                summary="Install Tailscale and sign in first.",
                problem=True,
                message="Install Tailscale and sign in before sharing the web app.",
            )
        try:
            node = _node(self.cli.json(("status", "--json", "--peers=false")))
        except HeinzelError as error:
            return SharingState(
                state="error",
                installed=True,
                logged_in=False,
                desired_enabled=desired,
                summary="Tailscale did not answer. Try again.",
                problem=True,
                message=str(error),
            )
        if node.get("BackendState") != "Running":
            return SharingState(
                state="login-required",
                installed=True,
                logged_in=False,
                desired_enabled=desired,
                summary=SIGN_IN,
                problem=True,
                message="Open Tailscale and sign in, then try sharing again.",
            )
        try:
            mapping = self._mapping(node)
            config = _config(self.cli.json(("serve", "status", "--json")))
            return self._state(mapping, config, desired)
        except HeinzelError as error:
            return SharingState(
                state="blocked",
                installed=True,
                logged_in=True,
                desired_enabled=desired,
                summary=error.summary
                if isinstance(error, SharingProblemError)
                else "Tailscale refused this. Try again.",
                problem=True,
                message=str(error),
            )

    def _state(self, mapping: Mapping, config: dict[str, object], desired: bool) -> SharingState:
        old = self.choices().intent
        if old:
            previous = intent_mapping(old)
            if previous.matches(config):
                mapping = previous
        mapping.enable(config)
        present = mapping.matches(config)
        configured = self.origins()
        finished: bool | None = None
        if present and old is not None and old.enabled and old.phase == "owned":
            # The saved request is complete in Tailscale and the configuration: the web owner finishes it here, so
            # turning sharing on is one step even when the request came from the CLI or the server restarted.
            finished = self.readiness.finish(mapping, configured)
        expected_origins: list[JsonValue] = []
        expected_origins.extend(sorted(configured))
        apply: dict[str, JsonValue] = (
            {"hz.ui_allowed_origins": expected_origins}
            if self.readiness.runtime.port is not None and configured != self.readiness.runtime.loaded_origins
            else {}
        )
        if not present:
            incomplete = old is not None and old.phase in {"enabling", "disabling"} and mapping.has_handler(config)
            return SharingState(
                state="blocked" if incomplete else "off",
                installed=True,
                logged_in=True,
                desired_enabled=desired,
                origin=mapping.origin,
                target=mapping.target,
                apply_settings=apply,
                summary="Last change did not finish. Check Tailscale Serve."
                if incomplete
                else "Tailscale stopped sharing. Try again."
                if desired
                else None,
                problem=incomplete or desired,
                message=(
                    "Sharing is off, but an earlier change did not finish.\n"
                    "To see what is left, run:\ntailscale serve status\n"
                    f"To delete what is left of the mapping, run:\n{mapping.clear_command}"
                )
                if incomplete
                else "Sharing is switched on in hz, but Tailscale no longer forwards to it. Try again to set it up."
                if desired
                else "Private web sharing is off.",
            )
        if old is None or old.phase != "owned":
            return SharingState(
                state="blocked",
                installed=True,
                logged_in=True,
                desired_enabled=desired,
                mapped=True,
                origin=mapping.origin,
                target=mapping.target,
                apply_settings=apply,
                summary="hz did not set this up. Check Tailscale Serve.",
                problem=True,
                message=(
                    "Tailscale already shares this app, and hz did not set that up.\n"
                    "So hz left it alone. You can keep it as it is.\n"
                    f"To let hz manage sharing, delete that mapping with this command:\n{mapping.clear_command}\n"
                    "Then switch sharing on here."
                ),
            )
        ready = self.readiness.verifies(mapping) and mapping.origin in configured
        web = self.readiness.runtime.port
        moved = web is not None and web != mapping.backend_port
        summary, message = (
            (None, "Private sharing is ready for an authenticated browser.")
            if ready
            else (
                "Set up for another hz port. Try again to move it.",
                (
                    f"Tailscale forwards to hz on port {mapping.backend_port}, but this hz runs on port {web}.\n"
                    "Try again to forward Tailscale to this hz."
                ),
            )
            if moved
            else (
                "Could not finish turning it on. Try again.",
                (
                    "Sharing is set up in Tailscale, but this hz web app could not load its address. Try again; if "
                    "it keeps failing, the hz log has the event tailscale.status.finish."
                ),
            )
            if finished is False
            else (
                "Turning on…",
                (
                    "Sharing is set up in Tailscale. The hz web app finishes turning it on the next time it shows "
                    "this status."
                ),
            )
        )
        return SharingState(
            state="ready" if ready else "apply-required",
            installed=True,
            logged_in=True,
            desired_enabled=desired,
            mapped=True,
            origin=mapping.origin,
            target=mapping.target,
            apply_settings=apply,
            summary=summary,
            problem=moved or finished is False,
            message=message,
        )


class SharingActions:
    """An explicit enable/disable gesture changes only the requested mapping and its own origin permission."""

    def __init__(self, sharing: Sharing, store: ServeStore, editor: ConfigEditor, lock: SharingLock) -> None:
        """Compose existing owner-scoped configuration and one conditional local Serve transaction."""
        self.sharing = sharing
        self.store = store
        self.editor = editor
        self.lock = lock
        self._moves: set[tuple[int, int]] = set()

    def enable(self) -> SharingState:
        """Configure private sharing after fresh conflict checks; readiness is confirmed only by a web owner.

        Raises:
            HeinzelError: If another service conflicts, source ownership prevents applying or the result is uncertain.
        """
        with self.lock.hold():
            mapping = self.sharing.mapping()
            choices = self.sharing.choices()
            connection = self.store.connect()
            snapshot = self.store.read(connection)
            planned = snapshot.config
            old = choices.intent
            owned = old is not None and old.phase in {"owned", "disabling"}
            planned, retired = _moved(old, mapping, planned) if old is not None and owned else (planned, None)
            if not owned and mapping.has_handler(planned):
                msg = (
                    f"Tailscale already shares this app at {mapping.origin}, and hz did not set that up, "
                    "so hz did not change it. To let hz manage sharing instead, "
                    f"delete that mapping with: {mapping.clear_command}"
                )
                raise HeinzelError(msg)
            planned = mapping.enable(planned)
            added = bool(
                old
                and old.phase in {"enabling", "owned", "disabling"}
                and old.origin == mapping.origin
                and old.added_origin
            )
            intent = SharingIntent(
                enabled=True,
                origin=mapping.origin,
                backend_port=mapping.backend_port,
                https_port=mapping.port,
                added_origin=added,
                phase="owned" if owned and planned == snapshot.config else "enabling",
            )
            self.editor.write("tailscale.intent", intent)
            change = self.editor.change_list("hz.ui_allowed_origins", add=(mapping.origin,))
            intent = intent.model_copy(update={"added_origin": added or mapping.origin in change.added})
            self.editor.write("tailscale.intent", intent)
            if mapping.origin not in self.sharing.origins():
                msg = "A higher-priority configuration source prevents applying the origin; Serve was not changed."
                raise HeinzelError(msg)
            if planned != snapshot.config:
                try:
                    self.store.write(connection, snapshot, planned)
                except HeinzelError:
                    if old is not None and owned:
                        self._keep(old, connection)
                    raise
            if not mapping.matches(self.store.read(connection).config):
                msg = (
                    "hz could not confirm that sharing is set up in Tailscale. "
                    "To see the current state, run: tailscale serve status. Then try again."
                )
                raise HeinzelError(msg)
            self.editor.write("tailscale.intent", intent.model_copy(update={"phase": "owned"}))
            if retired is not None:
                self.editor.change_list("hz.ui_allowed_origins", remove=(retired,))
            self.sharing.readiness.apply_origins(self.sharing.origins())
            return self.sharing.status()

    def _keep(self, old: SharingIntent, connection: Connection) -> None:
        """A move that left hz's own mapping exactly in place keeps it owned, so Try again can still move it."""
        try:
            if intent_mapping(old).matches(self.store.read(connection).config):
                self.editor.write("tailscale.intent", old)
        except HeinzelError:
            # Unknown outcome: the saved request stays as written and status asks to check Tailscale Serve.
            _LOG.warning("tailscale.enable.keep", extra={"plugin": "heinzel-tailscale", "outcome": "error"})

    def heal(self) -> SharingState:
        """Report status; a web owner first moves hz's own mapping that still forwards to another hz port to itself.

        This is the startup self-heal: the first status read of a restarted hz on a new port does what Try again (or
        switching off and on) does, without a click. It never touches a handler hz did not set, a switched-off request
        or a call from the CLI or MCP. It tries once per move; if that fails, the status says so and Try again stays.
        """
        state = self.sharing.status()
        old = self.sharing.choices().intent
        port = self.sharing.readiness.runtime.port
        if (
            port is None
            or old is None
            or not old.enabled
            or old.phase != "owned"
            or not state.mapped
            or state.target != f"http://127.0.0.1:{old.backend_port}"
            or old.backend_port == port
            or not self.sharing.readiness.web_owner()
            or (old.backend_port, port) in self._moves
        ):
            return state
        # One automatic attempt per move and process; after a failure, Try again is the way, never a refresh loop.
        self._moves.add((old.backend_port, port))
        fields = {"operation": "status", "step": "move", "plugin": "heinzel-tailscale", "port": port}
        try:
            moved = self.enable()
        except HeinzelError as error:
            _LOG.warning(
                "tailscale.status.move", extra={**fields, "outcome": "error", "error": str(error).splitlines()[0][:200]}
            )
            return self.sharing.status()
        _LOG.info("tailscale.status.move", extra={**fields, "outcome": "ok", "previous_port": old.backend_port})
        return moved

    def disable(self) -> SharingState:
        """Stop only hz's still-matching mapping, preserving unrelated services and manually approved origins.

        Raises:
            HeinzelError: If the mapping changed or a partial/uncertain result needs inspection.
        """
        with self.lock.hold():
            old = self.sharing.choices().intent
            if old is None or old.phase in {"unowned", "released"}:
                return self.sharing.status()
            mapping = intent_mapping(old)
            connection = self.store.connect()
            snapshot = self.store.read(connection)
            if old.phase == "enabling" and mapping.has_handler(snapshot.config):
                self.editor.write("tailscale.intent", old.model_copy(update={"enabled": False}))
                msg = (
                    "An earlier attempt to turn sharing on may or may not have finished, so hz cannot tell "
                    "whether it owns the setup. To see the current state, run: tailscale serve status."
                )
                raise HeinzelError(msg)
            planned = mapping.disable(snapshot.config)
            intent = SharingIntent(
                enabled=False,
                origin=mapping.origin,
                backend_port=mapping.backend_port,
                https_port=mapping.port,
                added_origin=old.added_origin,
                phase="disabling",
            )
            self.editor.write("tailscale.intent", intent)
            if planned != snapshot.config:
                self.store.write(connection, snapshot, planned)
            if mapping.has_handler(self.store.read(connection).config):
                msg = (
                    "Sharing is still set up in Tailscale, so hz cannot say it is off. "
                    "To see the current state, run: tailscale serve status. Then try again."
                )
                raise HeinzelError(msg)
            intent = intent.model_copy(update={"phase": "released"})
            self.editor.write("tailscale.intent", intent)
            if intent.added_origin:
                self.editor.change_list("hz.ui_allowed_origins", remove=(mapping.origin,))
                # Released mappings are never retried; a later manual mapping/grant cannot become ours again.
                self.editor.write("tailscale.intent", intent.model_copy(update={"added_origin": False}))
            self.sharing.readiness.apply_origins(self.sharing.origins())
            return self.sharing.status()


def _moved(old: SharingIntent, mapping: Mapping, config: dict[str, object]) -> tuple[dict[str, object], str | None]:
    """Plan moving hz's own mapping to a new port or address, as switching off and on does.

    Returns:
        The configuration without the previous mapping, and the origin hz added for it that is no longer used.

    Raises:
        HeinzelError: If the previous address now points at a handler hz did not set; it is never replaced.
    """
    previous = intent_mapping(old)
    if previous == mapping:
        return config, None
    retired = previous.origin if previous.origin != mapping.origin and old.added_origin else None
    return previous.disable(config), retired


def intent_mapping(intent: SharingIntent) -> Mapping:
    """Reconstruct the exact owned target; a malformed origin never becomes a mutation target.

    Raises:
        HeinzelError: If persisted intent is not the canonical origin of a valid tailnet node.
    """
    try:
        parsed = urlsplit(intent.origin)
    except ValueError as error:
        msg = "The saved sharing address is not valid, so hz changed nothing in Tailscale."
        raise HeinzelError(msg) from error
    mapping = Mapping.for_node(parsed.hostname or "", intent.backend_port, intent.https_port)
    if mapping.origin != intent.origin:
        msg = "The saved sharing address is not valid, so hz changed nothing in Tailscale."
        raise HeinzelError(msg)
    return mapping


def _config(value: object) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        msg = "Tailscale returned an unsupported Serve configuration; no changes were made."
        raise HeinzelError(msg)
    return cast("dict[str, object]", value)


def _node(value: object) -> dict[str, object]:
    """Narrow untrusted vendor JSON before inspecting its node facts."""
    return cast("dict[str, object]", value) if isinstance(value, dict) else {}
