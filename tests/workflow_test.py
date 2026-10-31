"""Local release scripts must exist on fresh runners, and uploads precede immutable publication."""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

ROOT = Path(__file__).parents[1]


def missing_checkout(workflow):
    problems = []
    for name, job in workflow["jobs"].items():
        checked_out = False
        for step in job.get("steps", []):
            if step.get("uses", "").startswith("actions/checkout@"):
                checked_out = True
            if "scripts/" in step.get("run", "") and not checked_out:
                problems.append(name)
    return problems


def test_local_script_execution_requires_checkout_on_its_own_job():
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        assert missing_checkout(yaml.safe_load(path.read_text())) == [], path


def test_guard_reproduces_a_publish_runner_with_no_source_checkout():
    assert missing_checkout({"jobs": {"publish": {"steps": [{"run": "uv run scripts/publish.py"}]}}}) == ["publish"]


def latest_policy_violations(name, workflow):
    expected = "true" if name == "compose" else "false"
    return [
        job_name
        for job_name, job in workflow["jobs"].items()
        for step in job.get("steps", [])
        if ("publishing --tag" in step.get("run", "") or "scripts/publish.py --tag" in step.get("run", ""))
        and f"--make-latest {expected}" not in step["run"]
    ]


def test_only_the_serialized_standard_app_writer_can_designate_latest():
    for name in ("compose", "release", "tools-release"):
        workflow = yaml.safe_load((ROOT / ".github/workflows" / f"{name}.yml").read_text())
        assert latest_policy_violations(name, workflow) == []
        if name == "compose":
            assert workflow["concurrency"] == {
                "group": "standard-app-${{ github.repository }}",
                "cancel-in-progress": False,
            }


def test_latest_policy_check_rejects_a_plugin_writer_without_explicit_policy():
    workflow = {"jobs": {"publish": {"steps": [{"run": "python -m heinzel_plugin_tools.publishing --tag example"}]}}}
    assert latest_policy_violations("release", workflow) == ["publish"]


def test_auto_release_runs_only_trusted_code_from_a_green_main_tip():
    workflow = yaml.safe_load((ROOT / ".github/workflows/auto-release.yml").read_text())
    job = workflow["jobs"]["release"]
    for guard in (
        "workflow_run.conclusion == 'success'",
        "workflow_run.event == 'push'",
        "workflow_run.head_repository.full_name == github.repository",
        "workflow_run.head_sha == github.sha",
    ):
        assert guard in job["if"]
    checkout = job["steps"][0]
    assert "actions/checkout" in checkout["uses"]
    assert "ref" not in checkout["with"]
    assert job["permissions"] == {"contents": "read", "actions": "write"}
