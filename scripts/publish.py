# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Run the toolkit's immutable artifact publisher for existing workflow callers."""

import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
result = subprocess.run(
    [
        "uv",
        "run",
        "--project",
        str(root),
        "--frozen",
        "--no-build",
        "--group",
        "tooling",
        "python",
        "-m",
        "heinzel_plugin_tools.publishing",
        *sys.argv[1:],
    ],
    check=False,
)
raise SystemExit(result.returncode)
