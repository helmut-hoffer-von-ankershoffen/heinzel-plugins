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


def test_focused_confidentiality_hook_ignores_foreign_uv_environment(tmp_path):
    import os
    import shlex
    import subprocess

    import yaml

    config = yaml.safe_load((Path(__file__).parents[1] / ".pre-commit-config.yaml").read_text())
    entry = next(
        item["entry"] for repo in config["repos"] for item in repo["hooks"] if item["id"] == "confidentiality-branch"
    )
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    uv = fakebin / "uv"
    uv.write_text('#!/bin/sh\nenv > "$HOME/observed-env"\nprintf "%s\\n" "$@" > "$HOME/observed-args"\n')
    uv.chmod(0o700)
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "PATH": str(fakebin) + ":/usr/bin:/bin",
        "HZ_TRUSTED_FOCUSED_PUSH": "1",
        "UV_PROJECT": "/foreign/project",
        "UV_WORKING_DIR": "/foreign/working-dir",
        "UV_ENV_FILE": "/foreign/env",
        "PYTHONPATH": "/foreign/python",
        "CONFIDENTIAL_TERMS": "fictional-sensitive-marker",
        "CONFIDENTIAL_TERMS_FILE": "/fictional/terms",
    }
    result = subprocess.run(shlex.split(entry), cwd=tmp_path, env=env, text=True, capture_output=True, check=False)  # noqa: S603 - reviewed checked-in hook and fake uv
    assert result.returncode == 0, result.stderr
    observed = (tmp_path / "observed-env").read_text()
    assert "UV_PROJECT=" not in observed and "UV_WORKING_DIR=" not in observed
    assert "UV_ENV_FILE=" not in observed and "PYTHONPATH=" not in observed
    assert "UV_OFFLINE=1" in observed
    assert "CONFIDENTIAL_TERMS=fictional-sensitive-marker" in observed
    assert "CONFIDENTIAL_TERMS_FILE=/fictional/terms" in observed
    args = (tmp_path / "observed-args").read_text().splitlines()
    assert args == [
        "run",
        "--no-env-file",
        "--no-project",
        "--script",
        str(tmp_path / "scripts/check_confidentiality.py"),
        "--branch",
    ]


@pytest.mark.parametrize("source", ["env", "file"])
def test_real_focused_confidentiality_scanner_rejects_fictional_branch(tmp_path, source):
    import os
    import shlex
    import shutil
    import subprocess

    import yaml

    config = yaml.safe_load((Path(__file__).parents[1] / ".pre-commit-config.yaml").read_text())
    entry = next(
        item["entry"] for repo in config["repos"] for item in repo["hooks"] if item["id"] == "confidentiality-branch"
    )
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    shutil.copyfile(
        Path(__file__).parents[1] / "scripts/check_confidentiality.py", scripts_dir / "check_confidentiality.py"
    )
    clean = {key: value for key, value in os.environ.items() if not key.startswith(("GIT_", "UV_", "PYTHON"))}
    git = shutil.which("git")
    assert git
    subprocess.run([git, "init", "-q"], cwd=tmp_path, env=clean, check=True)  # noqa: S603 - resolved Git binary
    subprocess.run([git, "switch", "-qc", "fixture/fictional-sensitive-marker"], cwd=tmp_path, env=clean, check=True)  # noqa: S603 - resolved Git binary
    subprocess.run(  # noqa: S603 - resolved Git binary and disposable fixture
        [
            git,
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "--allow-empty",
            "-qm",
            "fixture",
        ],
        cwd=tmp_path,
        env=clean,
        check=True,
    )
    terms = tmp_path / "terms"
    terms.write_text("fictional-sensitive-marker\n")
    env = {
        **clean,
        "HZ_TRUSTED_FOCUSED_PUSH": "1",
        "UV_PROJECT": "/foreign/project",
        "CONFIDENTIAL_TERMS": "fictional-sensitive-marker" if source == "env" else "",
        "CONFIDENTIAL_TERMS_FILE": str(terms) if source == "file" else "",
    }
    result = subprocess.run(shlex.split(entry), cwd=tmp_path, env=env, capture_output=True, text=True, check=False)  # noqa: S603 - checked-in hook entry
    assert result.returncode == 1
    assert "1 confidential term(s) found; remove them before committing." in result.stderr
