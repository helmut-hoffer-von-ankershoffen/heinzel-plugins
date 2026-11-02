"""The public quick start is plain ``uvx heinzel``; versions come from the release profile, not a ``@latest`` suffix."""

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[1]
# Built from parts so this file does not contain the string it forbids.
FORBIDDEN = "heinzel" + "@latest"
# The example plugin's README is part of its source-bound screenshot fingerprint: changing it needs a fresh capture and
# an independent image review plus a plugin release. Remove this entry in that change.
PENDING_RECAPTURE = {"plugins/heinzel-example/README.md"}
TEXT_SUFFIXES = {".md", ".html", ".htm", ".txt", ".toml", ".yml", ".yaml", ".json", ".py", ".sh", ".j2", ".jinja"}


def test_no_docs_or_site_file_uses_the_latest_suffix() -> None:
    """Catalog pages, READMEs and the site footer render this command; a suffix would put it back on the live site."""
    listed = subprocess.run(
        ["git", "ls-files", "-z"],  # noqa: S607 - git from PATH
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout
    offenders = []
    for name in filter(None, listed.split("\0")):
        path = REPO / name
        if name in PENDING_RECAPTURE or path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if FORBIDDEN in text:
            offenders.append(name)
    assert not offenders, f"Use plain `uvx heinzel` (no version suffix) in: {offenders}"
