"""Pure plans preserve unrelated Serve fields and refuse conflicting or public mappings."""

import copy
import re
from dataclasses import dataclass
from typing import Self, cast

from heinzel import HeinzelError

_PORT = 443


class SharingProblemError(HeinzelError):
    """A refusal with its one short status line for the pane; the full message stays the explanation."""

    def __init__(self, message: str, summary: str) -> None:
        """Keep the long message for the CLI and Details, and the short line (<= 60 characters) for the pane."""
        super().__init__(message)
        self.summary = summary


_DNS = re.compile(r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9-]+\Z")


@dataclass(frozen=True, slots=True)
class Mapping:
    """Only hz's root handler on one exact private HTTPS authority."""

    hostname: str
    port: int
    backend_port: int

    @classmethod
    def for_node(cls, hostname: str, backend_port: int, port: int = _PORT) -> Self:
        """Validate the node DNS name and explicit local/external ports before making a plan.

        Raises:
            HeinzelError: If either port is unsafe.
            SharingProblemError: If the reported name is not a tailnet DNS name.
        """
        name = hostname.removesuffix(".").lower()
        if not _DNS.fullmatch(name) or not name.endswith(".ts.net"):
            msg = "Tailscale did not report a valid tailnet DNS name; sign in and enable MagicDNS first."
            raise SharingProblemError(msg, "Turn on MagicDNS in Tailscale, then try again.")
        if not 1 <= backend_port <= 65535 or not 1 <= port <= 65535:  # noqa: PLR2004 - network port bounds
            msg = "The local backend and external HTTPS ports must be between 1 and 65535."
            raise HeinzelError(msg)
        return cls(name, port, backend_port)

    @property
    def authority(self) -> str:
        """Tailscale's Serve key includes the HTTPS port, including 443."""
        return f"{self.hostname}:{self.port}"

    @property
    def origin(self) -> str:
        """The browser origin omits the default HTTPS port."""
        return f"https://{self.hostname}" + ("" if self.port == _PORT else f":{self.port}")

    @property
    def clear_command(self) -> str:
        """The Tailscale command that removes only this root mapping, never other paths on the same port."""
        return f"tailscale serve --https={self.port} --set-path=/ off"

    @property
    def target(self) -> str:
        """The sole permitted target is the current app's loopback listener."""
        return f"http://127.0.0.1:{self.backend_port}"

    def matches(self, config: dict[str, object]) -> bool:
        """Whether this mapping has exactly the expected HTTPS handler and no public Funnel access."""
        try:
            return self._check(config) == {"Proxy": self.target} and _read_table(config, "TCP").get(str(self.port)) == {
                "HTTPS": True
            }
        except HeinzelError:
            return False

    def has_handler(self, config: dict[str, object]) -> bool:
        """Whether the root slot is already occupied, including a dormant or empty manual handler.

        Raises:
            HeinzelError: If the configuration cannot be inspected safely.
        """
        self._check(config)
        return "/" in _read_table(_read_table(_read_table(config, "Web"), self.authority), "Handlers")

    def enable(self, config: dict[str, object]) -> dict[str, object]:
        """Add the private handler without replacing any conflicting handler or unrelated value.

        Raises:
            SharingProblemError: If existing configuration conflicts with private hz sharing.
        """
        handler = self._check(config)
        if handler and handler != {"Proxy": self.target}:
            msg = (
                "Another service already uses this Tailscale web address. Choose a different sharing port in Settings."
            )
            raise SharingProblemError(msg, f"Port {self.port} is taken. Pick another port in Settings.")
        result = copy.deepcopy(config)
        tcp = _table(result, "TCP")
        tcp[str(self.port)] = {"HTTPS": True}
        _table(_table(_table(result, "Web"), self.authority), "Handlers")["/"] = {"Proxy": self.target}
        return result

    def disable(self, config: dict[str, object]) -> dict[str, object]:
        """Remove only the matching handler, preserving other paths, ports and service fields.

        Raises:
            HeinzelError: If the mapping has changed or is not owned by hz.
        """
        handler = self._check(config)
        if not handler:
            return copy.deepcopy(config)
        if handler != {"Proxy": self.target}:
            msg = (
                "The address hz shared now points somewhere else, so hz left it alone. "
                "To see it, run: tailscale serve status."
            )
            raise HeinzelError(msg)
        result = copy.deepcopy(config)
        web = _table(result, "Web")
        authority = _table(web, self.authority)
        handlers = _table(authority, "Handlers")
        del handlers["/"]
        if not handlers and set(authority) == {"Handlers"}:
            del web[self.authority]
            # Another host on the same HTTPS port still owns the listener.
            if not any(key.endswith(f":{self.port}") for key in web):
                _table(result, "TCP").pop(str(self.port), None)
        return result

    def _check(self, config: dict[str, object]) -> dict[str, object]:
        funnel = _read_table(config, "AllowFunnel")
        if funnel.get(self.authority):
            msg = "Tailscale already shares this port with the whole internet (Funnel). hz did not use or change it."
            raise SharingProblemError(msg, f"Port {self.port} is public (Funnel). Pick another port.")
        tcp = _read_table(config, "TCP").get(str(self.port))
        if tcp is not None and tcp != {"HTTPS": True}:
            msg = "Tailscale uses this port for something else. hz left it alone."
            raise SharingProblemError(msg, f"Port {self.port} is taken. Pick another port in Settings.")
        if config.get("Foreground"):
            msg = "A tailscale serve command is running in a terminal. hz left it alone."
            raise SharingProblemError(msg, "Stop tailscale serve in the terminal, then try again.")
        handlers = _read_table(_read_table(_read_table(config, "Web"), self.authority), "Handlers")
        return _read_table(handlers, "/")


def _read_table(table: dict[str, object], key: str) -> dict[str, object]:
    value = table.get(key, {})
    if not isinstance(value, dict):
        msg = "Tailscale returned an unsupported Serve configuration; no changes were made."
        raise HeinzelError(msg)
    return cast("dict[str, object]", value)


def _table(table: dict[str, object], key: str) -> dict[str, object]:
    if key not in table:
        table[key] = {}
    return _read_table(table, key)
