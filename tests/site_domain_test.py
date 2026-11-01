"""The product site lives on heinzel.team; the owner's personal domain must not creep back into the repository."""

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[1]
# Built from parts so this file does not contain the string it forbids.
OLD_DOMAIN = "hoffer-von-ankershoffen" + ".me"


def test_no_tracked_file_points_at_the_old_site_domain() -> None:
    """Released versions and installs still use the old URLs, and GitHub redirects them; new text must not."""
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
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary files
        if OLD_DOMAIN in text:
            offenders.append(name)
    assert not offenders, f"These files still use the old site domain; use https://heinzel.team/: {offenders}"
