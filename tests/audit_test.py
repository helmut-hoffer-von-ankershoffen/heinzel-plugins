"""The runtime-closure audit inspects the owning interpreter and honours a project allowlist."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from heinzel_plugin_tools import audit

pytestmark = pytest.mark.unit


@pytest.fixture
def audited(tmp_path, monkeypatch):
    """Run the inspection for real; record the license and vulnerability tools instead of fetching anything."""
    monkeypatch.chdir(tmp_path)
    calls = []
    real = subprocess.run

    def run(command, **options):
        if command[:2] == [sys.executable, "-m"] and command[2] in {"piplicenses", "pip_audit"}:
            record = {"command": command, "options": options}
            if command[2] == "pip_audit":
                record["requirements"] = Path(command[command.index("-r") + 1]).read_text()
            calls.append(record)
            return subprocess.CompletedProcess(command, 0)
        return real(command, **options)

    monkeypatch.setattr(audit.subprocess, "run", run)

    def go(name):
        monkeypatch.setattr(sys, "argv", ["audit", sys.executable, name])
        audit.main()
        return calls

    return go


def test_the_whole_runtime_closure_is_checked_without_the_owning_distribution(audited):
    licenses, vulnerabilities = audited("pytest")
    packages = licenses["command"][licenses["command"].index("--packages") + 1 :]
    assert {"pytest", "pluggy", "iniconfig"} <= set(packages)
    pinned = dict(line.split("==") for line in vulnerabilities["requirements"].split())
    # The owner itself is excluded because an unpublished local version cannot be looked up on PyPI.
    assert "pytest" not in pinned
    assert set(pinned) == set(packages) - {"pytest"}
    assert "--strict" in vulnerabilities["command"] and "--no-deps" in vulnerabilities["command"]


def test_the_packaged_license_allowlist_applies_when_the_project_has_none(audited):
    licenses, _ = audited("pytest")
    default = Path(audit.__file__).with_name("defaults") / "license-allowlist"
    expected = [line.strip() for line in default.read_text().splitlines() if line.strip() and not line.startswith("#")]
    assert f"--allow-only={';'.join(expected)}" in licenses["command"]


def test_a_project_allowlist_replaces_the_default_and_ignores_comments(audited, tmp_path):
    (tmp_path / ".license-allowlist").write_text("# reviewed 2026\nMIT License\n\n  Apache Software License  \n")
    licenses, _ = audited("pytest")
    assert "--allow-only=MIT License;Apache Software License" in licenses["command"]


def test_an_unknown_distribution_stops_the_audit_before_any_license_check(audited):
    with pytest.raises(subprocess.CalledProcessError):
        audited("heinzel-no-such-distribution")


def run_module(directory, *arguments):
    """Execute the toolkit as a user would, in a fresh interpreter rooted at a disposable collection."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith("PLUGIN_")}
    environment["PLUGIN_SOURCE_ROOT"] = str(directory)
    return subprocess.run(  # noqa: S603 - the running interpreter with fixed module and arguments
        [sys.executable, "-m", "heinzel_plugin_tools", *arguments],
        cwd=directory,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )


def test_module_execution_rejects_unknown_options_with_usage_and_no_traceback(tmp_path):
    result = run_module(tmp_path, "list", "--unknown-option")
    assert result.returncode == 2
    assert "unrecognized arguments: --unknown-option" in result.stderr
    assert "Traceback" not in result.stderr


def test_module_execution_lists_only_the_plugins_of_its_own_collection(tmp_path):
    directory = tmp_path / "plugins/heinzel-harbor"
    directory.mkdir(parents=True)
    (directory / "pyproject.toml").write_text(
        '[project]\nname = "heinzel-harbor"\nversion = "0.3.0"\n'
        '[project.entry-points."heinzel.modules"]\nharbor = "heinzel_harbor"\n'
    )
    result = run_module(tmp_path, "list")
    assert result.returncode == 0
    assert json.loads(result.stdout) == [
        {"name": "heinzel-harbor", "version": "0.3.0", "path": "plugins/heinzel-harbor"}
    ]
