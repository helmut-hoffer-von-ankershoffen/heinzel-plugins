"""Release notes from the changelogs, so no plugin release and no app release silently drops a change.

Usage:
    release_notes.py plugin <dist> [--version V]
        print the `## <version>` section of plugins/<dist>/CHANGELOG.md (default: the plugin's current version);
        exit 1 when it is missing or empty.
    release_notes.py app <version> [--profile dist/standard.json] [--previous <standard.json>]
        compare this app's profile with the previous final app's (fetched from GH_REPO unless given; none found:
        every plugin is new) and print the core release link, "old -> new" with the changelog sections of every
        changed plugin and one line per unchanged plugin; exit 1 when a changed plugin has no section.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

from packaging.version import InvalidVersion, Version

from heinzel_plugin_tools.publishing import api, fetch_bytes

ROOT = Path(__file__).resolve().parents[1]
CORE_REPOSITORY = "helmut-hoffer-von-ankershoffen/heinzel"
CORE = "heinzel"
BODY_LIMIT = 120_000  # GitHub refuses release bodies over 125,000 characters
PROFILE_LIMIT = 1024 * 1024
RELEASE_PAGES = 10

_spec = importlib.util.spec_from_file_location("plugin_versions", Path(__file__).with_name("plugin_versions.py"))
_versions = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_versions)
changelog_section = _versions.changelog_section
changelog_sections = _versions.changelog_sections


class NotesError(ValueError):
    """A release would lose a change: a section is missing or the inputs are not what they claim."""


def _distribution(name: str) -> str:
    return name if name.startswith(f"{CORE}-") else f"{CORE}-{name}"


def _changelog(root: Path, dist: str) -> str:
    path = root / "plugins" / dist / "CHANGELOG.md"
    if not path.is_file():
        raise NotesError(f"{dist}: plugins/{dist}/CHANGELOG.md is missing")
    return path.read_text(encoding="utf-8")


def plugin_notes(root: Path, name: str, version: str | None = None) -> str:
    dist = _distribution(name)
    if version is None:
        project = tomllib.loads((root / "plugins" / dist / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        version = str(project["version"])
    section = changelog_section(_changelog(root, dist), version)
    if not section:
        raise NotesError(f"{dist}: CHANGELOG.md has no non-empty `## {version}` section")
    return section + "\n"


def _plugins(profile: dict) -> dict[str, str]:
    artifacts = profile.get("artifacts")
    if not isinstance(artifacts, list):
        raise NotesError("The app profile lists no artifacts")
    plugins = {}
    for artifact in artifacts:
        name, version = artifact.get("name"), artifact.get("version")
        if not isinstance(name, str) or not isinstance(version, str) or name in plugins:
            raise NotesError("The app profile has an invalid or duplicate artifact")
        if name != CORE:
            plugins[name] = version
    return plugins


def _sections(root: Path, dist: str, old: str | None, new: str) -> list[tuple[str, str]]:
    """The changelog sections after `old` up to and including `new`, newest first; `new` must be there."""
    text = _changelog(root, dist)
    if not changelog_section(text, new):
        raise NotesError(f"{dist}: CHANGELOG.md has no non-empty `## {new}` section")
    upper = Version(new)
    lower = Version(old) if old else None
    chosen = []
    for heading, body in changelog_sections(text):
        try:
            version = Version(heading)
        except InvalidVersion:
            continue
        if body and version <= upper and (lower is None or version > lower):
            chosen.append((heading, body))
    return chosen


def core_link(version: str) -> str:
    tag = f"edge-v{version}" if Version(version).is_devrelease else f"v{version}"
    return f"https://github.com/{CORE_REPOSITORY}/releases/tag/{tag}"


def app_notes(
    root: Path, version: str, profile: dict, previous: dict | None, previous_tag: str | None = None, *, compact=False
) -> str:
    """Every plugin of the app appears: changed ones with their sections, unchanged ones on one line each."""
    current, before = _plugins(profile), _plugins(previous) if previous else {}
    lines = [f"Core: [heinzel {version}]({core_link(version)})", ""]
    lines.append(
        f"Compared with the previous final app {previous_tag}."
        if previous and previous_tag
        else "No previous final app: every plugin is listed as new."
    )
    changed = [name for name in sorted(current) if before.get(name) != current[name]]
    unchanged = [name for name in sorted(current) if before.get(name) == current[name]]
    removed = sorted(set(before) - set(current))
    if changed:
        lines += ["", "## Changed plugins"]
    for name in changed:
        lines += ["", f"### {name} {before.get(name, 'new')} -> {current[name]}"]
        sections = _sections(root, name, before.get(name), current[name])
        if compact:
            lines += ["", f"See plugins/{name}/CHANGELOG.md, sections {', '.join(h for h, _ in sections)}."]
            continue
        for heading, body in sections:
            lines += ["", f"#### {heading}", "", body]
    if removed:
        lines += ["", "## Removed plugins", ""] + [f"- {name} {before[name]} -> removed" for name in removed]
    if unchanged:
        lines += ["", "## Unchanged plugins", ""] + [f"- {name} {current[name]}" for name in unchanged]
    body = "\n".join(lines) + "\n"
    if len(body) > BODY_LIMIT:
        if compact:
            raise NotesError("The app release notes exceed GitHub's limit even without changelog text")
        print(
            f"The app release notes have {len(body)} characters, over {BODY_LIMIT}; "
            "listing every plugin without its changelog text.",
            file=sys.stderr,
        )
        return app_notes(root, version, profile, previous, previous_tag, compact=True)
    return body


def previous_final_app(repository: str, version: str) -> tuple[str | None, dict | None]:
    """The newest final (published, not prerelease) app release older than `version`, with its profile."""
    target, best = Version(version), None
    for page in range(1, RELEASE_PAGES + 1):
        releases = api(f"repos/{repository}/releases?per_page=100&page={page}") or []
        for release in releases:
            tag = release.get("tag_name", "")
            if not tag.startswith("app-v") or release.get("draft") or release.get("prerelease"):
                continue
            try:
                candidate = Version(tag.removeprefix("app-v"))
            except InvalidVersion:
                continue
            if candidate.is_prerelease or candidate.is_devrelease or candidate >= target:
                continue
            if best is None or candidate > best[0]:
                best = (candidate, tag, release)
        if len(releases) < 100:  # noqa: PLR2004 - the last page
            break
    if best is None:
        return None, None
    _, tag, release = best
    asset = next((item for item in release.get("assets", []) if item.get("name") == "standard.json"), None)
    if asset is None:
        raise NotesError(f"The previous final app {tag} has no standard.json")
    _, content = fetch_bytes(
        f"https://github.com/{repository}/releases/download/{tag}/standard.json",
        hosts={"github.com"},
        timeout=30,
        limit=PROFILE_LIMIT,
    )
    if len(content) > PROFILE_LIMIT:
        raise NotesError(f"The previous final app {tag} profile exceeds its size limit")
    digest = asset.get("digest")
    if digest and digest != "sha256:" + hashlib.sha256(content).hexdigest():
        raise NotesError(f"The previous final app {tag} profile differs from its recorded digest")
    return tag, json.loads(content)


def main(arguments: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    plugin = commands.add_parser("plugin")
    plugin.add_argument("dist")
    plugin.add_argument("--version")
    app = commands.add_parser("app")
    app.add_argument("version")
    app.add_argument("--profile", type=Path, default=Path("dist/standard.json"))
    app.add_argument("--previous", type=Path)
    args = parser.parse_args(arguments)
    try:
        if args.command == "plugin":
            sys.stdout.write(plugin_notes(root, args.dist, args.version))
            return 0
        profile = json.loads(args.profile.read_text(encoding="utf-8"))
        if profile.get("core_version") != args.version:
            raise NotesError(f"The app profile is for {profile.get('core_version')}, not {args.version}")
        if args.previous:
            previous_tag, previous = args.previous.name, json.loads(args.previous.read_text(encoding="utf-8"))
        else:
            previous_tag, previous = previous_final_app(os.environ["GH_REPO"], args.version)
        sys.stdout.write(app_notes(root, args.version, profile, previous, previous_tag))
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:  # GitHub, git, files, JSON
        print(f"Release notes stopped: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
