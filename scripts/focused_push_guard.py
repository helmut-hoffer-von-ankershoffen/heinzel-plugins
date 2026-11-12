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


def validate_transaction(raw: bytes) -> tuple[str, str, str, str]:
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
    if not REF.fullmatch(local_ref) or not REF.fullmatch(remote_ref):
        raise ValueError("branch refs required")
    if any(not SHA.fullmatch(sha) or sha == "0" * 40 for sha in (new, old)):
        raise ValueError("existing full SHA refs required")
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
        _, new, destination, old = validate_transaction(sys.stdin.buffer.read(65537))
        repo = Path(
            subprocess.check_output(
                ["git", "--no-replace-objects", "rev-parse", "--show-toplevel"],
                env=module.clean_env(),
                text=True,
                timeout=30,
            ).strip()
        )
        pin, _ = module.load(hook_dir, repo, sys.argv[1], sys.argv[2], old, new, "guard")
        if destination != pin["destination"]:
            raise ValueError("destination ref does not match the independent pin")
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"focused push guard: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
