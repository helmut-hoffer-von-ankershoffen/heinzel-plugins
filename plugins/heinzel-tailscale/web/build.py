# /// script
# requires-python = ">=3.12"
# dependencies = ["nodejs-wheel-binaries==24.19.0"]
# ///
"""Pinned Node and pnpm for this plugin's frontend, independent of a core checkout."""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import nodejs_wheel

web = Path(__file__).resolve().parent
node = Path(nodejs_wheel.__file__).parent / "bin"
env = dict(os.environ)
env["PATH"] = str(node) + os.pathsep + env.get("PATH", "")
env["npm_config_update_notifier"] = "false"
# The package manager itself is pinned; every frontend dependency is locked by this project.
npm = node.parent / "lib/node_modules/npm/bin/npm-cli.js"
command = [str(node / "node"), str(npm), "exec", "--yes", "--package=pnpm@12.15.0", "--", "pnpm"]
args = sys.argv[1:] or ["run", "build"]
stamp = web / "node_modules/.heinzel-lock"
initializing = args[0] == "install" and "--no-frozen-lockfile" in args
digest = "" if initializing else hashlib.sha256((web / "pnpm-lock.yaml").read_bytes()).hexdigest()
if not initializing and (not stamp.is_file() or stamp.read_text() != digest):
    subprocess.run(  # noqa: S603 - pinned package manager, no shell
        [*command, "install", "--frozen-lockfile", "--prefer-offline"], cwd=web, env=env, check=True, timeout=600
    )
    stamp.write_text(digest)
sys.exit(subprocess.run([*command, *args], cwd=web, env=env, check=False, timeout=600).returncode)  # noqa: S603 - CLI arguments, no shell
