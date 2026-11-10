"""Focused opt-in fails closed and ordinary hooks retain their original commands."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

scripts = Path(__file__).parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("focused_hook", scripts / "focused_hook.py")
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


def test_normal_owner_check_is_preserved(monkeypatch):
    seen = []
    monkeypatch.delenv("HZ_TRUSTED_FOCUSED_PUSH", raising=False)
    monkeypatch.setattr(hook.sys, "argv", ["focused_hook.py", "owners"])
    monkeypatch.setattr(
        hook.subprocess, "run", lambda command, check: seen.append(command) or SimpleNamespace(returncode=0)
    )
    with pytest.raises(SystemExit) as result:
        hook.main()
    assert result.value.code == 0
    assert seen == [["uv", "run", "--frozen", "--group", "tooling", "hz-plugin", "check-changed", "--git-hook"]]


def test_focused_mode_missing_ref_refuses_without_running_anything(monkeypatch):
    monkeypatch.setenv("HZ_TRUSTED_FOCUSED_PUSH", "1")
    monkeypatch.delenv("PRE_COMMIT_FROM_REF", raising=False)
    monkeypatch.delenv("PRE_COMMIT_TO_REF", raising=False)
    monkeypatch.setattr(hook.sys, "argv", ["focused_hook.py", "tooling"])
    monkeypatch.setattr(hook.subprocess, "run", lambda *args, **kwargs: pytest.fail("must not run"))
    with pytest.raises(SystemExit, match="exact hook-supplied revisions"):
        hook.main()
