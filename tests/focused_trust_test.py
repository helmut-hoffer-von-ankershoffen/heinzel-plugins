"""A pin must describe the active code and an executable transaction guard."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

scripts = Path(__file__).parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("focused_trust_tested", scripts / "focused_trust.py")
trust = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trust)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def pins(tmp_path):
    repo, hooks = tmp_path / "repo", tmp_path / "hooks"
    (repo / "scripts").mkdir(parents=True)
    hooks.mkdir()
    paths = {}
    for name in ("guard", "shim", "prek", "policy", "dispatcher", "hook", "materializer"):
        path = hooks / {"guard": "pre-push.legacy", "shim": "pre-push"}.get(name, name + ".py")
        contents = b'#!/bin/sh\necho "prek 0.5.7 (test)"\n' if name == "prek" else b"placeholder\n"
        if name == "policy":
            contents = b'def plan(repo, old, new, policy): return "reviewed"\n'
        path.write_bytes(contents)
        path.chmod(0o700 if name in {"guard", "shim", "prek"} else 0o600)
        paths[name] = path
    paths["trust"] = scripts / "focused_trust.py"
    paths["guard_python"] = Path(sys.executable).resolve()
    paths["dispatcher_python"] = Path(sys.executable).resolve()
    for name in ("dispatcher", "hook", "materializer"):
        (
            repo
            / "scripts"
            / {
                "dispatcher": "focused_dispatch.py",
                "hook": "focused_hook.py",
                "materializer": "focused_materialize.py",
            }[name]
        ).write_bytes(paths[name].read_bytes())
    pin = {
        "repo": str(repo.resolve()),
        "remote_name": "origin",
        "remote_url": "local",
        "destination": "refs/heads/test",
        "policy_commit": "a" * 40,
        "files": {name: {"path": str(path.resolve()), "sha256": sha(path)} for name, path in paths.items()},
    }
    config = hooks / "focused-policy.json"
    config.write_text(json.dumps(pin))
    config.chmod(0o600)
    return repo, hooks, paths


def test_valid_pin_then_nonexecutable_companion_fails(pins):
    repo, hooks, paths = pins
    assert trust.load(hooks, repo, "origin", "local", "b" * 40, "c" * 40, "guard")[1] == "reviewed"
    paths["guard"].chmod(0o600)
    with pytest.raises(ValueError, match="not executable"):
        trust.load(hooks, repo, "origin", "local", "b" * 40, "c" * 40, "guard")


def test_candidate_router_bytes_must_match_independent_pin(pins):
    repo, hooks, _ = pins
    (repo / "scripts/focused_hook.py").write_text("forged")
    with pytest.raises(ValueError, match="candidate hook"):
        trust.load(hooks, repo, "origin", "local", "b" * 40, "c" * 40, "guard")
