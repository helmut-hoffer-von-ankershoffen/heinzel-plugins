"""Route stock hook checks to their normal or independently pinned focused implementation."""

import os
import subprocess
import sys

MODES = {"tooling": "tooling", "owners": "owners"}


def main() -> None:
    # Only a literal from this table ever reaches the command; the argument merely selects it.
    mode = MODES.get(sys.argv[1]) if len(sys.argv) == 2 else None
    if mode is None:
        raise SystemExit("expected tooling or owners")
    focused = os.environ.get("HZ_TRUSTED_FOCUSED_PUSH") == "1"
    pre_push = bool(os.environ.get("PRE_COMMIT_FROM_REF") and os.environ.get("PRE_COMMIT_TO_REF"))
    if focused and not pre_push:
        raise SystemExit("focused push requires exact hook-supplied revisions")
    if focused:
        command = [
            "uv",
            "run",
            "--no-env-file",
            "--project",
            os.getcwd(),
            "--frozen",
            "--group",
            "tooling",
            "python",
            "scripts/focused_dispatch.py",
            mode,
        ]
    elif mode == "tooling":
        command = ["make", "check-fast"]
    else:
        command = ["uv", "run", "--frozen", "--group", "tooling", "hz-plugin", "check-changed", "--git-hook"]
    # make check-fast runs the tooling tests, whose fixture git must not reach the pushing worktree through GIT_*.
    # check-changed reads the hook's index itself (a partial commit has its own) and strips GIT_* for its children.
    hook_free = {"env": {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}}
    options = hook_free if mode == "tooling" else {}
    raise SystemExit(subprocess.run(command, check=False, **options).returncode)  # noqa: S603 - fixed commands


if __name__ == "__main__":
    main()
