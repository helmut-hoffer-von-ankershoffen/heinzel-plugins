# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Install an owning project's declared browser OS libraries only in explicit CI/release setup."""

import json
import os
import re
import subprocess
from pathlib import Path

from heinzel_plugin_tools.cli import projects


def bootstrap(name: str, root: Path) -> bool:
    """Resolve metadata without importing a plugin, then run its explicit locked browser dependency declaration."""
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 100:
        raise ValueError("Choose a canonical plugin distribution or short name")
    root = root.resolve()
    selected = [item for item in projects(root) if name in (item.name, item.name.removeprefix("heinzel-"))]
    if len(selected) != 1:
        raise ValueError("Choose exactly one owning plugin")
    owner = selected[0].directory.resolve()
    owner.relative_to(root)
    directory = owner / "tests/browser"
    directory.resolve().relative_to(owner)
    package = directory / "package.json"
    if not package.is_file():
        return False
    package.resolve().relative_to(directory.resolve())
    metadata = json.loads(package.read_text())
    if "browser:install-deps" not in metadata.get("scripts", {}):
        return False
    lock = directory / "package-lock.json"
    if not lock.is_file():
        raise ValueError("Declared browser libraries require the owning package-lock.json")
    lock.resolve().relative_to(directory.resolve())
    # Inherit the owning workflow job deadline, as the original inline setup did.
    # A separate subprocess timeout can kill npm while leaving its APT child alive.
    subprocess.run(["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"], cwd=directory, check=True)
    subprocess.run(["npm", "run", "--ignore-scripts", "browser:install-deps"], cwd=directory, check=True)
    return True


def bootstrap_profile(profile: str, root: Path) -> None:
    """Prepare the projects whose installed wheels the published composition actually accepts."""
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", profile):
        raise ValueError("Choose a canonical composition profile")
    for project in projects(root):
        if profile in project.options.get("profiles", []):
            bootstrap(project.name, root)


if __name__ == "__main__":
    if profile := os.environ.get("BROWSER_PROFILE"):
        if os.environ.get("PLUGIN"):
            raise ValueError("Choose one project or one composition profile")
        bootstrap_profile(profile, Path.cwd())
    else:
        bootstrap(os.environ["PLUGIN"], Path.cwd())
