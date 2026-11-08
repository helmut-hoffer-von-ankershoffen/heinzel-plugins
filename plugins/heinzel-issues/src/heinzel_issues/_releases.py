"""Which release shipped a finished item: pull request numbers, their merge commits, the first tag containing them.

Whoever works on an item writes the pull request into the tracker (`Fixed in #562`, `gh-562`, a pull request link,
`plugins #38`). Each named repository is a local git clone on this computer; Issues reads it and never fetches,
pushes or changes it. A merged pull request is found by the `(#562)` its squash commit's subject ends with, and the
release is the oldest tag matching the repository's pattern that contains that commit.
"""

import os
import re
import subprocess
from collections.abc import Callable, Sequence
from datetime import date as Day
from datetime import datetime
from pathlib import Path
from time import monotonic

from pydantic import BaseModel, ConfigDict, Field

TIMEOUT = 15
"""Seconds one git call may take."""
CACHE_SECONDS = 300.0
"""How long a lookup is kept: tags appear rarely, and a list must stay fast."""
_VERSION = re.compile(r"(\d+\.\d+\.\d+[0-9A-Za-z.+-]*)$")
_URL = re.compile(r"github\.com/[\w.-]+/(?P<repo>[\w.-]+)/pull/(?P<number>\d+)")
_GH = re.compile(r"\bgh-(?P<number>\d+)\b")
_HASH = re.compile(r"(?:(?P<repo>[A-Za-z][\w-]*)[ \t]*)?#(?P<number>\d+)\b")


class ReleaseSource(BaseModel):
    """A local clone whose tags are releases."""

    model_config = ConfigDict(extra="forbid")

    path: Path = Field(title="Clone", description="A git clone on this computer; it is read, never fetched.")
    names: list[str] = Field(
        default_factory=list[str],
        title="Names",
        description="How notes name this repository before a number, e.g. plugins for `plugins #38`.",
    )
    ref: str = Field(default="origin/main", title="Branch", description="Where merged pull requests are.")
    tags: str = Field(default="v*", title="Release tags", description="The tag pattern of releases, e.g. v*.")


class Release(BaseModel):
    """A release that contains the work."""

    model_config = ConfigDict(frozen=True)

    version: str = Field(description="The version, e.g. 0.9.27.")
    date: Day = Field(description="The day it was released.")


class PullRequest(BaseModel):
    """A pull request named in the tracker, and where it stands."""

    model_config = ConfigDict(frozen=True)

    repository: str = Field(description="The repository's first name, or `default`.")
    number: int = Field(description="The pull request number.")
    release: Release | None = Field(default=None, description="The first release that has it; none until then.")


def references(text: str, sources: Sequence[ReleaseSource]) -> list[tuple[int, int]]:
    """(source index, pull request number) pairs named in `text`, in order, without repeats.

    A bare `#562` or `gh-562` means the first source; `plugins #38` or a pull request link means the source with that
    name (or the repository's last path part). Names of no source are ignored, so prose like `step #2` is harmless.
    """
    if not sources:
        return []
    known = {name.lower(): index for index, source in enumerate(sources) for name in [*source.names, source.path.name]}
    found: list[tuple[int, int]] = []
    for match in _URL.finditer(text):
        if (index := known.get(match["repo"].lower())) is not None:
            found.append((index, int(match["number"])))
    text = _URL.sub(" ", text)
    found += [(0, int(match["number"])) for match in _GH.finditer(text)]
    for match in _HASH.finditer(text):
        name = (match["repo"] or "").lower()
        if name in known:
            index = known[name]
        elif not name or name in _PROSE:
            index = 0
        else:
            continue  # `step #2`: a number of something else
        found.append((index, int(match["number"])))
    return list(dict.fromkeys(found))


_PROSE = frozenset({"in", "by", "via", "see", "pr", "fixed", "merged", "and", "with", "shipped", "done"})
"""Words that may stand before a bare pull request number in a note: `Fixed in #562`, `PR #562`."""


Git = Callable[[Path, list[str]], str | None]
_REPOSITORY_VARIABLES = frozenset({"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"})
"""Set by a git hook around Heinzel; they would point the lookup at the wrong repository."""


def run_git(path: Path, args: list[str]) -> str | None:
    """Output of a read-only git command in `path`; None if git fails or is missing."""
    try:
        done = subprocess.run(  # noqa: S603 - fixed program and arguments, no shell
            ["git", "-C", str(path.expanduser()), *args],  # noqa: S607 - git from PATH on purpose
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
            env={key: value for key, value in os.environ.items() if key not in _REPOSITORY_VARIABLES},
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


class ReleaseResolver:
    """Finds the release of pull requests in local clones, caching each answer for a few minutes."""

    def __init__(self, sources: Sequence[ReleaseSource], git: Git = run_git) -> None:
        """Nothing is read until a release is asked for."""
        self.sources = list(sources)
        self._git = git
        self._cache: dict[tuple[int, int], tuple[float, Release | None]] = {}
        self.clock: Callable[[], float] = monotonic

    def pull_requests(self, text: str) -> list[PullRequest]:
        """The pull requests named in `text`, each with its release if it shipped."""
        return [
            PullRequest(
                repository=(self.sources[index].names or ["default"])[0],
                number=number,
                release=self.find(index, number),
            )
            for index, number in references(text, self.sources)
        ]

    def release(self, text: str) -> Release | None:
        """The release that completed the work named in `text`: the latest one any of its pull requests needs.

        None while no pull request is named, or one of them is not released yet.
        """
        found = self.pull_requests(text)
        if not found or any(pr.release is None for pr in found):
            return None
        return max((pr.release for pr in found if pr.release is not None), key=lambda r: (r.date, r.version))

    def find(self, index: int, number: int) -> Release | None:
        """The first release of one pull request, from cache while fresh."""
        now = self.clock()
        cached = self._cache.get((index, number))
        if cached is not None and now - cached[0] < CACHE_SECONDS:
            return cached[1]
        source = self.sources[index]
        release = self._lookup(source, number)
        self._cache[index, number] = (now, release)
        return release

    def _lookup(self, source: ReleaseSource, number: int) -> Release | None:
        commit = self._git(
            source.path, ["log", "-1", "--format=%H", "--fixed-strings", f"--grep=(#{number})", source.ref, "--"]
        )
        if not commit or not commit.strip():
            return None
        tags = self._git(
            source.path,
            [
                "tag",
                "--contains",
                commit.strip(),
                "--list",
                source.tags,
                "--sort=creatordate",
                "--format=%(refname:short) %(creatordate:iso-strict)",
            ],
        )
        for line in (tags or "").splitlines():
            name, _, when = line.partition(" ")
            if (version := _VERSION.search(name)) is None:
                continue
            try:
                day = datetime.fromisoformat(when.strip()).date()
            except ValueError:
                continue
            return Release(version=version[1], date=day)
        return None


def released_text(release: Release) -> str:
    """`Released in 0.9.27 on 7 Nov 2026`."""
    return f"Released in {release.version} on {release.date.day} {release.date:%b %Y}"
