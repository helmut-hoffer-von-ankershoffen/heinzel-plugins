# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Compatibility entry point for existing CI callers; implementation ships in the developer toolkit wheel."""

import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
result = subprocess.run(
    ["uv", "run", "--project", str(root), "--frozen", "--no-build", "--group", "tooling", "hz-plugin", *sys.argv[1:]],
    check=False,
)
raise SystemExit(result.returncode)
