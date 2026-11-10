"""The fixed plan must reach its owning tests and every non-test guard."""

import importlib.util
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

scripts = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(scripts))
spec = importlib.util.spec_from_file_location("focused_dispatch", scripts / "focused_dispatch.py")
dispatcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dispatcher)


def test_dispatch_executes_fixed_owner_and_frontend_plan(tmp_path, monkeypatch):
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "focused-policy.json").write_text(json.dumps({"remote_name": "origin", "remote_url": "example"}))
    plan = SimpleNamespace(
        tooling=("tests/tooling_test.py",),
        owners=(("heinzel-google", ("tests/unit/setup_test.py",)),),
        frontend=(("heinzel-clock", "plugins/heinzel-clock/web/src/ClockPanel.test.tsx"),),
    )
    pin = {"files": {"materializer": {"path": str(scripts / "focused_materialize.py")}}}
    trust = SimpleNamespace(load=lambda *args: (pin, plan))
    monkeypatch.setattr(dispatcher, "git", lambda *args: str(hooks if args[-1] == "hooks" else tmp_path))
    monkeypatch.setattr(dispatcher, "load_installed_trust", lambda path: trust)
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", "a" * 40)
    monkeypatch.setenv("PRE_COMMIT_TO_REF", "b" * 40)

    @contextmanager
    def snapshot(repo, rev):
        yield tmp_path

    materializer = SimpleNamespace(materialized=snapshot)
    loader = SimpleNamespace(exec_module=lambda module: setattr(module, "materialized", snapshot))
    fake_spec = SimpleNamespace(loader=loader)
    monkeypatch.setattr(dispatcher.importlib.util, "spec_from_file_location", lambda *args: fake_spec)
    monkeypatch.setattr(dispatcher.importlib.util, "module_from_spec", lambda spec: materializer)
    commands = []
    monkeypatch.setattr(dispatcher, "run", lambda command, cwd: commands.append(command))
    dispatcher.dispatch()
    joined = [" ".join(command) for command in commands]
    assert any("ruff check scripts tests src/heinzel_plugin_tools" in cmd for cmd in joined)
    assert any("ruff format --check" in cmd for cmd in joined)
    assert any("pytest tests/tooling_test.py -q -n 2" in cmd for cmd in joined)
    assert any("actionlint" in cmd for cmd in joined)
    assert any("zizmor --offline" in cmd for cmd in joined)
    assert any("heinzel-google tests/unit/setup_test.py" in cmd and "frontend=False" in cmd for cmd in joined)
    assert any("run typecheck" in cmd for cmd in joined)
    assert any("ClockPanel.test.tsx" in cmd and "--maxWorkers=2" in cmd for cmd in joined)


def test_missing_pinned_trust_loader_fails_closed(tmp_path):
    with pytest.raises((FileNotFoundError, ImportError)):
        dispatcher.load_installed_trust(tmp_path)


def test_dispatch_strips_caller_execution_overrides(tmp_path, monkeypatch):
    for key in (
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "PYTHONPATH",
        "PYTEST_ADDOPTS",
        "PLUGIN_SOURCE_ROOT",
        "NODE_OPTIONS",
        "UV_NO_SYNC",
        "UV_PROJECT",
    ):
        monkeypatch.setenv(key, "forged")
    observed = {}
    monkeypatch.setattr(dispatcher.subprocess, "run", lambda command, **kwargs: observed.update(kwargs))
    dispatcher.run(["test-command"], tmp_path)
    env = observed["env"]
    assert all(
        key not in env
        for key in (
            "GIT_DIR",
            "GIT_INDEX_FILE",
            "PYTHONPATH",
            "PYTEST_ADDOPTS",
            "NODE_OPTIONS",
            "UV_NO_SYNC",
            "UV_PROJECT",
        )
    )
    assert env["PLUGIN_SOURCE_ROOT"] == str(tmp_path)
    assert env["UV_OFFLINE"] == "1"
