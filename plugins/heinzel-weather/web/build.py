# /// script
# requires-python = ">=3.12"
# dependencies = ["nodejs-wheel-binaries==24.19.0"]
# ///
"""Pinned Node and pnpm for the Weather view's frontend, independent of a core checkout."""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import nodejs_wheel

WEB = Path(__file__).resolve().parent
NODE_BIN = Path(nodejs_wheel.__file__).parent / "bin"
PNPM_VERSION = "12.15.0"
LOCK_STAMP = WEB / "node_modules/.heinzel-lock"
LOCKFILE = WEB / "pnpm-lock.yaml"
TIMEOUT_SECONDS = 600

# The only pnpm invocations this project makes: its own check steps and the (re)install of its locked dependencies.
# Command-line text never reaches the process; it only selects one of these fixed argument lists.
INVOCATIONS: dict[tuple[str, ...], tuple[str, ...]] = {
    ("install",): ("install",),
    ("install", "--frozen-lockfile"): ("install", "--frozen-lockfile"),
    ("install", "--no-frozen-lockfile"): ("install", "--no-frozen-lockfile"),
    ("run", "build"): ("run", "build"),
    ("run", "lint"): ("run", "lint"),
    ("run", "test"): ("run", "test"),
    ("run", "typecheck"): ("run", "typecheck"),
}


def pnpm(arguments: tuple[str, ...]) -> int:
    """Run the pinned pnpm, through the pinned npm of the pinned Node, in the web directory."""
    environment = {
        **os.environ,
        "PATH": str(NODE_BIN) + os.pathsep + os.environ.get("PATH", ""),
        "npm_config_update_notifier": "false",
    }
    npm = NODE_BIN.parent / "lib/node_modules/npm/bin/npm-cli.js"
    command = [str(NODE_BIN / "node"), str(npm), "exec", "--yes", f"--package=pnpm@{PNPM_VERSION}", "--", "pnpm"]
    return subprocess.run(  # noqa: S603
        [*command, *arguments], cwd=WEB, env=environment, check=False, timeout=TIMEOUT_SECONDS
    ).returncode


def main(requested: list[str]) -> int:
    """Install the locked dependencies when the lockfile changed, then run the one allowed invocation."""
    arguments = INVOCATIONS.get(tuple(requested or ["run", "build"]))
    if arguments is None:
        allowed = ", ".join(" ".join(key) for key in INVOCATIONS)
        sys.stderr.write(f"unsupported pnpm invocation {requested!r}; allowed: {allowed}\n")
        return 2
    if arguments[0] == "install" and "--no-frozen-lockfile" in arguments:
        return pnpm(arguments)
    digest = hashlib.sha256(LOCKFILE.read_bytes()).hexdigest()
    if not LOCK_STAMP.is_file() or LOCK_STAMP.read_text() != digest:
        installed = pnpm(("install", "--frozen-lockfile", "--prefer-offline"))
        if installed != 0:
            return installed
        LOCK_STAMP.write_text(digest)
    return pnpm(arguments)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
