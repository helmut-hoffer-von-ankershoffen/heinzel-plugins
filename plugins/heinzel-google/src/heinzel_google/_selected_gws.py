"""Map the owner's selected GWS command to its existing native binary, without running a launcher.

The pinned wrapper files are byte matches to the npm 0.22.5 package, not publisher authentication. A host must
independently verify its selected configuration, installed plugin authority and exact human-approved read grant.
"""

import hashlib
import os
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from heinzel import Config, CurrentUser, HeinzelError

from heinzel_google._existing_lease import CapturedGwsRead, binary_digest
from heinzel_google._gws import GoogleSession, Process
from heinzel_google._models import GoogleSettings

_WRAPPER_FILES = {
    "run.js": "15ab1bf9506a63201feba50335ec6e0a0fcfd1a781e69139e43193b38ea8c0b0",
    "platform.js": "896fe379a055aea6b1619059c6c04728e555cec9c6718c7d5514e9dbc94eccdd",
    "package.json": "2b14e8400ff43eeeab45ba19db2ee6aa6d2a64124c3dc2defb3b7aac5f6231ed",
}
_MAX_WRAPPER_BYTES = 1_000_000


def source_digest(path: Path) -> str:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as handle:
            metadata = os.fstat(handle.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > _MAX_WRAPPER_BYTES:
                raise ValueError  # noqa: TRY301
            data = handle.read(_MAX_WRAPPER_BYTES + 1)
            if len(data) != metadata.st_size:
                raise ValueError  # noqa: TRY301
            return hashlib.sha256(data).hexdigest()
    except (OSError, ValueError):
        msg = "The selected Google command changed or is unavailable"
        raise HeinzelError(msg) from None


@dataclass(frozen=True, slots=True)
class Selection:
    """Exact owner-selected path and currently installed binary, not publisher or grant proof."""

    command: Path
    binary: Path
    binary_sha256: str
    wrapper: bool


def selected(session: GoogleSession) -> Selection:
    """Snapshot the configured native CLI or the unchanged known npm launcher and its existing binary.

    Raises:
        HeinzelError: If the selected command or known wrapper is unavailable or changed.
    """
    if session.settings.gws_path is None:
        msg = "Select the Google Workspace CLI in your own settings before reviewing a connected read"
        raise HeinzelError(msg)
    try:
        command = Path(session.executable()).resolve(strict=True)
    except (OSError, RuntimeError):
        msg = "The selected Google command is unavailable"
        raise HeinzelError(msg) from None
    if command.name == "run.js":
        root = command.parent
        if any(source_digest(root / name) != digest for name, digest in _WRAPPER_FILES.items()):
            msg = "The selected Google launcher is unsupported or changed"
            raise HeinzelError(msg)
        binary = root / "bin" / "gws"
        return Selection(command, binary, binary_digest(binary), wrapper=True)
    return Selection(command, command, binary_digest(command), wrapper=False)


def describe_selection(current: CurrentUser, session: GoogleSession) -> Selection | None:
    """Describe owner-configured source bytes without starting a process or inspecting an account.

    The result is continuity information, not publisher authentication or a read grant.

    Raises:
        HeinzelError: If the caller or owner-selected configuration cannot be verified.
    """
    context = current.context()
    if (
        context.principal != current.owner()
        or context.authentication not in {"cli", "api-bearer", "web-session", "web-device"}
        or "private:read" not in context.permissions
    ):
        msg = "The Google source review requires its authenticated owner"
        raise HeinzelError(msg)
    fresh = Config.load(Path.home()).settings(GoogleSettings, "google")
    if fresh.gws_path is None and session.settings.gws_path is None:
        return None
    if fresh.gws_path is None or fresh.gws_path != session.settings.gws_path:
        msg = "Select the Google Workspace CLI in your own settings before reviewing a connected read"
        raise HeinzelError(msg)
    return selected(session)


class SelectedCapturedGwsRead(CapturedGwsRead):
    """Unregistered lease that refuses changes in the owner's selected command and wrapper mapping."""

    def __init__(self, current: CurrentUser, session: GoogleSession) -> None:
        self._selected_session = session
        self._selection = selected(session)
        self._assert_selection()
        super().__init__(current, self._selection.binary)

    @property
    def selection(self) -> Selection:
        """The selected command and native binary snapshot, not an approval or publisher proof."""
        return self._selection

    def _assert_selection(self) -> None:
        fresh = Config.load(Path.home()).settings(GoogleSettings, "google")
        if (
            fresh.gws_path != self._selected_session.settings.gws_path
            or selected(self._selected_session) != self._selection
        ):
            msg = "The selected Google command changed; review it again"
            raise HeinzelError(msg)

    def _run(
        self,
        executable: str,
        arguments: Sequence[str],
        timeout: float,
        context: tuple[Mapping[str, str], str, int],
    ) -> Process:
        self._assert_selection()
        return super()._run(executable, arguments, timeout, context)

    def run(self, executable: str, arguments: Sequence[str], timeout: float) -> Process:
        """Accept the selected command identity but execute only its verified native binary.

        Raises:
            HeinzelError: If the command or its selected native mapping changes.
        """
        self._check_owner()
        self._assert_selection()
        if Path(executable).resolve() != self._selection.command:
            msg = "The selected Google command changed; review it again"
            raise HeinzelError(msg)
        return super().run(str(self._selection.binary), arguments, timeout)

    def _export(self) -> bytes:
        self._assert_selection()
        return super()._export()
