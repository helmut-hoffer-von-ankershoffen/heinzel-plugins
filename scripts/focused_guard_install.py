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
from pathlib import Path


def digest(path: Path) -> str:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise ValueError(f"{path}: expected a regular file")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install(source: Path, hook_dir: Path, source_sha256: str, shim_sha256: str) -> None:
    if len(source_sha256) != 64 or len(shim_sha256) != 64:
        raise ValueError("expected full independent SHA-256 pins")
    shim = hook_dir / "pre-push"
    target = hook_dir / "pre-push.legacy"
    if digest(shim) != shim_sha256 or not os.access(shim, os.X_OK):
        raise ValueError("stock prek shim is missing or differs from its pin")
    if digest(source) != source_sha256:
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
    if digest(target) != source_sha256:
        target.unlink(missing_ok=True)
        raise ValueError("installed companion digest mismatch")
    if digest(shim) != shim_sha256:
        target.unlink(missing_ok=True)
        raise ValueError("stock shim changed during installation")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("hook_dir", type=Path)
    parser.add_argument("--reviewed-source-sha256", required=True)
    parser.add_argument("--stock-shim-sha256", required=True)
    args = parser.parse_args()
    install(args.source, args.hook_dir, args.reviewed_source_sha256, args.stock_shim_sha256)


if __name__ == "__main__":
    main()
