"""A dispatch at current main still enforces file, title and branch policies without an empty commit check."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

spec = importlib.util.spec_from_file_location("policy", Path(__file__).parents[1] / "scripts/check_policy.py")
assert spec and spec.loader
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


@pytest.mark.parametrize("commits", ["", "a" * 40 + "\n"])
@pytest.mark.parametrize("required", ["true", "false"])
def test_empty_and_nonempty_ranges_preserve_all_applicable_policies(monkeypatch, commits, required):
    calls = []
    monkeypatch.delenv("CHECK_BASE", raising=False)
    monkeypatch.setenv("CHECK_TITLE", "refactor(plugin): isolate delivery")
    monkeypatch.setenv("CHECK_BRANCH", "refactor/plugin-delivery")
    monkeypatch.setenv("CONFIDENTIALITY_REQUIRED", required)
    monkeypatch.setattr(policy, "run", lambda *args: calls.append(args))

    def revision_query(command, **kwargs):
        assert command == ["git", "rev-list", "origin/main..HEAD"]
        assert kwargs["check"] is True
        return subprocess.CompletedProcess(command, 0, stdout=commits)

    monkeypatch.setattr(policy.subprocess, "run", revision_query)
    policy.main()
    assert any(args[-1] == "--require" for args in calls) is (required == "true")
    assert any(len(args) == 1 and args[0].endswith("check_confidentiality.py") for args in calls) is (
        required == "false"
    )
    assert any(args[-2:] == ("--messages", "origin/main..HEAD") for args in calls)
    assert any(args[-2:] == ("--text", "refactor/plugin-delivery") for args in calls)
    assert any(args[-2:] == ("--message", "refactor(plugin): isolate delivery") for args in calls)
    assert any("--rev-range" in args for args in calls) is bool(commits)
