"""Read one supplied GitHub CHANGELOG and matching real releases through a privately pinned gh lease.

The token is exported by gh inside the lease and is never logged or persisted. Ordinary Github reads continue
to let gh own authentication. This optional source-only service never grants writes or historical catch-up.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar, cast
from urllib.parse import quote, urlsplit

from heinzel import Config, CurrentUser, HeinzelError, Kernel
from heinzel.kernel import (
    ReleaseFeedBaseline,
    ReleaseFeedIdentity,
    ReleaseFeedLease,
    ReleaseFeedService,
    ReleasePage,
    ReleaseRecord,
)
from pydantic import SecretStr

from heinzel_github._adapter import repository_name as _repository
from heinzel_github._client import GhClient
from heinzel_github._gh import Gh, environment, hosts_file
from heinzel_github._models import GithubSettings

_URL_PARTS = 5
_TOKEN_LIMIT = 4096
_CURSOR_PARTS = 2
_PAGE_SIZE = 100
_MAX_BINARY = 256 * 1024 * 1024


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _reference(reference: str, host: str) -> tuple[str, str, str]:
    value = urlsplit(reference)
    bits = value.path.strip("/").split("/")
    if (
        value.scheme != "https"
        or value.netloc != host
        or value.query
        or value.fragment
        or len(bits) < _URL_PARTS
        or bits[2] != "blob"
        or not bits[-1].lower().endswith(".md")
        or any(part in {"", ".", ".."} for part in bits)
    ):
        msg = "Supply an exact HTTPS GitHub blob URL for the CHANGELOG Markdown"
        raise HeinzelError(msg)
    return _repository("/".join(bits[:2])), bits[3], "/".join(bits[4:])


class _CapturedGh(Gh):
    def __init__(self, settings: GithubSettings) -> None:
        super().__init__(settings)
        source = super().executable()
        if source is None:
            msg = "Select an installed GitHub CLI before polling releases"
            raise HeinzelError(msg)
        self.selected = Path(source).resolve(strict=True)
        self._temporary = tempfile.TemporaryDirectory(prefix="hz-release-gh-")
        self.path = Path(self._temporary.name) / "gh"
        try:
            # Capture executable bytes before exporting the credential, so PATH replacement cannot redirect it.
            with self.selected.open("rb") as stream:
                binary = stream.read(_MAX_BINARY + 1)
            if not 0 < len(binary) <= _MAX_BINARY:
                raise ValueError  # noqa: TRY301
            if binary[:4] not in {b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\x7fELF", b"\xca\xfe\xba\xbe"}:
                raise ValueError  # noqa: TRY301
            self.path.write_bytes(binary)
            self.path.chmod(0o700)
            self.binary_digest = hashlib.sha256(binary).hexdigest()
            self.original_environment = environment(settings.host)
            self.original_config = hosts_file()
            self.config_digest = _digest(self.original_config) if self.original_config.is_file() else "absent"
            self._environment = dict(self.original_environment)
            result = self.run(
                ["auth", "token", "--hostname", settings.host], host=settings.host, timeout=settings.timeout
            )
            token = result.stdout.decode().strip()
            if (
                result.returncode != 0
                or result.truncated
                or not token
                or len(token) > _TOKEN_LIMIT
                or any(c.isspace() for c in token)
            ):
                raise ValueError  # noqa: TRY301
            self._environment = {
                key: value
                for key, value in self._environment.items()
                if key not in {"GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"}
            }
            variable = (
                "GH_TOKEN"
                if settings.host == "github.com" or settings.host.endswith(".ghe.com")
                else "GH_ENTERPRISE_TOKEN"
            )
            self._environment.update({variable: token, "GH_CONFIG_DIR": self._temporary.name})
            self.adapter = {path.name: _digest(path) for path in Path(__file__).parent.glob("*.py")}
            self.source = hashlib.sha256(
                json.dumps(
                    {
                        "selected": str(self.selected),
                        "binary": self.binary_digest,
                        "config": self.config_digest,
                        "host": settings.host,
                        "environment": hashlib.sha256(
                            json.dumps(self.original_environment, sort_keys=True).encode()
                        ).hexdigest(),
                        "adapter": {path.name: _digest(path) for path in Path(__file__).parent.glob("*.py")},
                    },
                    sort_keys=True,
                ).encode()
            ).hexdigest()
        except (OSError, ValueError, UnicodeError):
            self.close()
            msg = "The existing GitHub CLI credential or native source could not be privately captured"
            raise HeinzelError(msg) from None
        except BaseException:
            self.close()
            raise

    def executable(self) -> str:
        return str(self.path)

    def execution_environment(self, host: str) -> dict[str, str]:
        del host
        return self._environment

    def check(self) -> None:
        config = _digest(self.original_config) if self.original_config.is_file() else "absent"
        if (
            _digest(self.selected) != self.binary_digest
            or config != self.config_digest
            or {path.name: _digest(path) for path in Path(__file__).parent.glob("*.py")} != self.adapter
            or environment(self._settings.host) != self.original_environment
        ):
            msg = "The selected GitHub CLI source or credential selection changed"
            raise HeinzelError(msg)

    def close(self) -> None:
        self._environment = {}
        self._temporary.cleanup()


def _cursor(identity: ReleaseFeedIdentity, frontier: tuple[str, int]) -> str:
    return base64.urlsafe_b64encode(
        json.dumps([identity.model_dump(), list(frontier)], sort_keys=True).encode()
    ).decode()


def _decode_cursor(cursor: str, identity_value: ReleaseFeedIdentity) -> tuple[str, int]:
    try:
        parsed: object = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
        if not isinstance(parsed, list):
            raise TypeError  # noqa: TRY301
        parts = cast("list[object]", parsed)
        if len(parts) != _CURSOR_PARTS:
            raise ValueError  # noqa: TRY301
        identity, raw = parts
        if identity != identity_value.model_dump() or not isinstance(raw, list):
            raise ValueError  # noqa: TRY301
        values = cast("list[object]", raw)
        if len(values) != _CURSOR_PARTS or not isinstance(values[0], str) or type(values[1]) is not int:
            raise ValueError  # noqa: TRY301
        return values[0], values[1]
    except (ValueError, TypeError, UnicodeError):
        msg = "The GitHub release cursor does not belong to this exact captured source"
        raise HeinzelError(msg) from None


def _frontier(item: dict[str, object]) -> tuple[str, int]:
    published, identity = item.get("published_at"), item.get("id")
    if not isinstance(published, str) or type(identity) is not int:
        msg = "GitHub returned an invalid release identity or publication time"
        raise HeinzelError(msg)
    moment = datetime.fromisoformat(published)
    if moment.tzinfo is None:
        msg = "GitHub returned a release without a timezone"
        raise HeinzelError(msg)
    return moment.astimezone(UTC).isoformat(), identity


def _section(markdown: str, tag: str) -> str:
    lines = markdown.splitlines(keepends=True)
    wanted = tag.removeprefix("v")
    matches = [
        (index, len(line) - len(line.lstrip("#")))
        for index, line in enumerate(lines)
        if re.match(r"^#{1,3}\s", line) and re.search(rf"(?<![A-Za-z0-9.])v?{re.escape(wanted)}(?![A-Za-z0-9.])", line)
    ]
    if len(matches) != 1:
        msg = "The supplied CHANGELOG has no unambiguous section for this real release tag"
        raise HeinzelError(msg)
    index, level = matches[0]
    end = next((n for n in range(index + 1, len(lines)) if re.match(rf"^#{{1,{level}}}\s", lines[n])), len(lines))
    return "".join(lines[index:end])


class _FeedLease(ReleaseFeedLease):
    def __init__(self, service: GithubReleaseFeeds, reference: str) -> None:
        self.service, self.reference = service, reference
        self.head = service.current.context()
        self.repository, self.ref, self.file = _reference(reference, service.settings.host)
        self.gh = _CapturedGh(service.settings)
        try:
            self.client = GhClient(self.gh, service.settings.host, service.settings.timeout)
            user = self.client.get("user")
            account = user.get("login")
            if not isinstance(account, str) or not account:
                raise ValueError  # noqa: TRY301
            self.identity = ReleaseFeedIdentity(
                account=f"{service.settings.host}:{account}",
                source=self.gh.source,
                reference=reference,
                read_scope=f"repo:{self.repository}:releases+contents",
            )
        except BaseException:
            self.close()
            raise

    def _check(self) -> None:
        if self.service.current.context() != self.head:
            msg = "The GitHub lease owner context changed"
            raise HeinzelError(msg)
        self.service.check()
        self.gh.check()
        who = self.client.get("user").get("login")
        if self.identity.account != f"{self.service.settings.host}:{who}":
            msg = "The captured GitHub account changed"
            raise HeinzelError(msg)

    def _releases(self) -> list[dict[str, object]]:
        self._check()
        return next(self.client.pages(f"repos/{self.repository}/releases", {}))

    def _published_releases(self) -> list[dict[str, object]]:
        # A full raw provider page may hide releases on the next page, including behind drafts.
        # Publication order is not a completeness proof for GitHub's provider page ordering.
        page = self._releases()
        if len(page) >= _PAGE_SIZE:
            msg = "The bounded GitHub release page is incomplete; refusing to skip history"
            raise HeinzelError(msg)
        return [item for item in page if item.get("draft") is False]

    def baseline(self) -> ReleaseFeedBaseline:
        """Observe a complete bounded frontier without emitting historical releases.

        Raises:
            HeinzelError: If a full raw provider page cannot establish a complete baseline.
        """
        records = self._published_releases()
        frontier = max((_frontier(item) for item in records), default=(datetime.now(UTC).isoformat(), 0))
        return ReleaseFeedBaseline(identity=self.identity, cursor=_cursor(self.identity, frontier))

    def poll(self, cursor: str) -> ReleasePage:
        """Read one bounded ordered page and combine real notes with the matching literal CHANGELOG section.

        Raises:
            HeinzelError: If source continuity, cursor, bounded history or exact release text cannot be established.
            ValueError: If GitHub supplies malformed publication text.
        """
        frontier = _decode_cursor(cursor, self.identity)
        page = self._published_releases()
        new = sorted((item for item in page if _frontier(item) > frontier), key=_frontier)
        records: list[ReleaseRecord] = []
        if new:
            self._check()
            content = self.client.get(
                f"repos/{self.repository}/contents/{quote(self.file, safe='/')}?ref={quote(self.ref, safe='')}"
            )
            if content.get("path") != self.file or content.get("encoding") != "base64":
                msg = "GitHub did not attest the exact supplied CHANGELOG"
                raise HeinzelError(msg)
            markdown = base64.b64decode(str(content.get("content", "")), validate=False).decode("utf-8")
            for item in new:
                tag, notes = item.get("tag_name"), item.get("body")
                if not isinstance(tag, str) or not tag or not isinstance(notes, str) or not notes:
                    msg = "The real release notes are missing"
                    raise HeinzelError(msg)
                text = json.dumps(
                    {"tag": tag, "release_notes": notes, "changelog_markdown": _section(markdown, tag)},
                    ensure_ascii=False,
                    sort_keys=True,
                )
                revision = hashlib.sha256(json.dumps([item, content.get("sha")], sort_keys=True).encode()).hexdigest()
                records.append(
                    ReleaseRecord(
                        identity=f"{self.repository}:release:{item['id']}",
                        revision=revision,
                        published_at=datetime.fromisoformat(str(item["published_at"])),
                        text=SecretStr(text),
                    )
                )
        return ReleasePage(
            identity=self.identity,
            cursor=_cursor(self.identity, max((_frontier(item) for item in new), default=frontier)),
            releases=tuple(records),
        )

    def close(self) -> None:
        """Release the privately captured gh executable and token; no polling work is backgrounded."""
        self.gh.close()


class GithubReleaseFeeds(ReleaseFeedService):
    """Optional source-only code-host companion for supplied CHANGELOG Markdown and real releases."""

    supported_operations: ClassVar[frozenset[str]] = frozenset({"release-feed"})

    def __init__(self, kernel: Kernel, current: CurrentUser, settings: GithubSettings) -> None:
        self.kernel, self.current, self.settings = kernel, current, settings
        self.record = kernel.module("github")
        self.owner = current.principal().id

    def check(self) -> None:
        """Require the exact owner, selected provider and current settings at every observation.

        Raises:
            HeinzelError: If the captured provider or owner changed.
        """
        selected, _ = self.kernel.selected_capability_provider("code-host")
        context = self.current.context()
        if (
            context.principal != self.current.owner()
            or context.authentication not in {"cli", "api-bearer", "web-session", "web-device", "daemon"}
            or "private:read" not in context.permissions
            or selected is not self.record
            or self.current.principal().id != self.owner
            or self.kernel.resolve(CurrentUser) is not self.current
            or Config.load(Path.home()).settings(GithubSettings, "github") != self.settings
        ):
            msg = "The selected GitHub release source or owner changed"
            raise HeinzelError(msg)

    def open_lease(self, reference: str) -> ReleaseFeedLease:
        """Capture the supplied read source only; never create or modify a release."""
        self.check()
        return _FeedLease(self, reference)
