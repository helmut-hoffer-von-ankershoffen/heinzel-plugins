"""Materialize a frozen Git commit for an isolated focused-check runner."""

from __future__ import annotations

import os
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def _clean_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    return env


@contextmanager
def materialized(repo: Path, revision: str) -> Iterator[Path]:
    """Yield a clean isolated clone of an exact commit, not mutable checkout bytes."""
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        raise ValueError("a full commit id is required")
    env = _clean_env()
    if (
        subprocess.check_output(
            ["git", "--no-replace-objects", "cat-file", "-t", revision], cwd=repo, env=env, text=True, timeout=30
        ).strip()
        != "commit"
    ):
        raise ValueError("a commit is required")
    with tempfile.TemporaryDirectory(prefix="focused-check-", dir=repo.parent) as temporary:
        tree = Path(temporary) / "tree"
        subprocess.run(
            ["git", "--no-replace-objects", "clone", "--quiet", "--no-local", "--no-checkout", str(repo), str(tree)],
            env=env,
            check=True,
            timeout=120,
        )
        subprocess.run(
            ["git", "--no-replace-objects", "checkout", "--quiet", "--detach", revision],
            cwd=tree,
            env=env,
            check=True,
            timeout=120,
        )
        yield tree
