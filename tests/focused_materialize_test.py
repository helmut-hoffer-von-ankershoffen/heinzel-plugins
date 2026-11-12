"""An isolated checkout must ignore caller Git variables and hidden worktree edits."""

import importlib.util
import os
import subprocess
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "focused_materialize", Path(__file__).parents[1] / "scripts/focused_materialize.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def git(repo, *args):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    return subprocess.check_output(["git", *args], cwd=repo, env=env, text=True).strip()  # noqa: S603, S607


def test_snapshot_ignores_skip_worktree_and_caller_git_dir(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "source.py").write_text("reviewed\n")
    git(repo, "add", "source.py")
    git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "base")
    revision = git(repo, "rev-parse", "HEAD")
    git(repo, "update-index", "--skip-worktree", "source.py")
    (repo / "source.py").write_text("unreviewed\n")
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "wrong"))
    with module.materialized(repo, revision) as tree:
        assert (tree / "source.py").read_text() == "reviewed\n"
        assert git(tree, "rev-parse", "HEAD") == revision
    assert (repo / "source.py").read_text() == "unreviewed\n"
