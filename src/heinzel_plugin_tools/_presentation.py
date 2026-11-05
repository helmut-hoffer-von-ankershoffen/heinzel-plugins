"""Narrow presentation authority for the normal capture environment, never SDK health data."""

import json
import os
import re
import socket
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from heinzel_plugin_tools.privacy import CaptureError


def _identity(path: Path) -> tuple[int, int, int, int, int, int, int]:
    value = path.lstat()
    return value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns


@dataclass(frozen=True)
class OwningPrefix:
    """A fixed, attested project prefix with replacement-sensitive filesystem evidence."""

    prefix: str
    evidence: tuple[tuple[Path, tuple[int, int, int, int, int, int, int]], ...]

    hostname: str | None = None

    def verify(self) -> None:
        try:
            changed = (self.hostname is not None and socket.gethostname() != self.hostname) or any(
                _identity(path) != expected for path, expected in self.evidence
            )
        except OSError:
            changed = True
        if changed:
            raise CaptureError("The owning capture environment changed after prefix verification")


def _validate_environment(expected: Path, binary: Path, config: Path, interpreter: Path) -> None:
    """Refuse unsafe roots, aliases, ownership, permissions and non-owning selection."""
    if expected in {Path(expected.anchor), Path.home().resolve()}:
        raise CaptureError("A root or home directory cannot be an owning capture prefix")
    for path in (expected, expected / "bin", config):
        value = path.lstat()
        if path.is_symlink() or (hasattr(os, "getuid") and value.st_uid != os.getuid()) or value.st_mode & 0o022:
            raise CaptureError("The owning capture environment must be private, owned and free of directory aliases")
    if not expected.is_dir() or not (expected / "bin").is_dir() or not stat.S_ISREG(config.stat().st_mode):
        raise CaptureError("The owning capture environment is not a normal project .venv")
    if interpreter.absolute() != binary:
        raise CaptureError("The selected Python is not the normal owning capture interpreter")


def _interpreter_paths(expected: Path, binary: Path, config: Path) -> list[Path]:
    """Boundedly retain every alias identity, refusing cycles and foreign virtual environments."""
    paths = [expected, expected / "bin", config]
    current = binary
    for _ in range(16):
        if current in paths:
            raise CaptureError("The owning capture interpreter has a cyclic alias")
        if current.parent.name == "bin" and current.parent.parent != expected:
            if (current.parent.parent / "pyvenv.cfg").exists():
                raise CaptureError("The owning capture interpreter aliases a foreign environment")
        paths.append(current)
        if not current.is_symlink():
            break
        target = current.readlink()
        current = target if target.is_absolute() else current.parent / target
    else:
        raise CaptureError("The owning capture interpreter has too many aliases")
    return paths


def _prefix_aliases(expected: Path) -> set[str]:
    """Recognize fixed Darwin OS aliases only when they reach the same canonical directory."""
    aliases = {str(expected)}
    if sys.platform == "darwin":
        for alias in ("/var", "/tmp"):  # noqa: S108 - inspect fixed OS aliases; no temporary file is created
            canonical = Path("/private" + alias)
            if str(expected).startswith(str(canonical) + "/") and Path(alias).resolve() == canonical:
                aliases.add(str(expected).removeprefix("/private"))
    return aliases


def _verify_reported_identity(identity: object, expected: Path, binary: Path) -> tuple[str, str]:
    """Bind reported prefix/executable and independent hostname to the validated environment."""
    aliases = _prefix_aliases(expected)
    if (
        not isinstance(identity, list)
        or len(identity) != 3
        or not all(isinstance(value, str) for value in identity)
        or identity[0] not in aliases
        or identity[1] not in {prefix + "/bin/python" for prefix in aliases}
        or Path(identity[0]).resolve(strict=True) != expected
        or Path(identity[1]).resolve(strict=True) != binary.resolve(strict=True)
    ):
        raise CaptureError("The selected Python did not attest the exact owning capture prefix")
    if identity[2] != socket.gethostname() or not re.fullmatch(
        r"(?=.{1,253}\Z)[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
        r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*",
        identity[2],
    ):
        raise CaptureError("The selected Python did not attest the same unambiguous controller hostname")
    return identity[0], identity[2]


