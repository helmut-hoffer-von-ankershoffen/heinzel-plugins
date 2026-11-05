"""Owning CI and protected releases share locked browser OS setup before acceptance."""

import json
import os
import runpy
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit
ROOT = Path(__file__).parents[1]
SCRIPT = runpy.run_path(str(ROOT / "scripts/browser_dependencies.py"))
BOOTSTRAP = SCRIPT["bootstrap"]
COMMAND = "uv run --frozen --no-build --group tooling python scripts/browser_dependencies.py"


def workflow(name):
    return yaml.safe_load((ROOT / f".github/workflows/{name}.yml").read_text())


def test_ci_and_release_share_setup_before_installed_acceptance():
    steps = workflow("ci")["jobs"]["plugin"]["steps"]
    setup = next(step for step in steps if step.get("run") == COMMAND)
    acceptance = next(step for step in steps if "make acceptance" in step.get("run", ""))
    assert steps.index(setup) < steps.index(acceptance)
    assert setup["env"]["PLUGIN"] == "${{ matrix.name }}"
    release = next(step for step in workflow("release")["jobs"]["build"]["steps"] if step.get("id") == "verify")
    assert release["if"] == "inputs.resume_tag == ''"
    assert release["env"]["PLUGIN"] == "${{ inputs.plugin }}"
    assert release["run"].index(COMMAND) < release["run"].index('hz-plugin verify-release "$PLUGIN"')
    assert release["run"].index('test "$PUBLISH" != true || test "$REF" = refs/heads/main') < release["run"].index(
        COMMAND
    )
    assert release["run"].index('if [ "$REGISTRY" = pypi ] && [ "$PRIVATE" = true ]; then') < release["run"].index(
        COMMAND
    )


def owner(tmp_path, *, declared=True, locked=True):
    directory = tmp_path / "plugins/owning project"
    directory.mkdir(parents=True)
    (directory / "pyproject.toml").write_text(
        '[project]\nname="heinzel-example"\nversion="1.0.0"\n'
        '[project.entry-points."heinzel.modules"]\nexample="must_not_import"\n'
    )
    (directory / "must_not_import.py").write_text('raise AssertionError("Never import project code")\n')
    browser = directory / "tests/browser"
    browser.mkdir(parents=True)
    (browser / "package.json").write_text(
        json.dumps({"scripts": {"browser:install-deps": "declared"} if declared else {}})
    )
    if locked:
        (browser / "package-lock.json").write_text("{}\n")
    return browser


@pytest.mark.parametrize("name", ["example", "heinzel-example"])
def test_project_selection_runs_exact_locked_commands_without_import_or_shell(tmp_path, monkeypatch, name):
    browser = owner(tmp_path)
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda command, **kw: calls.append((command, kw)))
    assert BOOTSTRAP(name, tmp_path) is True
    assert [call[0] for call in calls] == [
        ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"],
        ["npm", "run", "--ignore-scripts", "browser:install-deps"],
    ]
    assert all(call[1] == {"cwd": browser, "check": True, "timeout": 120} for call in calls)


@pytest.mark.parametrize("missing_package", [False, True])
def test_missing_declaration_is_noop(tmp_path, monkeypatch, missing_package):
    browser = owner(tmp_path, declared=False)
    if missing_package:
        (browser / "package.json").unlink()
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: pytest.fail("Undeclared dependencies cannot execute"))
    assert BOOTSTRAP("example", tmp_path) is False


def test_declared_dependencies_refuse_missing_lock(tmp_path, monkeypatch):
    owner(tmp_path, locked=False)
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: pytest.fail("Unlocked dependencies cannot execute"))
    with pytest.raises(ValueError, match="package-lock"):
        BOOTSTRAP("example", tmp_path)


@pytest.mark.parametrize("name", ["../example", "--example", "example;echo injected", "$(id)", "absent"])
def test_unsafe_or_unknown_project_cannot_execute(tmp_path, monkeypatch, name):
    owner(tmp_path)
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: pytest.fail("Unsafe selection cannot execute"))
    with pytest.raises(ValueError):
        BOOTSTRAP(name, tmp_path)


def test_project_browser_cannot_escape_owner(tmp_path, monkeypatch):
    browser = owner(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (browser / "package.json").unlink()
    (browser / "package-lock.json").unlink()
    browser.rmdir()
    browser.symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: pytest.fail("Escaped selection cannot execute"))
    with pytest.raises(ValueError):
        BOOTSTRAP("example", tmp_path)


@pytest.mark.parametrize(
    "publish,ref,private", [("true", "refs/heads/unsafe", "false"), ("true", "refs/heads/main", "true")]
)
def test_release_rejects_wrong_ref_and_private_pypi_before_bootstrap(tmp_path, publish, ref, private):
    step = next(step for step in workflow("release")["jobs"]["build"]["steps"] if step.get("id") == "verify")
    binary = tmp_path / "uv"
    marker = tmp_path / "executed"
    binary.write_text('#!/bin/sh\ntouch "$BOOTSTRAP_MARKER"\n')
    binary.chmod(0o700)
    result = subprocess.run(  # noqa: S603 - executes the checked-in workflow against a marker-only uv fixture
        ["/bin/bash", "-e", "-c", step["run"]],
        env=dict(
            os.environ,
            PATH=f"{tmp_path}:/usr/bin:/bin",
            BOOTSTRAP_MARKER=str(marker),
            PUBLISH=publish,
            REF=ref,
            REGISTRY="pypi",
            PRIVATE=private,
        ),
        check=False,
        capture_output=True,
    )
    assert result.returncode != 0
    assert not marker.exists()


def test_new_ci_script_declares_python_metadata():
    text = (ROOT / "scripts/browser_dependencies.py").read_text()
    metadata = text.split("# /// script\n", 1)[1].split("# ///", 1)[0]
    parsed = tomllib.loads("\n".join(line.removeprefix("# ") for line in metadata.splitlines()))
    assert parsed == {"requires-python": ">=3.12", "dependencies": []}


def test_published_composition_prepares_exact_profile_before_acceptance():
    step = next(
        step for step in workflow("compose")["jobs"]["compose"]["steps"] if "scripts/compose.py" in step.get("run", "")
    )
    hook = f"BROWSER_PROFILE=standard {COMMAND}"
    assert step["run"].index('test "$REF" = refs/heads/main') < step["run"].index(hook)
    assert step["run"].index(hook) < step["run"].index("python scripts/compose.py")


def test_composition_profile_selects_only_its_owning_projects(tmp_path, monkeypatch):
    browser = owner(tmp_path)
    metadata = browser.parents[1] / "pyproject.toml"
    metadata.write_text(metadata.read_text() + '[tool.heinzel.plugin]\nprofiles=["standard"]\n')
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda command, **kw: calls.append((command, kw)))
    SCRIPT["bootstrap_profile"]("different", tmp_path)
    assert calls == []
    SCRIPT["bootstrap_profile"]("standard", tmp_path)
    assert len(calls) == 2
    assert all(call[1]["cwd"] == browser for call in calls)
