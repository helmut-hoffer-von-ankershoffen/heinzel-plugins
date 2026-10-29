# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Select a compatible released core or download a built candidate from official core CI."""

import os
import subprocess
from pathlib import Path
from urllib.parse import urlsplit


def select(url: str, run: str) -> str:
    if url:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.username or parsed.password or any(ord(char) < 32 for char in url):
            raise ValueError("Use a single HTTPS candidate wheel URL")
        return url
    if run:
        if not run.isascii() or not run.isdigit():
            raise ValueError("Core run must be a numeric official Actions run ID")
        destination = Path(".candidates/core").resolve()
        destination.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "gh",
                "run",
                "download",
                run,
                "--repo",
                "helmut-hoffer-von-ankershoffen/heinzel",
                "--name",
                "plugin-core",
                "--dir",
                str(destination),
            ],
            check=True,
            timeout=120,
        )
        wheels = list(destination.glob("heinzel-*.whl"))
        if len(wheels) != 1 or any(ord(char) < 32 for char in str(wheels[0])):
            raise ValueError("The candidate artifact must contain exactly one core wheel")
        return str(wheels[0])
    return ""


if __name__ == "__main__":
    wheel = select(os.environ.get("CORE_URL", ""), os.environ.get("CORE_RUN", ""))
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(f"wheel={wheel}\n")
