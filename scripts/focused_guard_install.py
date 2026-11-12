#!/usr/bin/env python3
"""Install an independently reviewed companion without replacing the prek shim.

This installer is deliberately not wired into setup until the focused dispatcher
and its externally pinned policy are reviewed. It never overwrites a legacy hook.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import subprocess
from pathlib import Path


def digest(path: Path, root: Path) -> str:
    """Hash a regular file that stays lexically inside the given root; the check precedes any access."""
    base = os.path.realpath(root)
    if not os.path.abspath(path).startswith(base + os.sep):
        raise ValueError(f"{path}: outside {root}")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise ValueError(f"{path}: expected a regular file")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install(source: Path, hook_dir: Path, source_sha256: str, shim_sha256: str) -> None:
    if len(source_sha256) != 64 or len(shim_sha256) != 64:
        raise ValueError("expected full independent SHA-256 pins")
    hook_dir = Path(os.path.realpath(hook_dir))
    shim = hook_dir / "pre-push"
    target = hook_dir / "pre-push.legacy"
    if digest(shim, hook_dir) != shim_sha256 or not os.access(shim, os.X_OK):
        raise ValueError("stock prek shim is missing or differs from its pin")
    if digest(source, source.parent) != source_sha256:
        raise ValueError("companion source differs from its review pin")
    # Never overwrite an existing legacy hook, including a symlink.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o700)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(source.read_bytes())
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    if digest(target, hook_dir) != source_sha256:
        target.unlink(missing_ok=True)
        raise ValueError("installed companion digest mismatch")
    if digest(shim, hook_dir) != shim_sha256:
        target.unlink(missing_ok=True)
        raise ValueError("stock shim changed during installation")


def confined(candidate: Path, root: Path) -> Path:
    """Resolve a path and refuse anything outside the given root (no traversal, no symlink escape)."""
    resolved = os.path.realpath(candidate)
    base = os.path.realpath(root)
    if resolved != base and not resolved.startswith(base + os.sep):
        raise ValueError(f"{candidate}: outside {root}")
    return Path(resolved)


def git_path(*args: str) -> Path:
    out = subprocess.run(  # noqa: S603 - fixed git command without caller input
        ["git", "rev-parse", *args], check=True, capture_output=True, text=True
    ).stdout.strip()
    return Path(out).resolve()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="companion inside this checkout")
    parser.add_argument("--reviewed-source-sha256", required=True)
    parser.add_argument("--stock-shim-sha256", required=True)
    args = parser.parse_args()
    # The hook directory comes from git, never from the command line; the source must live inside this checkout.
    toplevel = git_path("--show-toplevel")
    hook_dir = git_path("--git-path", "hooks")
    install(confined(args.source, toplevel), hook_dir, args.reviewed_source_sha256, args.stock_shim_sha256)


if __name__ == "__main__":
    main()
