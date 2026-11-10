"""The standalone companion guard must fail closed on malformed transactions."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "focused_push_guard", Path(__file__).parents[1] / "scripts/focused_push_guard.py"
)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def test_only_one_existing_branch_transaction_is_accepted():
    old, new = "a" * 40, "b" * 40
    line = f"refs/heads/work {new} refs/heads/work {old}\n"
    assert guard.validate_transaction(line.encode()) == ("refs/heads/work", new, "refs/heads/work", old)
    for value in ("", line + line, line.replace(old, "0" * 40), "malformed\n"):
        with pytest.raises(ValueError):
            guard.validate_transaction(value.encode())
    with pytest.raises(ValueError):
        guard.validate_transaction(b"\xff")


def test_ordinary_nonfocused_push_is_not_vetoed(monkeypatch):
    monkeypatch.delenv("HZ_TRUSTED_FOCUSED_PUSH", raising=False)
    assert guard.main() == 0


@pytest.mark.parametrize("name", ["SKIP", "PREK_SKIP"])
def test_focused_push_refuses_skip_overrides(name, monkeypatch, capsys):
    monkeypatch.setenv("HZ_TRUSTED_FOCUSED_PUSH", "1")
    monkeypatch.setenv(name, "check-fast")
    assert guard.main() == 1
    assert "skip overrides are forbidden" in capsys.readouterr().err
