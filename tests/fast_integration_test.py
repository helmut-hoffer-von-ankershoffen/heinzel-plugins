"""The fast plugin loop executes real owning offline behavior and preserves failures."""

import sys
from pathlib import Path

import pytest

from heinzel_plugin_tools import cli

pytestmark = pytest.mark.integration


def test_fast_loop_runs_an_integration_only_plugin_and_propagates_failure(tmp_path, monkeypatch):
    """An owning offline suite is valid without unit tests; failures must still block a commit."""
    project = cli.Project(
        tmp_path,
        "heinzel-harbor",
        "0.1.0",
        {"project": {"dependencies": [], "entry-points": {"heinzel.modules": {"harbor": "heinzel_harbor"}}}},
    )
    (project.directory / "tests").mkdir()
    test = project.directory / "tests/behavior_test.py"
    (project.directory / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\nmarkers=["integration: Offline public contract", "e2e: External system"]\n'
    )
    monkeypatch.setattr(cli, "prepare_environment", lambda *_: Path(sys.executable))
    monkeypatch.setattr(cli, "boundaries", lambda *_: None)
    monkeypatch.setattr(cli, "python_command", lambda _, _core, command: [sys.executable, "-m", *command])
    original = cli.run
    monkeypatch.setattr(
        cli, "run", lambda command, **kwargs: original(command, **kwargs) if "pytest" in command else None
    )
    test.write_text("import pytest\npytestmark=pytest.mark.integration\ndef test_behavior():\n    assert 2 + 2 == 4\n")
    cli.check(project, None, fast=True)
    test.write_text("import pytest\npytestmark=pytest.mark.integration\ndef test_behavior():\n    assert False\n")
    with pytest.raises(SystemExit) as failure:
        cli.check(project, None, fast=True)
    assert failure.value.code == 1
