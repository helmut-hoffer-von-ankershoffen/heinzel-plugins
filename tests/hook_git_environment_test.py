"""No test's git reaches the repository a git hook runs for (bead heinzel-management-70clb).

A pre-push hook exports GIT_DIR and GIT_INDEX_FILE for the pushing worktree. capture_test.py and
gallery_index_guard_test.py inherited them and staged 908 rendered template files in that worktree's index.
The decoy repository below plays that worktree.
"""

import importlib.util
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.unit


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _decoy(tmp_path: Path, fixture_git) -> tuple[Path, str, bytes]:
    """The pushing worktree stand-in: one commit, an index; returns its path, HEAD and index bytes."""
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    fixture_git(decoy, "init", "-q", "-b", "main")
    (decoy / "AGENTS.md").write_text("the real file\n" * 50)
    fixture_git(decoy, "add", "AGENTS.md")
    fixture_git(decoy, "commit", "-q", "-m", "decoy")
    head = fixture_git(decoy, "rev-parse", "HEAD").stdout.strip()
    return decoy, head, (decoy / ".git" / "index").read_bytes()


def _point_at(decoy: Path) -> dict[str, str]:
    return {
        "GIT_DIR": str(decoy / ".git"),
        "GIT_INDEX_FILE": str(decoy / ".git" / "index"),
        "GIT_WORK_TREE": str(decoy),
        "GIT_PREFIX": "",
    }


def _assert_untouched(fixture_git, decoy: Path, head: str, index: bytes) -> None:
    assert fixture_git(decoy, "rev-parse", "HEAD").stdout.strip() == head
    assert (decoy / ".git" / "index").read_bytes() == index
    assert fixture_git(decoy, "status", "--porcelain").stdout == ""


def test_fixture_git_commits_in_its_repository_while_a_hook_points_git_elsewhere(tmp_path, monkeypatch, fixture_git):
    decoy, head, index = _decoy(tmp_path, fixture_git)
    for key, value in _point_at(decoy).items():
        monkeypatch.setenv(key, value)
    fixture = tmp_path / "fixture"
    fixture.mkdir()

    fixture_git(fixture, "init", "-q", "-b", "main")
    (fixture / "AGENTS.md").write_text("three\nline\nfile\n")
    fixture_git(fixture, "add", "AGENTS.md")
    fixture_git(fixture, "commit", "-q", "-m", "fixture")

    _assert_untouched(fixture_git, decoy, head, index)
    assert fixture_git(fixture, "show", "HEAD:AGENTS.md").stdout == "three\nline\nfile\n"


def test_the_session_strip_also_drops_the_outer_hooks_prek_context(monkeypatch):
    conftest = _load("tests_conftest_copy", ROOT / "tests" / "conftest.py")
    for key in ("GIT_DIR", "PRE_COMMIT", "PRE_COMMIT_FROM_REF", "PRE_COMMIT_TO_REF", "PREK_HOOK_STAGE"):
        monkeypatch.setenv(key, "from-the-outer-push")
    monkeypatch.setenv("CONFIDENTIAL_TERMS", "kept")

    conftest.strip_git_environment()

    assert [key for key in os.environ if key.startswith(conftest.HOOK_PREFIXES)] == []
    assert os.environ["CONFIDENTIAL_TERMS"] == "kept"


def test_a_suite_started_by_a_hook_cannot_reach_the_hooks_repository(tmp_path, fixture_git):
    """End to end: pytest launched with a hook's GIT_*, a test running plain git (no helper) in its fixture."""
    decoy, head, index = _decoy(tmp_path, fixture_git)
    suite = tmp_path / "suite"
    suite.mkdir()
    (suite / "conftest.py").write_bytes((ROOT / "tests" / "conftest.py").read_bytes())
    (suite / "probe_test.py").write_text(
        textwrap.dedent(
            """
            import os, subprocess

            def test_plain_git_in_a_fixture(tmp_path):
                run = lambda *args: subprocess.run(
                    ["git", "-c", "core.hooksPath=/dev/null", "-c", "user.name=T", "-c", "user.email=t@example.test",
                     *args], cwd=tmp_path, check=True, capture_output=True)
                run("init", "-q")
                (tmp_path / "AGENTS.md").write_text("three\\nline\\nfile\\n")
                run("add", "AGENTS.md")
                run("commit", "-q", "-m", "probe")
                assert [key for key in os.environ if key.startswith(("GIT_", "PRE_COMMIT", "PREK_"))] == []
            """
        )
    )
    environment = {**os.environ, **_point_at(decoy), "PRE_COMMIT_FROM_REF": "a" * 40, "PREK_HOOK_STAGE": "pre-push"}
    environment.pop("PYTEST_ADDOPTS", None)
    result = subprocess.run(  # noqa: S603 - this interpreter, fixed arguments
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir", str(suite), str(suite)],
        cwd=suite,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    _assert_untouched(fixture_git, decoy, head, index)
    assert result.returncode == 0, result.stdout + result.stderr


def test_plugin_checks_and_the_tooling_hook_launch_children_without_git_variables(monkeypatch):
    """The hook runners: hz-plugin's `run` (owning plugin tests) and focused_hook.py's make check-fast."""
    from heinzel_plugin_tools import cli

    for key in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY", "GIT_PREFIX"):
        monkeypatch.setenv(key, "the-pushing-worktree")
    seen = []
    monkeypatch.setattr(
        cli.subprocess, "run", lambda command, **kw: seen.append(kw["env"]) or subprocess.CompletedProcess(command, 0)
    )
    cli.run(["pytest"])
    cli.run(["pytest"], env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})

    hook = _load("focused_hook_env", ROOT / "scripts" / "focused_hook.py")
    monkeypatch.delenv("HZ_TRUSTED_FOCUSED_PUSH", raising=False)
    monkeypatch.setattr(hook.sys, "argv", ["focused_hook.py", "tooling"])
    monkeypatch.setattr(
        hook.subprocess, "run", lambda command, **kw: seen.append(kw["env"]) or subprocess.CompletedProcess(command, 0)
    )
    with pytest.raises(SystemExit):
        hook.main()

    assert len(seen) == 3
    assert all(not [key for key in env if key.startswith("GIT_")] for env in seen)
    assert seen[1]["PYTHONDONTWRITEBYTECODE"] == "1"
    assert os.environ["GIT_DIR"] == "the-pushing-worktree"  # the runner's own git calls keep the hook's view


def test_the_tooling_test_step_unsets_every_inherited_git_variable():
    environment = {**os.environ, "GIT_DIR": "/the-pushing-worktree/.git", "GIT_INDEX_FILE": "/the-pushing/index"}
    plan = subprocess.run(
        ["make", "-n", "--no-print-directory", "tooling-check"],  # noqa: S607 - dry run of the repo's Makefile
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    ).stdout
    [pytest_line] = [line for line in plan.splitlines() if "pytest tests" in line]
    assert "-u GIT_DIR" in pytest_line
    assert "-u GIT_INDEX_FILE" in pytest_line
