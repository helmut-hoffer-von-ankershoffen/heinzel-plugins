"""Route stock hook checks to their normal or independently pinned focused implementation."""

import os
import subprocess
import sys


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"tooling", "owners"}:
        raise SystemExit("expected tooling or owners")
    mode = sys.argv[1]
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
    raise SystemExit(subprocess.run(command, check=False).returncode)  # noqa: S603 - fixed commands


if __name__ == "__main__":
    main()
