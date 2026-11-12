"""A plugin version bump must ship something, carry its changelog section, and get released (ADR 0114)."""

import re
import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath

PLUGINS = "plugins"
REVISION = re.compile(r"[0-9A-Za-z][0-9A-Za-z_./~^-]*")
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


def _changelog(revision: str, plugin: str) -> str:
    try:
        return _git("show", f"{revision}:{PLUGINS}/{plugin}/CHANGELOG.md")
    except subprocess.CalledProcessError:
        return ""


def changelog_sections(text: str) -> list[tuple[str, str]]:
    """Each `## <heading>` of a changelog with its stripped text, top first."""
    sections: list[tuple[str, list[str]]] = []
    for line in text.splitlines():
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif sections:
            sections[-1][1].append(line)
    return [(heading, "\n".join(lines).strip()) for heading, lines in sections]


def changelog_section(text: str, version: str) -> str:
    """The non-empty text of the `## <version>` section, or "" when it is missing or empty."""
    return next((body for heading, body in changelog_sections(text) if heading == version), "")


def _version(text: str) -> str | None:
    return tomllib.loads(text).get("project", {}).get("version") if text else None


def _shipped_metadata(text: str) -> dict[str, object]:
    """The project file without its version and the catalog's screenshots, which never reach a wheel."""
    data = tomllib.loads(text)
    data.get("project", {}).pop("version", None)
    data.get("tool", {}).get("heinzel", {}).pop("catalog", None)
    return data


def unjustified_bumps(base: str, head: str = "HEAD") -> list[str]:
    """Plugins whose version changed in `base..head` although nothing they ship did.

    Raises:
        ValueError: If a revision could be read as a git option.
    """
    if not (REVISION.fullmatch(base) and REVISION.fullmatch(head)):
        msg = "A revision must be a plain commit or ref name."
        raise ValueError(msg)
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


def unbumped_changes(base: str, head: str = "HEAD") -> list[str]:
    """Plugins whose shipped files or metadata changed in `base..head` although their version did not.

    Without a bump the change never becomes a release, so users of the published plugin never get it.

    Raises:
        ValueError: If a revision could be read as a git option.
    """
    if not (REVISION.fullmatch(base) and REVISION.fullmatch(head)):
        msg = "A revision must be a plain commit or ref name."
        raise ValueError(msg)
    changed: dict[str, list[str]] = {}
    for path in _git("diff", "--name-only", f"{base}...{head}").splitlines():
        parts = PurePosixPath(path).parts
        if len(parts) > 2 and parts[0] == PLUGINS:  # noqa: PLR2004 - plugins/<name>/<path>
            changed.setdefault(parts[1], []).append(path)
    stale = []
    for plugin, paths in sorted(changed.items()):
        before, after = _pyproject(base, plugin), _pyproject(head, plugin)
        if not before or not after or _version(before) != _version(after):
            continue  # a new or removed plugin, or a bump: `unjustified_bumps` judges those
        if _shipped_metadata(before) != _shipped_metadata(after) or any(_shipped(path, plugin) for path in paths):
            stale.append(plugin)
    return stale


def missing_changelogs(base: str, head: str = "HEAD") -> list[str]:
    """Plugins bumped in `base..head` whose changelog does not open with a non-empty `## <new version>` section.

    The section becomes the plugin's release notes and the app's notes, so a bump without one would drop the change
    from what users read.

    Raises:
        ValueError: If a revision could be read as a git option.
    """
    if not (REVISION.fullmatch(base) and REVISION.fullmatch(head)):
        msg = "A revision must be a plain commit or ref name."
        raise ValueError(msg)
    plugins = set()
    for path in _git("diff", "--name-only", f"{base}...{head}").splitlines():
        parts = PurePosixPath(path).parts
        if len(parts) > 2 and parts[0] == PLUGINS:  # noqa: PLR2004 - plugins/<name>/<path>
            plugins.add(parts[1])
    missing = []
    for plugin in sorted(plugins):
        after = _pyproject(head, plugin)
        version = _version(after)
        if not after or version == _version(_pyproject(base, plugin)):
            continue
        sections = changelog_sections(_changelog(head, plugin))
        while sections and not sections[0][1] and not sections[0][0][:1].isdigit():
            sections = sections[1:]  # an empty placeholder such as `## Unreleased` holds nothing to drop
        if not sections or sections[0][0] != version or not sections[0][1]:
            missing.append(plugin)
    return missing


def unreleased(root: Path, tags: set[str]) -> list[str]:
    """Plugins in `root` whose current version has no release tag yet."""
    names = []
    for path in sorted((root / PLUGINS).glob("*/pyproject.toml")):
        project = tomllib.loads(path.read_text(encoding="utf-8"))["project"]
        if f"{project['name']}/v{project['version']}" not in tags:
            names.append(project["name"])
    return names


def main(arguments: list[str]) -> int:
    """`check <base>` refuses a bump that ships nothing or lacks its changelog section, or a shipped change without a
    bump; `unreleased` lists the rest."""
    if arguments[:1] == ["check"] and len(arguments) == 2:  # noqa: PLR2004
        bumps = unjustified_bumps(arguments[1])
        stale = unbumped_changes(arguments[1])
        undocumented = missing_changelogs(arguments[1])
        for plugin in undocumented:
            print(
                f"{plugin}: the version changed but CHANGELOG.md does not open with a non-empty `## <new version>` "
                "section; add it, because it becomes the release notes of the plugin and of the app.",
                file=sys.stderr,
            )
        for plugin in stale:
            print(
                f"{plugin}: what it ships changed but its version did not; bump `project.version` and add a changelog "
                "line, or the change never reaches a release.",
                file=sys.stderr,
            )
        for plugin in bumps:
            print(
                f"{plugin}: the version changed but nothing it ships did; revert the bump, because every new version "
                "must become a release.",
                file=sys.stderr,
            )
        return 1 if bumps or stale or undocumented else 0
    if arguments == ["unreleased"]:
        print("\n".join(unreleased(Path(), set(_git("tag", "--list").splitlines()))))
        return 0
    print(main.__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
