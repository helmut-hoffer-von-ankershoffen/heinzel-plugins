"""Narrow presentation authority for the normal capture environment, never SDK health data."""

import json
import os
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

    def verify(self) -> None:
        try:
            changed = any(_identity(path) != expected for path, expected in self.evidence)
        except OSError:
            changed = True
        if changed:
            raise CaptureError("The owning capture environment changed after prefix verification")


def owning_prefix(root: Path, interpreter: Path) -> OwningPrefix:
    """Attest the tool's fixed .venv; no caller-supplied prefix or external environment gains authority."""
    expected = root.resolve(strict=True) / ".venv"
    binary = expected / "bin/python"
    config = expected / "pyvenv.cfg"
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
    evidence = tuple((path, _identity(path)) for path in paths)
    probe = subprocess.run(
        [str(binary), "-I", "-B", "-c", "import json,sys;print(json.dumps([sys.prefix,sys.executable]))"],
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )
    identity = json.loads(probe.stdout)
    aliases = {str(expected)}
    if sys.platform == "darwin":
        for alias in ("/var", "/tmp"):  # noqa: S108 - inspect fixed OS aliases; no temporary file is created
            canonical = Path("/private" + alias)
            if str(expected).startswith(str(canonical) + "/") and Path(alias).resolve() == canonical:
                aliases.add(str(expected).removeprefix("/private"))
    if (
        not isinstance(identity, list)
        or len(identity) != 2
        or not all(isinstance(value, str) for value in identity)
        or identity[0] not in aliases
        or identity[1] not in {prefix + "/bin/python" for prefix in aliases}
        or Path(identity[0]).resolve(strict=True) != expected
        or Path(identity[1]).resolve(strict=True) != binary.resolve(strict=True)
    ):
        raise CaptureError("The selected Python did not attest the exact owning capture prefix")
    result = OwningPrefix(identity[0], evidence)
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
