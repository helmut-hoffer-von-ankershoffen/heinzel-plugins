"""Deterministic privacy guards for screenshot captures: no agent decides what may be published.

A capture is refused when the text a scene shows (DOM text, input values, the document title and the URL, or a CLI
transcript) matches a credential, a real email address, a private path, a private hostname, a non-documentation IP
address or a configured confidential term. Captions come from the checked-in definition; the images themselves are
reviewed in the pull request diff like any other change.
"""

import importlib.util
import ipaddress
import os
import re
import socket
import stat
import sys
from pathlib import Path

DRAFT = Path(".preview/screenshots/draft")

# Credentials, in the spirit of the repository's gitleaks rules (scripts/tools.toml pins gitleaks for the commits).
SECRET_PATTERNS = (
    r"(?:[?#&](?:access_)?token=)[A-Za-z0-9_-]+",
    r"Bearer\s+[A-Za-z0-9._-]{12,}",
    r"gh[pousr]_[A-Za-z0-9]{16,}",
    r"github_pat_[A-Za-z0-9_]{22,}",
    r"glpat-[A-Za-z0-9_-]{20,}",
    r"sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}",
    r"(?:sk|rk)_live_[A-Za-z0-9]{16,}",
    r"xox[abposr]-[A-Za-z0-9-]{10,}",
    r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",
    r"\bAIza[0-9A-Za-z_-]{35}\b",
    r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}",
    r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY(?: BLOCK)?-----",
    r"\b(?:api[_-]?key|secret|password|passwd|client[_-]?secret|auth[_-]?token)\b\s*[:=]\s*[\"']?[A-Za-z0-9_+/=-]{16,}",
)
PRIVATE_PATH = r"(?:/Users/|/home/|/private/var/folders/|/var/folders/|/private/tmp/|/tmp/|[A-Za-z]:\\Users\\)[^\s/\\]+"
EMAIL = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
FICTIONAL_EMAIL = ("@example.com", ".example", "@example.org", "@example.net", "@example.test")
PRIVATE_HOST = r"\b(?:[A-Za-z0-9-]+\.)+(?:local|localdomain|lan|internal|intranet|corp|home|ts\.net)\b"
IPV4 = r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"
FICTIONAL_HOSTS = {"localhost", "demo-host", "demo-workstation"}


class CaptureError(ValueError):
    """A deliberate safe author-facing error, without arbitrary provider or parser output."""


class StaleGallery(CaptureError):
    """The committed gallery no longer matches its UI inputs; `command` regenerates it."""

    def __init__(self, message: str, command: str) -> None:
        super().__init__(message)
        self.command = command


def canonical_text(value: str) -> str:
    """Match commit hooks before hashing generated text: LF, no trailing whitespace, one final newline."""
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = "\n".join(line.rstrip() for line in value.split("\n")).rstrip()
    return value + "\n" if value else ""


def safe_path(root: Path, relative: Path | str) -> Path:
    """Reject linked paths before reading or writing an owning project's artifacts."""
    root = root.resolve()
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise CaptureError("Screenshot artifacts must stay inside their owning project")
    current = root
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise CaptureError("Screenshot artifacts cannot follow symbolic links")
    if not current.resolve().is_relative_to(root):
        raise CaptureError("Screenshot artifacts must stay inside their owning project")
    return current


def atomic_text(path: Path, content: str) -> None:
    """Replace a regular owned file without following a previous destination link."""
    import tempfile

    if path.is_symlink():
        raise CaptureError("Screenshot artifacts cannot follow symbolic links")
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        temporary.write(content)
        staged = Path(temporary.name)
    try:
        if path.is_symlink():
            raise CaptureError("Screenshot artifacts cannot follow symbolic links")
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)


def regular_bytes(path: Path, limit: int) -> bytes:
    """Read a bounded regular, unlinked file."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
                raise CaptureError(f"{path.name} must be a bounded regular file")
            return stream.read(limit + 1)
    except OSError as error:
        raise CaptureError(f"{path.name} must be a bounded regular file") from error


def _confidentiality_module():
    """The repository's confidential-terms checker (scripts/check_confidentiality.py), when this is a checkout."""
    script = Path(__file__).resolve().parents[2] / "scripts/check_confidentiality.py"
    if not script.is_file():
        return None
    spec = importlib.util.spec_from_file_location("_hz_confidentiality", script)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def terms_required() -> bool:
    """In CI the terms must be configured (as the policy job requires them), unless CONFIDENTIALITY_REQUIRED=false."""
    return os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("CONFIDENTIALITY_REQUIRED") != "false"


_WARNED: list[bool] = []


def confidential_patterns() -> list[re.Pattern[str]]:
    """The configured confidential terms as the commit hook matches them.

    Without terms the guard cannot scan for them: CI fails (`terms_required`), a local run warns once on stderr.
    """
    module = _confidentiality_module()
    terms = module.load_terms() if module else []
    if not terms:
        if terms_required():
            raise CaptureError(
                "No confidential terms are configured, so the screenshot guard would scan for none. "
                "Set CONFIDENTIAL_TERMS from the repository secret (or CONFIDENTIALITY_REQUIRED=false where none exist)"
            )
        if not _WARNED:
            _WARNED.append(True)
            print(
                "warning: no confidential terms are configured (CONFIDENTIAL_TERMS or "
                "~/.config/heinzel-dev/confidential-terms); the screenshot guard checks everything else",
                file=sys.stderr,
            )
        return []
    return module.patterns(terms)


def _private_ip(text: str) -> bool:
    for candidate in re.findall(IPV4, text):
        try:
            address = ipaddress.IPv4Address(candidate)
        except ValueError:
            continue
        documentation = any(
            address in ipaddress.IPv4Network(network)
            for network in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
        )
        if not (address.is_loopback or address.is_unspecified or documentation):
            return True
    return False


def _private_host(text: str) -> bool:
    for match in re.finditer(PRIVATE_HOST, text, re.I):
        labels = match.group(0).lower().split(".")
        if not any("example" in label or label in FICTIONAL_HOSTS for label in labels):
            return True
    return False


def scan_text(value: str, *, terms: list[re.Pattern[str]] | None = None) -> None:
    """Refuse recognizable credentials, personal identity, host identity and confidential terms."""
    if any(re.search(pattern, value, re.I) for pattern in SECRET_PATTERNS):
        raise CaptureError("Capture text contains a possible credential; use fictional fixtures and capture again")
    if re.search(PRIVATE_PATH, value) or any(
        not email.lower().endswith(FICTIONAL_EMAIL) for email in re.findall(EMAIL, value)
    ):
        raise CaptureError("Capture text contains private paths or personal identity; use fictional demonstration data")
    if _private_host(value) or _private_ip(value):
        raise CaptureError("Capture text contains a private hostname or IP address; use example or documentation ones")
    private = [str(Path.home()), socket.gethostname()]
    if any(part not in FICTIONAL_HOSTS and len(part) > 3 and part in value for part in private):
        raise CaptureError("Capture text contains host-specific information; replace it with a fictional fixture")
    if any(pattern.search(value) for pattern in (confidential_patterns() if terms is None else terms)):
        raise CaptureError("Capture text contains a confidential term; use fictional demonstration data")


def page_text(page) -> str:
    """Everything a UI scene can show: DOM text, form values, the document title and the URL."""
    body = page.locator("body").inner_text()
    forms = page.locator("input,textarea").evaluate_all("els => els.map(el => el.value).join('\\n')")
    title = page.title()
    return "\n".join(str(part or "") for part in (body, forms, title, page.url))
