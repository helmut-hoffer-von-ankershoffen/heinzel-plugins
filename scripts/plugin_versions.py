"""A plugin version bump must ship something, and every bumped version gets released (ADR 0114)."""

import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath

PLUGINS = "plugins"
NOT_SHIPPED = ("tests", "docs", "media", "screenshots")


def _git(*arguments: str) -> str:
    return subprocess.run(  # noqa: S603 - fixed git commands
        ["git", *arguments],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout


def _shipped(path: str, plugin: str) -> bool:
    relative = PurePosixPath(path).relative_to(f"{PLUGINS}/{plugin}")
    return relative.parts[0] not in NOT_SHIPPED and relative.suffix != ".md" and str(relative) != "pyproject.toml"


def _pyproject(revision: str, plugin: str) -> str:
    try:
        return _git("show", f"{revision}:{PLUGINS}/{plugin}/pyproject.toml")
    except subprocess.CalledProcessError:
        return ""


def _version(text: str) -> str | None:
    return tomllib.loads(text).get("project", {}).get("version") if text else None


def _shipped_metadata(text: str) -> dict[str, object]:
    """The project file without its version and the catalog's screenshots, which never reach a wheel."""
    data = tomllib.loads(text)
    data.get("project", {}).pop("version", None)
    data.get("tool", {}).get("heinzel", {}).pop("catalog", None)
    return data


def unjustified_bumps(base: str, head: str = "HEAD") -> list[str]:
    """Plugins whose version changed in `base..head` although nothing they ship did."""
    changed: dict[str, list[str]] = {}
    for path in _git("diff", "--name-only", f"{base}...{head}").splitlines():
        parts = PurePosixPath(path).parts
        if len(parts) > 2 and parts[0] == PLUGINS:  # noqa: PLR2004 - plugins/<name>/<path>
            changed.setdefault(parts[1], []).append(path)
    bumps = []
    for plugin, paths in sorted(changed.items()):
        before, after = _pyproject(base, plugin), _pyproject(head, plugin)
        if not before or not after or _version(before) == _version(after):
            continue
        metadata_changed = _shipped_metadata(before) != _shipped_metadata(after)
        if not metadata_changed and not any(_shipped(path, plugin) for path in paths):
            bumps.append(plugin)
    return bumps


def unreleased(root: Path, tags: set[str]) -> list[str]:
    """Plugins in `root` whose current version has no release tag yet."""
    names = []
    for path in sorted((root / PLUGINS).glob("*/pyproject.toml")):
        project = tomllib.loads(path.read_text(encoding="utf-8"))["project"]
        if f"{project['name']}/v{project['version']}" not in tags:
            names.append(project["name"])
    return names


def main(arguments: list[str]) -> int:
    """`check <base>` refuses a bump that ships nothing; `unreleased` lists what needs a release."""
    if arguments[:1] == ["check"] and len(arguments) == 2:  # noqa: PLR2004
        bumps = unjustified_bumps(arguments[1])
        for plugin in bumps:
            print(
                f"{plugin}: the version changed but nothing it ships did; revert the bump, because every new version "
                "must become a release.",
                file=sys.stderr,
            )
        return 1 if bumps else 0
    if arguments == ["unreleased"]:
        print("\n".join(unreleased(Path(), set(_git("tag", "--list").splitlines()))))
        return 0
    print(main.__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
