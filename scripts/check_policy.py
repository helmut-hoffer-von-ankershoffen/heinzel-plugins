"""Apply conventional-commit and confidentiality safeguards without importing any plugin or core source."""

import os
import subprocess
import sys
from pathlib import Path


def run(*arguments: str) -> None:
    subprocess.run([sys.executable, *arguments], check=True, timeout=120)


def main() -> None:
    base = os.environ.get("CHECK_BASE") or "origin/main"
    revision_range = f"{base}..HEAD"
    commits = subprocess.run(
        ["git", "rev-list", revision_range], check=True, capture_output=True, text=True, timeout=30
    ).stdout
    if commits.strip():
        run("-m", "commitizen", "check", "--rev-range", revision_range)
    scanner = str(Path(__file__).with_name("check_confidentiality.py"))
    run(scanner, *([] if os.environ.get("CONFIDENTIALITY_REQUIRED") == "false" else ["--require"]))
    run(scanner, "--messages", revision_range)
    for key in ("CHECK_TITLE", "CHECK_BRANCH"):
        if value := os.environ.get(key):
            if key == "CHECK_TITLE":
                run("-m", "commitizen", "check", "--message", value)
            run(scanner, "--text", value)


if __name__ == "__main__":
    main()
