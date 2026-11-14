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


@pytest.mark.parametrize(
    "expression,allowed,accepted",
    [
        ("MIT", "MIT", True),
        ("Apache-2.0", "Apache-2.0", True),
        ("MIT AND Apache-2.0", "MIT AND Apache-2.0", True),
        ("MIT OR Apache-2.0", "MIT OR Apache-2.0", True),
        ("MIT AND GPL-3.0-only", "MIT", False),
        ("MIT OR GPL-3.0-only", "MIT", False),
        ("MIT AND Apache-2.0", "MIT\nApache-2.0", False),
        ("MIT OR Apache-2.0", "MIT\nApache-2.0", False),
        ("MIT-0", "MIT", False),
        ("Apache-2.0", "Apache", False),
        ("MIT", "mit", False),
        ("mit", "MIT", False),
    ],
)
def test_vendored_license_requires_exact_case_sensitive_allowlist_expression(
    audited, tmp_path, monkeypatch, expression, allowed, accepted
):
    from heinzel_plugin_tools.vendor import VerifiedInventory

    # Only the audit policy is under test; the manifest verifier supplies this inventory in production.
    inventory = VerifiedInventory(("verified.py",), "example-sdk", "1.2.3", expression)
    monkeypatch.setattr(audit.vendor, "project", lambda _root: inventory)
    (tmp_path / ".license-allowlist").write_text(allowed + "\n")
    if accepted:
        licenses, vulnerabilities = audited("pytest")
        assert f"--allow-only={';'.join(allowed.splitlines())}" in licenses["command"]
        assert "example-sdk==1.2.3" in vulnerabilities["requirements"]
    else:
        with pytest.raises(ValueError, match="Vendored upstream license"):
            audited("pytest")


CLOSURE = {"versions": {}, "direct": ["httpx", "pydantic"], "core": ["pydantic", "opentelemetry-api"]}


@pytest.mark.parametrize(
    ("package", "case"),
    [
        ("opentelemetry-api", "core"),  # Core forces the fix with its release
        ("pydantic", "core"),  # declared too, but Core already forces it
        ("httpx", "declared"),
        ("h11", "transitive"),  # reaches users only through httpx
    ],
)
def test_each_vulnerable_package_gets_its_security_relock_case(package, case):
    assert audit.security_case(package, CLOSURE) == case


def test_the_audit_names_the_case_and_the_fix_for_every_finding(tmp_path, capsys):
    report = tmp_path / "audit.json"
    findings = [
        {"name": "h11", "version": "0.14.0", "vulns": [{"id": "GHSA-1", "fix_versions": ["0.16.0"]}]},
        {"name": "httpx", "version": "0.28.1", "vulns": []},
    ]
    report.write_text(json.dumps({"dependencies": findings}))
    audit.report_cases(report, CLOSURE)
    audit.report_cases(tmp_path / "absent.json", CLOSURE)
    assert capsys.readouterr().out == (
        "h11 0.14.0 (GHSA-1; fixed in 0.16.0): comes only through this plugin's dependencies: "
        "add a direct floor (pkg>=fixed), patch bump\n"
    )


def test_a_failing_vulnerability_audit_still_fails_after_naming_the_cases(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    real = subprocess.run

    def run(command, **options):
        if command[:2] == [sys.executable, "-m"] and command[2] in {"piplicenses", "pip_audit"}:
            return subprocess.CompletedProcess(command, 1 if command[2] == "pip_audit" else 0)
        return real(command, **options)

    monkeypatch.setattr(audit.subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["audit", sys.executable, "pytest"])
    with pytest.raises(subprocess.CalledProcessError):
        audit.main()
