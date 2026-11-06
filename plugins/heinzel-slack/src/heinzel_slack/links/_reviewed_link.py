"""Source-captured SlackCLI delivery of one approved Google Doc link to the selected user's self DM.

Only a file-backed stored profile can be privately pinned. Bot/app credentials and Socket Mode are not used.
The core owns human approval. Missing self DMs are refused; this adapter never creates a destination.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar, cast
from urllib.parse import urlsplit

from heinzel import ChannelNotice, ChannelReceipt, ChannelTarget, CurrentUser, HeinzelError, Settings
from heinzel.kernel import ReviewedLinkChannel

from heinzel_slack._settings import SlackSettings
from heinzel_slack._store import Store
from heinzel_slack.links._cli_process import run

_MAX_BINARY = 256 * 1024 * 1024
_MAX_CONFIG = 1024 * 1024
_TOOL_VERSION = b"0.18.0"


def _adapter_sources() -> dict[str, str]:
    root = Path(__file__).parents[1]
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(_bytes(path, _MAX_CONFIG)).hexdigest()
        for path in root.rglob("*.py")
    }


def _bytes(path: Path, maximum: int) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 0 <= info.st_size <= maximum:
            msg = "The selected Slack CLI source cannot be captured"
            raise HeinzelError(msg)
        data = stream.read(maximum + 1)
        if len(data) != info.st_size:
            msg = "The selected Slack CLI source changed during capture"
            raise HeinzelError(msg)
        return data


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _json(data: bytes) -> dict[str, object]:
    try:
        value = json.loads(data, object_pairs_hook=_pairs)
        if isinstance(value, dict):
            return cast("dict[str, object]", value)
    except (ValueError, UnicodeError):
        pass
    msg = "Slack CLI returned an invalid structured acknowledgement"
    raise HeinzelError(msg)


class _CapturedCli:
    def __init__(self, settings: SlackSettings, current: CurrentUser) -> None:
        self.settings, self.current = settings, current
        self.deadline = time.monotonic() + settings.timeout
        self.owner = current.principal().id
        self.head = current.context()
        if (
            self.head.principal != current.owner()
            or self.head.authentication not in {"cli", "api-bearer", "web-session", "web-device", "daemon"}
            or "private:read" not in self.head.permissions
        ):
            msg = "Slack link delivery requires its authenticated private owner"
            raise HeinzelError(msg)
        if settings.cli_path is None or not settings.cli_profile:
            msg = "Select an exact native Slack CLI and stored profile before reviewing a link"
            raise HeinzelError(msg)
        self.binary = Path(settings.cli_path).resolve(strict=True)
        self.config = Path.home() / ".config" / "slackcli" / "workspaces.json"
        binary = _bytes(self.binary, _MAX_BINARY)
        # Refuse launchers and scripts: captured bytes must be a native executable.
        if binary[:4] not in {b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\x7fELF", b"\xca\xfe\xba\xbe"}:
            msg = "Select the installed native Slack CLI binary"
            raise HeinzelError(msg)
        self.binary_digest = hashlib.sha256(binary).hexdigest()
        self.config_bytes = _bytes(self.config, _MAX_CONFIG)
        data = _json(self.config_bytes)
        profiles = data.get("workspaces")
        profile = cast("dict[str, object]", profiles).get(settings.cli_profile) if isinstance(profiles, dict) else None
        if not isinstance(profile, dict):
            msg = "The exact Slack profile is missing"
            raise HeinzelError(msg)
        profile = cast("dict[str, object]", profile)
        if profile.get("secret_backend", "file") != "file":
            msg = "The selected Slack profile cannot be privately pinned (file-backed exact profile required)"
            raise HeinzelError(msg)
        if profile.get("auth_type") != "browser":
            msg = "Reviewed SlackCLI links require browser auth; standard-token SDK writes may retry uncertain sends"
            raise HeinzelError(msg)
        self._temporary = tempfile.TemporaryDirectory(prefix="hz-slackcli-lease-")
        try:
            home = Path(self._temporary.name)
            self.executable = home / "slackcli"
            self.executable.write_bytes(binary)
            self.executable.chmod(0o700)
            directory = home / ".config" / "slackcli"
            directory.mkdir(parents=True, mode=0o700)
            target = directory / "workspaces.json"
            target.write_text(
                json.dumps({"default_workspace": settings.cli_profile, "workspaces": {settings.cli_profile: profile}})
            )
            target.chmod(0o600)
            self.environment = {
                "HOME": str(home),
                "PATH": "/usr/bin:/bin",
                "CI": "1",
                "SLACKCLI_NO_UPDATE_NOTIFIER": "1",
                "SLACKCLI_LOG_LEVEL": "off",
                "SLACKCLI_LOG_DIR": str(home / "logs"),
            }
            remaining = self.deadline - time.monotonic()
            if (
                remaining <= 0
                or run(self.executable, ["--version"], self.environment, remaining).strip() != _TOOL_VERSION
            ):
                msg = "Reviewed Slack links require the audited SlackCLI 0.18.0 command contract"
                raise HeinzelError(msg)
            self.adapter = _adapter_sources()
            self.source = hashlib.sha256(
                json.dumps(
                    {
                        "binary": str(self.binary),
                        "binary_sha256": self.binary_digest,
                        "profile": settings.cli_profile,
                        "tool": "slackcli",
                        "version": _TOOL_VERSION.decode(),
                        "config_sha256": hashlib.sha256(self.config_bytes).hexdigest(),
                        "adapter": self.adapter,
                    },
                    sort_keys=True,
                ).encode()
            ).hexdigest()
        except BaseException:
            self.close()
            raise

    def _check(self) -> None:
        from heinzel import Config  # noqa: PLC0415

        fresh = Config.load(Path.home()).settings(SlackSettings, "slack")
        if (
            self.current.context() != self.head
            or self.current.principal().id != self.owner
            or self.current.context().principal != self.current.owner()
            or fresh.cli_path != self.settings.cli_path
            or fresh.cli_profile != self.settings.cli_profile
            or self.settings.cli_path is None
            or Path(self.settings.cli_path).resolve(strict=True) != self.binary
            or hashlib.sha256(_bytes(self.binary, _MAX_BINARY)).hexdigest() != self.binary_digest
            or _adapter_sources() != self.adapter
            or _bytes(self.config, _MAX_CONFIG) != self.config_bytes
        ):
            msg = "The captured Slack CLI owner, profile or source changed"
            raise HeinzelError(msg)

    def call(self, arguments: list[str]) -> dict[str, object]:
        self._check()
        read = arguments == ["auth", "whoami"]
        prefix = [
            "conversations",
            "list",
            "--types",
            "im",
            "--limit",
            "200",
            "--fields",
            "id,user,is_im,is_mpim,is_archived",
        ]
        read = (
            read
            or arguments == prefix
            or (
                arguments[: len(prefix)] == prefix
                and len(arguments) == len(prefix) + 2
                and arguments[-2] == "--cursor"
                and 0 < len(arguments[-1]) <= 2048
            )
        )
        write = (
            len(arguments) == 6
            and arguments[:3] == ["messages", "send", "--recipient-id"]
            and re.fullmatch(r"D[A-Z0-9]{6,20}", arguments[3]) is not None
            and arguments[4] == "--message"
            and re.fullmatch(r"https://docs\.google\.com/document/d/[A-Za-z0-9_-]+/edit(?:[?#][^\s]*)?", arguments[5])
            is not None
        )
        if not (read or write):
            msg = "The Slack CLI request exceeds the reviewed-link adapter's fixed operations"
            raise HeinzelError(msg)
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            msg = "The bounded Slack CLI lease expired before this provider request"
            raise HeinzelError(msg)
        return _json(
            run(
                self.executable,
                [*arguments, "--workspace", self.settings.cli_profile, "--json"],
                self.environment,
                remaining,
            )
        )

    def target(self) -> ChannelTarget:
        identity = self.call(["auth", "whoami"])
        team, user = identity.get("workspace_id"), identity.get("user_id")
        if (
            identity.get("status") != "ok"
            or identity.get("profile") != self.settings.cli_profile
            or not isinstance(team, str)
            or re.fullmatch(r"T[A-Z0-9]{6,20}", team) is None
            or not isinstance(user, str)
            or re.fullmatch(r"[UW][A-Z0-9]{6,20}", user) is None
        ):
            msg = "Slack did not attest the exact selected profile and user"
            raise HeinzelError(msg)
        cursor = ""
        seen: set[str] = set()
        matches: set[str] = set()
        for _ in range(20):
            args = [
                "conversations",
                "list",
                "--types",
                "im",
                "--limit",
                "200",
                "--fields",
                "id,user,is_im,is_mpim,is_archived",
            ]
            if cursor:
                args += ["--cursor", cursor]
            page = self.call(args)
            conversations = page.get("conversations")
            if not isinstance(conversations, list):
                break
            for candidate in cast("list[object]", conversations):
                if not isinstance(candidate, dict):
                    msg = "Slack returned an invalid conversation identity"
                    raise HeinzelError(msg)
                item = cast("dict[str, object]", candidate)
                if (
                    item.get("user") == user
                    and item.get("is_im") is True
                    and item.get("is_mpim") is not True
                    and item.get("is_archived") is not True
                ):
                    channel = item.get("id")
                    if isinstance(channel, str) and re.fullmatch(r"D[A-Z0-9]{6,20}", channel):
                        matches.add(channel)
            next_cursor = page.get("next_cursor")
            if next_cursor in (None, ""):
                if len(matches) == 1:
                    return ChannelTarget(
                        account=f"slack:{team}:{user}",
                        destination=matches.pop(),
                        scope=f"slackcli:self-dm:chat.write:{self.source}",
                    )
                break
            if not isinstance(next_cursor, str) or next_cursor in seen:
                break
            seen.add(next_cursor)
            cursor = next_cursor
        msg = "Slack did not attest exactly one existing self direct message"
        raise HeinzelError(msg)

    def close(self) -> None:
        self._temporary.cleanup()


class SlackReviewedLinks(ReviewedLinkChannel):
    """One human-approved document link, source-bound to the authenticated user's existing self DM."""

    name = "slack-reviewed-links"
    supported_operations: ClassVar[frozenset[str]] = frozenset({"reviewed-document-link"})

    def __init__(self, settings: SlackSettings, current: CurrentUser, hz: Settings) -> None:
        self._settings, self._current = settings, current
        self._directory = hz.state_dir / "slack-cli-links"

    def available(self) -> bool:
        """Whether an exact CLI and profile have been selected; makes no provider request."""
        return self._settings.cli_path is not None and bool(self._settings.cli_profile)

    def delivery_target(self) -> ChannelTarget | None:
        """Attest the selected account, captured source and existing self DM before human approval."""
        if not self.available():
            return None
        cli = _CapturedCli(self._settings, self._current)
        try:
            return cli.target()
        finally:
            cli.close()

    def deliver_link_reviewed(self, notice: ChannelNotice, target: ChannelTarget) -> ChannelReceipt:
        """Send only the literal approved Google Doc URL, consume a durable intent and require Slack's ack."""
        parts = urlsplit(notice.body)
        if (
            parts.scheme != "https"
            or parts.netloc != "docs.google.com"
            or re.fullmatch(r"/document/d/[A-Za-z0-9_-]+/edit", parts.path) is None
        ):
            return ChannelReceipt(
                channel=self.name, status="refused", detail="Only an approved Google Doc link is supported"
            )
        cli = _CapturedCli(self._settings, self._current)
        try:
            if cli.target() != target:
                return ChannelReceipt(
                    channel=self.name, status="refused", detail="The exact Slack posting target changed"
                )
            store = Store(self._directory)
            # Bind a stable key to exact bytes and target; reusing a key for another payload never authorizes it.
            key = f"link:{notice.key}"
            if not store.begin_delivery(key, datetime.now(UTC)):
                known = store.delivery(key)
                return ChannelReceipt(
                    channel=self.name,
                    status="unknown",
                    reference=known[1] if known else None,
                    detail="A prior delivery was attempted; never replay it",
                )
            # Fresh target check after the durable intent and through the same private credential/binary capture.
            if cli.target() != target:
                return ChannelReceipt(channel=self.name, status="refused", detail="Slack target changed before send")
            try:
                reply = cli.call(["messages", "send", "--recipient-id", target.destination, "--message", notice.body])
                ts = reply.get("ts")
                if (
                    reply.get("channel_id") != target.destination
                    or not isinstance(ts, str)
                    or re.fullmatch(r"[0-9]+\.[0-9]{1,6}", ts) is None
                ):
                    raise HeinzelError("Slack acknowledgement is ambiguous")
            except HeinzelError:
                store.end_delivery(key, "unknown", None)
                return ChannelReceipt(
                    channel=self.name, status="unknown", detail="Slack delivery may have happened; do not retry"
                )
            reference = f"{target.destination}:{ts}"
            store.end_delivery(key, "delivered", reference)
            return ChannelReceipt(channel=self.name, status="delivered", reference=reference)
        finally:
            cli.close()
