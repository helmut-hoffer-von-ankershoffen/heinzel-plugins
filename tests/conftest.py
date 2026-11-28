"""Test-only configuration for the shared plugin toolkit."""

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "Fixture",
    "GIT_AUTHOR_EMAIL": "fixture@example.test",
    "GIT_COMMITTER_NAME": "Fixture",
    "GIT_COMMITTER_EMAIL": "fixture@example.test",
}


HOOK_PREFIXES = ("GIT_", "PRE_COMMIT", "PREK_")


def strip_git_environment() -> None:
    """Drop what a git hook exported: GIT_* (GIT_DIR, GIT_INDEX_FILE, ...) and prek's PRE_COMMIT*/PREK_* context.

    A test that runs git in a fixture repository would otherwise write to the committing or pushing worktree's index
    (it once staged 908 rendered template files there), and the fixture's own hooks would believe they run inside
    the outer push (PRE_COMMIT_FROM_REF) and refuse.
    """
    for key in [key for key in os.environ if key.startswith(HOOK_PREFIXES)]:
        del os.environ[key]


def pytest_configure(config: pytest.Config) -> None:
    """Already during collection no child git can reach the repository a hook runs for."""
    del config
    strip_git_environment()


@pytest.fixture(autouse=True, scope="session")
def _no_hook_git_environment() -> None:
    """For the whole session no test or child git inherits the GIT_* of a hook that started pytest."""
    strip_git_environment()


def git_environment() -> dict[str, str]:
    """The environment for a fixture git: no inherited GIT_*, no global or system configuration, a fixed identity."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith(HOOK_PREFIXES)}
    environment.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", **GIT_IDENTITY)
    return environment


def run_fixture_git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run `git ARGS` in the fixture repository CWD without hooks and with the isolated environment."""
    return subprocess.run(  # noqa: S603 - fixed git argument lists from tests
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", *args],  # noqa: S607
        cwd=cwd,
        env=git_environment(),
        check=check,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.fixture
def fixture_git() -> Callable[..., subprocess.CompletedProcess[str]]:
    """The shared way for a test to run git in its own repository (see `run_fixture_git`)."""
    return run_fixture_git


@pytest.fixture
def fictional_capture_terms(monkeypatch):
    """Give opted-in gallery fixtures a synthetic term without disabling the CI guard."""
    monkeypatch.setenv("CONFIDENTIAL_TERMS", "fictional-capture-canary-8329")
