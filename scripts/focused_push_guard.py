#!/usr/bin/env -S python3 -I
"""Transaction guard for a reviewed, installed prek pre-push.legacy companion.

This only validates one ref. It does not narrow or replace any stock check.
Install only from independently reviewed bytes with an external immutable policy
receipt. The full focused-check runner is not yet implemented.
"""

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{40}\Z")
REF = re.compile(r"refs/heads/[A-Za-z0-9][A-Za-z0-9._/-]*\Z")


def validate_transaction(raw: bytes, *, repo: Path, git_env: dict[str, str]) -> tuple[str, str, str, str]:
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("push input is not ASCII") from exc
    if len(lines) != 1:
        raise ValueError("one pushed branch is required")
    parts = lines[0].split(" ")
    if len(parts) != 4:
        raise ValueError("malformed push input")
    local_ref, new, remote_ref, old = parts
    if not REF.fullmatch(remote_ref):
        raise ValueError("branch refs required")
    if any(not SHA.fullmatch(sha) or sha == "0" * 40 for sha in (new, old)):
        raise ValueError("existing full SHA refs required")
    if not REF.fullmatch(local_ref):
        if local_ref != new:
            raise ValueError("source must be a branch or the exact new commit")
        # sm ship pushes the checked commit as a literal SHA to the same-named remote branch.
        # Git reports both its branch identity and object ID alongside any dirty paths.
        status = subprocess.check_output(
            [
                "git",
                "--no-replace-objects",
                "status",
                "--porcelain=v2",
                "--branch",
                "--untracked-files=all",
                "--ignore-submodules=none",
                "--no-ahead-behind",
            ],
            cwd=repo,
            env=git_env,
            timeout=30,
        ).splitlines()
        branch = remote_ref.removeprefix("refs/heads/")
        if (
            f"# branch.oid {new}".encode() not in status
            or f"# branch.head {branch}".encode() not in status
            or any(not row.startswith(b"# ") for row in status)
        ):
            raise ValueError("literal source requires the clean checked-out destination branch at the new commit")
    return local_ref, new, remote_ref, old


def main() -> int:
    if os.environ.get("HZ_TRUSTED_FOCUSED_PUSH") != "1":
        return 0
    try:
        if any(os.environ.get(name) for name in ("SKIP", "PREK_SKIP")):
            raise ValueError("skip overrides are forbidden during a focused push")
        if len(sys.argv) != 3:
            raise ValueError("expected remote name and URL")
        hook_dir = Path(__file__).resolve().parent
        spec = importlib.util.spec_from_file_location("installed_focused_trust", hook_dir / "focused_trust.py")
        if spec is None or spec.loader is None:
            raise ValueError("installed focused trust loader is missing")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        repo = Path(
            subprocess.check_output(
                ["git", "--no-replace-objects", "rev-parse", "--show-toplevel"],
                env=module.clean_env(),
                text=True,
                timeout=30,
            ).strip()
        )
        _, new, destination, old = validate_transaction(
            sys.stdin.buffer.read(65537), repo=repo, git_env=module.clean_env()
        )
        pin, _ = module.load(hook_dir, repo, sys.argv[1], sys.argv[2], old, new, "guard")
        if destination != pin["destination"]:
            raise ValueError("destination ref does not match the independent pin")
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"focused push guard: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
