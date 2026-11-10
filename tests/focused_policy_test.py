"""Evidence for the inert focused-policy planner; not a hook bypass."""

import os
import subprocess

import pytest

from heinzel_plugin_tools import focused_policy as policy


def git(repo, *args):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    # All arguments are fixed by this disposable local Git fixture.
    return subprocess.check_output(["git", *args], cwd=repo, env=env, text=True).strip()  # noqa: S603, S607


def commit(repo, name):
    git(repo, "add", ".")
    git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", name)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def history(tmp_path, monkeypatch):
    git(tmp_path, "init", "-q")
    (tmp_path / "test.py").write_text("contract\n")
    (tmp_path / "source").write_text("base\n")
    anchor = commit(tmp_path, "anchor")
    (tmp_path / "old").write_text("old\n")
    old = commit(tmp_path, "old")
    (tmp_path / "source").write_text("feature\n")
    candidate = commit(tmp_path, "candidate")
    git(tmp_path, "checkout", "-qb", "policy", anchor)
    (tmp_path / "policy").write_text("trusted\n")
    trusted = commit(tmp_path, "policy")
    git(tmp_path, "checkout", "-q", "--detach", candidate)
    git(
        tmp_path,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "merge",
        "-q",
        "--no-ff",
        trusted,
        "-m",
        "merge",
    )
    head = git(tmp_path, "rev-parse", "HEAD")
    monkeypatch.setattr(policy, "ANCHOR", anchor)
    monkeypatch.setattr(policy, "PLANS", {old: (candidate, ("test.py",))})
    monkeypatch.setattr(policy, "POLICY_PATHS", frozenset({"policy"}))
    return tmp_path, old, head, trusted


def test_exact_reviewed_history_selects_fixed_tests(history):
    repo, old, head, trusted = history
    assert isinstance(policy.plan(repo, old, head, trusted), policy.CheckPlan)


def test_unknown_base_and_untrusted_policy_are_rejected(history):
    repo, old, head, trusted = history
    with pytest.raises(ValueError):
        policy.plan(repo, "0" * 40, head, trusted)
    with pytest.raises(ValueError):
        policy.plan(repo, old, head, old)


def test_missing_or_modified_contract_is_rejected(history):
    repo, old, _, trusted = history
    (repo / "test.py").unlink()
    new = commit(repo, "remove contract")
    with pytest.raises(ValueError):
        policy.plan(repo, old, new, trusted)


def test_modified_policy_and_unknown_changes_are_rejected(history):
    repo, old, _, trusted = history
    (repo / "policy").write_text("forged\n")
    new = commit(repo, "forge")
    with pytest.raises(ValueError):
        policy.plan(repo, old, new, trusted)
    (repo / "policy").write_text("trusted\n")
    (repo / "unknown").write_text("unknown\n")
    new = commit(repo, "unknown")
    with pytest.raises(ValueError):
        policy.plan(repo, old, new, trusted)


def test_dirty_checkout_fails_closed(history):
    repo, old, head, trusted = history
    (repo / "source").write_text("dirty\n")
    with pytest.raises(ValueError):
        policy.plan(repo, old, head, trusted)
