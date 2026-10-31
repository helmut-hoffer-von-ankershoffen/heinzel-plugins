"""Unregistered experiment for a privately captured existing GWS connection.

No method supplies human approval, installed publisher authentication or a model tool. The host must enforce those
boundaries before use. An access token is held in memory and passed only to subprocesses; cleanup is not secure erasure.
"""

import hashlib
import hmac
import json
import math
import os
import re
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from importlib.resources import files
from pathlib import Path
from typing import Concatenate, Never, SupportsIndex, cast

from heinzel import CurrentUser, HeinzelError

from heinzel_google._gws import GRACE, MAX_BYTES, Gws, Process, environment, signal_group
from heinzel_google._token_exchange import ARTIFACT_SCOPES, covered

_MAX_CREDENTIAL_BYTES = 32_768
_MAX_BINARY_BYTES = 512 * 1024 * 1024
_MAX_WINDOW = timedelta(days=31)
_MAX_PAGESIZE = 250
_MAX_EMAIL = 254
_MAX_PAGE_TOKEN = 4096
_MAX_TIMEOUT = 120.0
_EXCHANGE_TIMEOUT = 30.0
_MAX_TOKEN_LIFETIME = 86400
_MAX_SCOPE_BYTES = 8192
_MAX_SCOPES = 128
_MIN_TOKEN_LIFETIME = 30
_SCOPES = (
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
)
_MAIL_SCOPES = (
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
)
_COMMAND_LENGTH = 7
_MAGIC_LENGTH = 4
_MACHO = {b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"}
_NATIVE = _MACHO | {b"\x7fELF"}
_SOURCE_ENV = (
    "HOME",
    "USER",
    "LOGNAME",
    "LANG",
    "TMPDIR",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "XDG_RUNTIME_DIR",
    "DBUS_SESSION_BUS_ADDRESS",
    "GOOGLE_WORKSPACE_CLI_CONFIG_DIR",
    "GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND",
)
_FORBIDDEN = (
    "GOOGLE_WORKSPACE_CLI_TOKEN",
    "GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_WORKSPACE_CLI_ACCOUNT",
    "GOOGLE_WORKSPACE_CLI_IMPERSONATED_USER",
)
_PERMISSION = re.compile(r"[A-Za-z0-9_-]{1,256}\Z", re.ASCII)


@dataclass(frozen=True, slots=True, repr=False)
class DriveIdentity:
    """Drive's requesting-user permission ID and optional unverified display email."""

    permission_id: str
    email: str | None

    def __repr__(self) -> str:
        return "<DriveIdentity private>"


@dataclass(frozen=True, slots=True)
class ReadWindow:
    """Exact host-reviewed half-open time window; it is not itself an approval."""

    since: datetime
    until: datetime

    def __post_init__(self) -> None:
        """Validate bounded aware timestamps.

        Raises:
            HeinzelError: If the window is invalid or too wide.
        """
        if (
            self.since.tzinfo is None
            or self.since.utcoffset() is None
            or self.until.tzinfo is None
            or self.until.utcoffset() is None
            or self.since >= self.until
            or self.until - self.since > _MAX_WINDOW
        ):
            msg = "The requested read window is invalid"
            raise HeinzelError(msg)


def binary_digest(path: Path) -> str:
    """Fingerprint a bounded regular native executable, not a publisher attestation.

    Raises:
        HeinzelError: If the selected executable is unavailable or unsafe.
    """
    invalid = "The selected GWS executable is unavailable"
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or not _MAGIC_LENGTH <= info.st_size <= _MAX_BINARY_BYTES:
                raise HeinzelError(invalid)  # noqa: TRY301
            first = stream.read(_MAGIC_LENGTH)
            if first not in _NATIVE:
                raise HeinzelError(invalid)  # noqa: TRY301
            digest = hashlib.sha256(first)
            remaining = info.st_size - _MAGIC_LENGTH
            while remaining:
                chunk = stream.read(min(remaining, 1024 * 1024))
                if not chunk:
                    raise HeinzelError(invalid)  # noqa: TRY301
                digest.update(chunk)
                remaining -= len(chunk)
            if stream.read(1):
                raise HeinzelError(invalid)  # noqa: TRY301
            return digest.hexdigest()
    except (OSError, HeinzelError):
        raise HeinzelError(invalid) from None


def _capture_binary(source: Path, destination: Path, expected: str) -> None:
    """Copy bounded reviewed executable bytes into a private lease directory.

    Raises:
        HeinzelError: If the bytes cannot be captured exactly.
    """
    denied = "The selected GWS executable could not be captured"
    try:
        fd = os.open(source, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream, destination.open("xb") as output:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or not _MAGIC_LENGTH <= info.st_size <= _MAX_BINARY_BYTES:
                raise HeinzelError(denied)  # noqa: TRY301
            remaining = info.st_size
            while remaining:
                chunk = stream.read(min(remaining, 1024 * 1024))
                if not chunk:
                    raise HeinzelError(denied)  # noqa: TRY301
                output.write(chunk)
                remaining -= len(chunk)
            if stream.read(1):
                raise HeinzelError(denied)  # noqa: TRY301
        destination.chmod(0o700)
        if binary_digest(destination) != expected:
            raise HeinzelError(denied)  # noqa: TRY301
    except (OSError, HeinzelError):
        raise HeinzelError(denied) from None


def _private_source_environment() -> dict[str, str]:
    if any(os.environ.get(name) for name in _FORBIDDEN):
        msg = "The current Google credential source is not supported for this connection"
        raise HeinzelError(msg)
    env = environment()
    return {key: env[key] for key in _SOURCE_ENV if key in env} | {"PATH": "/usr/bin:/bin"}


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _invalid_constant(_value: str) -> Never:
    raise ValueError


def _credentials(data: bytes) -> bytes:
    """Validate exactly the documented authorized-user export without returning diagnostics.

    Raises:
        HeinzelError: If export is oversized, malformed, or a different credential type.
    """
    denied = "The existing Google connection could not be safely captured"
    if not 0 < len(data) <= _MAX_CREDENTIAL_BYTES:
        raise HeinzelError(denied)
    try:
        raw: object = json.loads(data, object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise HeinzelError(denied) from None
    if not isinstance(raw, dict):
        raise HeinzelError(denied)
    value = cast("dict[str, object]", raw)
    if set(value) != {"type", "client_id", "client_secret", "refresh_token"} or value.get("type") != "authorized_user":
        raise HeinzelError(denied)
    for key in ("client_id", "client_secret", "refresh_token"):
        item = value.get(key)
        if not isinstance(item, str) or not item or not item.isprintable() or len(item) > _MAX_CREDENTIAL_BYTES:
            raise HeinzelError(denied)
    return data


class _ExchangeUncertainError(Exception):
    """The private OAuth helper did not confirm termination."""


def _exchange_token(
    exported: bytes, *, mail: bool = False, artifact: str | None = None
) -> tuple[str, float, tuple[str, ...]]:
    """Exchange in a killable helper with an end-to-end deadline, never exposing diagnostics.

    Raises:
        HeinzelError: If exchange, termination or validation fails.
        ValueError: Invalid provider output is converted to a safe error.
        _ExchangeUncertainError: An uncertain helper stop is converted to a safe error.
    """
    denied = "The existing Google connection could not obtain a bounded access token"
    _credentials(exported)
    started = time.monotonic()
    try:
        helper = files("heinzel_google").joinpath("_token_exchange.py").read_bytes()
        if not 0 < len(helper) <= _MAX_CREDENTIAL_BYTES:
            raise ValueError  # noqa: TRY301
        helper_source = helper.decode("utf-8")
        process = subprocess.Popen(  # noqa: S603 - pinned Python and captured public helper source, no shell
            [
                sys.executable,
                "-I",
                "-S",
                "-c",
                helper_source,
                *([artifact] if artifact else ["mail"] if mail else []),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env={"PATH": "/usr/bin:/bin"},
            cwd="/",
            start_new_session=True,
        )
        try:
            try:
                raw, _ = process.communicate(exported, timeout=_EXCHANGE_TIMEOUT)
            except subprocess.TimeoutExpired:
                msg = "Token exchange exceeded its deadline"
                raise ValueError(msg) from None
        finally:
            signal_group(process.pid, signal.SIGKILL)
            try:
                process.communicate(timeout=GRACE)
            except subprocess.TimeoutExpired:
                msg = "Token exchange termination is uncertain"
                raise _ExchangeUncertainError(msg) from None
        if process.returncode != 0 or len(raw) > _MAX_CREDENTIAL_BYTES:
            raise ValueError  # noqa: TRY301
        data = json.loads(raw, object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
        token, lifetime, scope = data.get("access_token"), data.get("expires_in"), data.get("scope")
        if (
            not isinstance(token, str)
            or not token
            or not token.isascii()
            or not token.isprintable()
            or len(token) > _MAX_CREDENTIAL_BYTES
            or type(lifetime) is not int
            or not _MIN_TOKEN_LIFETIME <= lifetime <= _MAX_TOKEN_LIFETIME
            or data.get("token_type") != "Bearer"
            or not isinstance(scope, str)
            or not scope.isascii()
            or not scope.isprintable()
            or len(scope) > _MAX_SCOPE_BYTES
            or len(scope.split()) > _MAX_SCOPES
            or not covered(
                ARTIFACT_SCOPES[artifact] if artifact else _MAIL_SCOPES if mail else _SCOPES,
                set(scope.split()),
            )
        ):
            raise ValueError  # noqa: TRY301
        expires = started + lifetime - 5
        if time.monotonic() >= expires:
            raise ValueError  # noqa: TRY301
    except _ExchangeUncertainError:
        msg = "The private Google authentication helper could not be confirmed stopped"
        raise HeinzelError(msg) from None
    except Exception:  # noqa: BLE001 - never expose network, credential, or provider diagnostics
        raise HeinzelError(denied) from None
    else:
        return token, expires, tuple(sorted(set(scope.split())))


def _serialized[T: "CapturedGwsRead", **P, R](
    method: Callable[Concatenate[T, P], R],
) -> Callable[Concatenate[T, P], R]:
    @wraps(method)
    def wrapped(self: T, /, *args: P.args, **kwargs: P.kwargs) -> R:
        with self.lease_lock:
            try:
                return method(self, *args, **kwargs)
            except BaseException as exc:
                if not isinstance(exc, Exception):
                    self.discard()
                raise

    return wrapped


class CapturedGwsRead(Gws):
    """Private per-lease captured credential and cache; never registered as a runnable operation."""

    def __init__(self, current: CurrentUser, executable: Path) -> None:
        self.lease_lock = threading.RLock()
        self._current = current
        self._owner = current.principal().id
        self._head = current.context()
        self._check_owner()
        try:
            self._executable = executable.resolve(strict=True)
        except OSError:
            msg = "The selected GWS executable is unavailable"
            raise HeinzelError(msg) from None
        self._digest = binary_digest(self._executable)
        self._source_env = _private_source_environment()
        self._temporary: tempfile.TemporaryDirectory[str] | None = tempfile.TemporaryDirectory(prefix="hz-gws-lease-")
        self._identity: DriveIdentity | None = None
        self._window: ReadWindow | None = None
        self._page_token: str | None = None
        self._page_query: str | None = None
        self._seen_tokens: set[str] = set()
        try:
            self._captured_executable = Path(self._temporary.name) / "gws-captured"
            _capture_binary(self._executable, self._captured_executable, self._digest)
            version = self._run(
                str(self._executable),
                ["--version"],
                10,
                (self._source_env, self._temporary.name, _MAX_CREDENTIAL_BYTES),
            )
            if version.exit_code != 0 or version.truncated or version.stdout.splitlines()[:1] != [b"gws 0.22.5"]:
                msg = "The selected GWS version is unsupported"
                raise HeinzelError(msg)  # noqa: TRY301
            exported = self._export()
            self._export_digest = hashlib.sha256(exported).digest()
            self._token, self._expires, self._scopes = self._exchange(exported)
        except BaseException:
            self._cleanup()
            raise

    def _run(
        self,
        executable: str,
        arguments: Sequence[str],
        timeout: float,
        context: tuple[Mapping[str, str], str, int],
    ) -> Process:
        """Launch captured bytes while retaining the selected path as the reviewed identity.

        Raises:
            HeinzelError: If the requested executable differs from the selected source.
            OSError: If the bounded subprocess fails.
        """
        if Path(executable) != self._executable or self._temporary is None:
            msg = "The selected GWS executable is unavailable"
            raise HeinzelError(msg)
        return super()._run(str(self._captured_executable), arguments, timeout, context)

    def __repr__(self) -> str:
        return "<CapturedGwsRead private>"

    def __reduce_ex__(self, _protocol: SupportsIndex) -> Never:
        msg = "A private Google connection lease cannot be serialized"
        raise TypeError(msg)

    def _check_owner(self) -> None:
        context = self._current.context()
        if (
            context != self._head
            or context.authentication not in {"cli", "api-bearer", "web-session", "web-device", "daemon"}
            or context.principal != self._current.owner()
            or context.principal.id != self._owner
            or "private:read" not in context.permissions
        ):
            msg = "The Google connection belongs to another owner"
            raise HeinzelError(msg)

    def _export(self) -> bytes:
        self._check_owner()
        if self._temporary is None or self._source_env != _private_source_environment():
            msg = "The Google connection source changed or is unavailable"
            raise HeinzelError(msg)
        if binary_digest(self._executable) != self._digest:
            msg = "The selected GWS executable changed"
            raise HeinzelError(msg)
        try:
            result = self._run(
                str(self._executable),
                ["auth", "export", "--unmasked"],
                10,
                (self._source_env, self._temporary.name, _MAX_CREDENTIAL_BYTES),
            )
            if result.exit_code != 0 or result.truncated:
                msg = "The existing Google connection could not be safely captured"
                raise HeinzelError(msg)  # noqa: TRY301
            return _credentials(result.stdout)
        except Exception:  # noqa: BLE001 - subprocess errors and output can contain secrets
            msg = "The existing Google connection could not be safely captured"
            raise HeinzelError(msg) from None

    @staticmethod
    def _exchange(exported: bytes) -> tuple[str, float, tuple[str, ...]]:
        return _exchange_token(exported)

    def _check_current(self) -> None:
        try:
            current_digest = hashlib.sha256(self._export()).digest()
        except HeinzelError:
            self._cleanup()
            raise
        if not hmac.compare_digest(current_digest, self._export_digest):
            self._cleanup()
            msg = "The Google connection changed; review it again"
            raise HeinzelError(msg)
        if time.monotonic() >= self._expires:
            self._cleanup()
            msg = "The Google connection lease expired"
            raise HeinzelError(msg)

    def _read(self, arguments: Sequence[str], timeout: float) -> Process:
        self._check_owner()
        self._check_current()
        if self._temporary is None:
            msg = "The Google connection lease is closed"
            raise HeinzelError(msg)
        env = {
            "PATH": "/usr/bin:/bin",
            "HOME": self._temporary.name,
            "XDG_CONFIG_HOME": self._temporary.name,
            "GOOGLE_WORKSPACE_CLI_CONFIG_DIR": self._temporary.name,
            "GOOGLE_WORKSPACE_CLI_TOKEN": self._token,
        }
        try:
            result = self._run(str(self._executable), arguments, timeout, (env, self._temporary.name, MAX_BYTES))
        except Exception:  # noqa: BLE001 - subprocess error text may include private material
            self._cleanup()
            msg = "The Google read could not be completed; subprocess termination may be uncertain"
            raise HeinzelError(msg) from None
        if result.exit_code != 0 or result.truncated:
            return Process(result.exit_code, b"", b"", result.truncated)
        return result

    @_serialized
    def observed_scopes(self) -> tuple[str, ...]:
        """Provider token scopes, potentially broader than the host's strictly limited read commands.

        Raises:
            HeinzelError: If the owner or connection changed or the lease expired.
        """
        self._check_current()
        return self._scopes

    @_serialized
    def inspect_identity(self) -> DriveIdentity:
        """Read the requesting Drive user through the captured credential; this is not an approval.

        Raises:
            HeinzelError: If Drive cannot establish the exact requesting permission identity.
            ValueError: Invalid provider JSON is mapped to a safe error.
        """
        self._check_owner()
        result = self._read(
            [
                "drive",
                "about",
                "get",
                "--params",
                '{"fields":"user(permissionId,emailAddress,me)"}',
                "--format",
                "json",
            ],
            10,
        )
        denied = "The Google Drive identity could not be verified"
        try:
            if result.exit_code != 0 or result.truncated or len(result.stdout) > _MAX_CREDENTIAL_BYTES:
                raise ValueError  # noqa: TRY301
            decoded: object = json.loads(
                result.stdout, object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant
            )
            data = cast("dict[str, object]", decoded) if isinstance(decoded, dict) else {}
            raw_user = data.get("user")
            user = cast("dict[str, object]", raw_user) if isinstance(raw_user, dict) else {}
            permission = user.get("permissionId")
            email = user.get("emailAddress")
            if (
                user.get("me") is not True
                or not isinstance(permission, str)
                or not _PERMISSION.fullmatch(permission)
                or (
                    email is not None
                    and (
                        not isinstance(email, str)
                        or not email.isascii()
                        or not email.isprintable()
                        or len(email) > _MAX_EMAIL
                    )
                )
            ):
                raise ValueError  # noqa: TRY301
            return DriveIdentity(permission, email)
        except (ValueError, TypeError, RecursionError):
            raise HeinzelError(denied) from None

    @_serialized
    def bind_review(self, identity: DriveIdentity, window: ReadWindow, scopes: tuple[str, ...]) -> None:
        """Match the exact host-reviewed identity, provider scopes and window; this is not an approval boundary.

        Raises:
            HeinzelError: If the reviewed identity/window does not match the captured source.
        """
        self._check_owner()
        self._identity, self._window = None, None
        self._page_token = None
        self._page_query = None
        self._seen_tokens.clear()
        observed = self.inspect_identity()
        if (
            type(identity) is not DriveIdentity
            or type(window) is not ReadWindow
            or identity != observed
            or type(scopes) is not tuple
            or scopes != self._scopes
        ):
            msg = "The reviewed Google connection does not match"
            raise HeinzelError(msg)
        self._identity, self._window = observed, window

    @_serialized
    def close(self) -> None:
        """Remove private temporary files; deletion does not promise secure erasure."""
        self._check_owner()
        self._cleanup()

    @_serialized
    def discard(self) -> None:
        """Unconditionally discard private resources after cancellation or lost call context."""
        self._cleanup()

    def _cleanup(self) -> None:
        self._identity, self._window = None, None
        self._page_token = None
        self._page_query = None
        self._seen_tokens.clear()
        self._token = ""
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None

    @_serialized
    def run(self, executable: str, arguments: Sequence[str], timeout: float) -> Process:
        """Allow only the reviewed primary Calendar window; every page uses the captured credential.

        Raises:
            HeinzelError: If the lease, command, identity, executable or reviewed window differs.
            ValueError: Invalid parameters are mapped to a safe error.
        """
        self._check_owner()
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= _MAX_TIMEOUT:
            msg = "The Google read timeout is invalid"
            raise HeinzelError(msg)
        args = list(arguments)
        if Path(executable).resolve() != self._executable:
            msg = "The selected GWS executable changed"
            raise HeinzelError(msg)
        if args == ["--version"]:
            self._check_current()
            if self._temporary is None:
                msg = "The Google connection lease is closed"
                raise HeinzelError(msg)
            return self._run(
                str(self._executable), args, timeout, (self._source_env, self._temporary.name, _MAX_CREDENTIAL_BYTES)
            )
        if (
            self._identity is None
            or self._window is None
            or len(args) != _COMMAND_LENGTH
            or args[:3] != ["calendar", "events", "list"]
            or args[3] != "--params"
            or args[5:] != ["--format", "json"]
        ):
            msg = "This Google read is unavailable under the captured connection"
            raise HeinzelError(msg)
        params = self._calendar_params(args[4], self._window)
        self._check_page_query(params)
        try:
            if self.inspect_identity() != self._identity:
                msg = "The Google connection identity changed; review it again"
                raise HeinzelError(msg)  # noqa: TRY301
        except HeinzelError:
            self._identity, self._window = None, None
            raise
        return self._read_page(args, timeout)

    def _check_page_query(self, params: dict[str, object]) -> None:
        supplied = params.get("pageToken")
        if supplied != self._page_token:
            msg = "The Google page continuation is not the expected next page"
            raise HeinzelError(msg)
        query = json.dumps({key: value for key, value in params.items() if key != "pageToken"}, sort_keys=True)
        if supplied is not None and query != self._page_query:
            msg = "The Google page does not match the initial query"
            raise HeinzelError(msg)
        if supplied is None:
            self._seen_tokens.clear()
            self._page_query = query

    @staticmethod
    def _calendar_params(encoded: str, window: ReadWindow) -> dict[str, object]:
        try:
            raw: object = json.loads(encoded, object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
            if not isinstance(raw, dict):
                raise TypeError  # noqa: TRY301
            params = cast("dict[str, object]", raw)
            maximum, since, until, page = (
                params.get("maxResults"),
                params.get("timeMin"),
                params.get("timeMax"),
                params.get("pageToken"),
            )
            allowed = {"calendarId", "timeMin", "timeMax", "singleEvents", "showDeleted", "maxResults", "pageToken"}
            if (
                not set(params) <= allowed
                or params.get("calendarId") != "primary"
                or params.get("singleEvents") is not True
                or type(params.get("showDeleted")) is not bool
                or type(maximum) is not int
                or not 1 <= maximum <= _MAX_PAGESIZE
                or not isinstance(since, str)
                or datetime.fromisoformat(since) != window.since
                or not isinstance(until, str)
                or datetime.fromisoformat(until) != window.until
                or ("pageToken" in params and (not isinstance(page, str) or len(page) > _MAX_PAGE_TOKEN))
            ):
                raise ValueError  # noqa: TRY301
        except (ValueError, TypeError, KeyError, AttributeError):
            msg = "The Google read does not match its reviewed window"
            raise HeinzelError(msg) from None
        return params

    def _read_page(self, args: list[str], timeout: float) -> Process:
        result = self._read(args, timeout)
        if result.exit_code != 0 or result.truncated:
            return result
        try:
            decoded: object = json.loads(
                result.stdout, object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant
            )
            payload = cast("dict[str, object]", decoded) if isinstance(decoded, dict) else None
            token = payload.get("nextPageToken") if payload is not None else None
            if payload is None or (
                token is not None
                and (
                    not isinstance(token, str)
                    or not token
                    or len(token) > _MAX_PAGE_TOKEN
                    or token in self._seen_tokens
                )
            ):
                raise ValueError  # noqa: TRY301
            if token is not None:
                self._seen_tokens.add(token)
            self._page_token = token
        except (ValueError, TypeError, RecursionError):
            self._identity, self._window = None, None
            self._page_token = None
            self._seen_tokens.clear()
            msg = "The Google page continuation could not be verified"
            raise HeinzelError(msg) from None
        return result
