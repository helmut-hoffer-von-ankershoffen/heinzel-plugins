"""Planner revisions remain operands while real revisions still select changed plugins."""

import json
import os
import shutil
import subprocess
import sys

import pytest

from heinzel_plugin_tools import cli

pytestmark = pytest.mark.integration


def test_planner_rejects_git_output_option(tmp_path, monkeypatch):
    destination = tmp_path / "injected"
    monkeypatch.setattr(sys, "argv", ["hz-plugin", "plan", f"--base=--output={destination}"])
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 2
    assert not destination.exists()
    assert not destination.with_name("injected...HEAD").exists()


def test_planner_accepts_real_revision(tmp_path, monkeypatch, capsys):
    for key in list(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delenv(key)

    def git(*arguments):
        return subprocess.check_output(  # noqa: S603 - fixed commands in an isolated fixture repository
            [str(shutil.which("git")), *arguments],
            cwd=tmp_path,
            env={key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
            text=True,
            timeout=10,
        ).strip()

    git("init", "--quiet", "--initial-branch=main")
    git("config", "user.name", "Example Author")
    git("config", "user.email", "author@example.test")
    directory = tmp_path / "plugins/heinzel-harbor"
    directory.mkdir(parents=True)
    (directory / "pyproject.toml").write_text(
        '[project]\nname="heinzel-harbor"\nversion="1.0.0"\n'
        '[project.entry-points."heinzel.modules"]\nharbor="heinzel_harbor"\n'
    )
    git("add", ".")
    git("-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Initial")
    previous = git("rev-parse", "HEAD")
    (directory / "example.txt").write_text("Changed")
    git("add", ".")
    git("-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Change")
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    inventory = cli.projects(tmp_path)
    monkeypatch.setattr(cli, "projects", lambda: inventory)
    monkeypatch.setattr(sys, "argv", ["hz-plugin", "plan", "--base", previous])
    assert cli.main() == 0
    assert [item["name"] for item in json.loads(capsys.readouterr().out)["include"]] == ["heinzel-harbor"]