def owning_prefix(root: Path, interpreter: Path) -> OwningPrefix:
    """Attest the tool's fixed .venv; no caller-supplied prefix or external environment gains authority."""
    expected = root.resolve(strict=True) / ".venv"
    binary = expected / "bin/python"
    config = expected / "pyvenv.cfg"
    _validate_environment(expected, binary, config, interpreter)
    paths = _interpreter_paths(expected, binary, config)
    evidence = tuple((path, _identity(path)) for path in paths)
    probe = subprocess.run(
        [
            str(binary),
            "-I",
            "-B",
            "-c",
            "import json,socket,sys;print(json.dumps([sys.prefix,sys.executable,socket.gethostname()]))",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )
    prefix, hostname = _verify_reported_identity(json.loads(probe.stdout), expected, binary)
    result = OwningPrefix(prefix, evidence, hostname)
    result.verify()
    return result


def redact_owning_prefix(page, identity: OwningPrefix) -> None:
    """Change only exact prefix tokens in rendered text; leave health models, rows and other text intact."""
    identity.verify()
    page.evaluate(
        r"""prefix => {
          const escape = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
          const pattern = new RegExp('(^|[\\s(\\[\\{\\x22\\x27=])' + escape(prefix) +
            '(?=$|[/\\s)\\]\\}\\x22\\x27])(?:/[^\\s()\\[\\]{}\\x22\\x27<>]*)?', 'g');
          const scrub = text => {
            // A URL/email-bearing node is ambiguous, including whitespace inside query values.
            // Leave it for the ordinary scanner rather than interpreting it as path presentation.
            if (/[a-z][a-z0-9+.-]*:\/\/|mailto:|@/i.test(text)) return text;
            return text.replace(pattern, (match, lead) => {
            const path = match.slice(lead.length);
            const suffix = path.slice(prefix.length);
            // No normalization/decoding grants authority to a different spelling of a path.
            if (/[\\%?#]/.test(suffix) ||
                (suffix && suffix.slice(1).split('/').some(part => ['', '.', '..'].includes(part)))) return match;
            return lead + '/demo-profile/.venv' + path.slice(prefix.length);
            });
          };
          const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          let node;
          while ((node = walker.nextNode())) {
            if (['SCRIPT', 'STYLE'].includes(node.parentElement?.tagName)) continue;
            const next = scrub(node.textContent);
            if (next !== node.textContent) node.textContent = next;
          }
        }""",
        identity.prefix,
    )


def redact_doctor_hostname(page, identity: OwningPrefix) -> None:
    """Fictionalize only Doctor's unique, whole hostname detail; never generic hostname tokens."""
    identity.verify()
    if identity.hostname is None:
        return
    outcome = page.evaluate(
        r"""hostname => {
          if (location.pathname !== '/doctor') return 'not-doctor';
          const tables = [...document.querySelectorAll('table')];
          const rows = tables.flatMap(table => [...table.querySelectorAll(':scope > tbody > tr')]);
          const matches = rows.filter(row => row.cells[0]?.textContent === 'system.doctor' &&
            row.cells[1]?.textContent === 'hostname');
          if (tables.length !== 1 || matches.length !== 1) return 'refused';
          const row = matches[0], cells = [...row.cells];
          const headers = tables[0].querySelectorAll(':scope > thead > tr > th[scope="col"]');
          if (cells.length !== 5 || cells.some(cell => cell.tagName !== 'TD') || headers.length !== 5 ||
              tables[0].querySelectorAll(':scope > caption').length !== 1) return 'refused';
          const detail = cells[3];
          if (detail.childNodes.length !== 1 || detail.firstChild.nodeType !== Node.TEXT_NODE ||
              detail.firstChild.textContent !== hostname) return 'refused';
          detail.firstChild.textContent = 'demo-host';
          return 'redacted';
        }""",
        identity.hostname,
    )
    if outcome not in {"not-doctor", "redacted"}:
        raise CaptureError("Doctor hostname presentation is ambiguous; capture refused without changing its detail")
