"""The standalone companion guard must fail closed on malformed transactions."""

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "focused_push_guard", Path(__file__).parents[1] / "scripts/focused_push_guard.py"
)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def test_only_one_existing_branch_transaction_is_accepted(tmp_path):
    old, new = "a" * 40, "b" * 40
    line = f"refs/heads/work {new} refs/heads/work {old}\n"
    assert guard.validate_transaction(line.encode(), repo=tmp_path, git_env={}) == (
        "refs/heads/work",
        new,
        "refs/heads/work",
        old,
    )
    for value in ("", line + line, line.replace(old, "0" * 40), "malformed\n"):
        with pytest.raises(ValueError):
            guard.validate_transaction(value.encode(), repo=tmp_path, git_env={})
    with pytest.raises(ValueError):
        guard.validate_transaction(b"\xff", repo=tmp_path, git_env={})


def test_ordinary_nonfocused_push_is_not_vetoed(monkeypatch):
    monkeypatch.delenv("HZ_TRUSTED_FOCUSED_PUSH", raising=False)
    assert guard.main() == 0


@pytest.mark.parametrize("name", ["SKIP", "PREK_SKIP"])
def test_focused_push_refuses_skip_overrides(name, monkeypatch, capsys):
    monkeypatch.setenv("HZ_TRUSTED_FOCUSED_PUSH", "1")
    monkeypatch.setenv(name, "check-fast")
    assert guard.main() == 1
    assert "skip overrides are forbidden" in capsys.readouterr().err


def test_literal_source_requires_its_clean_checked_out_destination_branch(tmp_path):
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
    }

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, env=env, text=True).strip()  # noqa: S603, S607

    git("init", "-q", "--initial-branch=work")
    git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--allow-empty", "-qm", "one")
    old = git("rev-parse", "HEAD")
    git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--allow-empty", "-qm", "two")
    new = git("rev-parse", "HEAD")
    destination = "refs/heads/work"

    def validate(source=new, after=new, remote_ref=destination):
        line = f"{source} {after} {remote_ref} {old}\n"
        return guard.validate_transaction(line.encode(), repo=tmp_path, git_env=env)

    assert validate() == (new, new, destination, old)
    for args in [(old, new), (old, old), (new, new, "refs/heads/other"), ("HEAD", new), (new[:10], new)]:
        with pytest.raises(ValueError):
            validate(*args)
    (tmp_path / "extra").write_text("dirty")
    with pytest.raises(ValueError, match="clean checked-out"):
        validate()
    (tmp_path / "extra").unlink()
    git("switch", "--detach", "-q", new)
    with pytest.raises(ValueError, match="clean checked-out"):
        validate()
