"""The runtime-closure audit inspects the owning interpreter and honours a project allowlist."""

import json
import runpy
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


def test_module_execution_reports_command_failure_without_a_traceback(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["heinzel_plugin_tools", "list", "--unknown-option"])
    with pytest.raises(SystemExit) as stopped:
        runpy.run_module("heinzel_plugin_tools", run_name="__main__")
    assert stopped.value.code == 2
    assert "unrecognized arguments" in capsys.readouterr().err


def test_module_execution_lists_the_collection_as_json(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["heinzel_plugin_tools", "list"])
    with pytest.raises(SystemExit) as stopped:
        runpy.run_module("heinzel_plugin_tools", run_name="__main__")
    assert stopped.value.code == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed and all({"name", "version", "path"} == set(item) for item in listed)
