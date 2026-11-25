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


def test_auto_release_publishes_every_merged_bump_and_never_twice():
    """Owner 2026-11-22: CI publishes a plugin when its bump merges; no channel switch keeps it dark."""
    text = (ROOT / ".github/workflows/auto-release.yml").read_text()
    run = yaml.safe_load(text)["jobs"]["release"]["steps"][-1]["run"]
    assert "RELEASE_CHANNELS" not in text
    assert "plugin_versions.py unreleased --skip-published" in run
    assert "gh workflow run release.yml --ref main" in run and '-f expected_sha="$GREEN_SHA"' in run
    release = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    assert release["run-name"] == "Release ${{ inputs.plugin }}"


def test_every_release_body_comes_from_the_changelog_notes():
    for name in ("compose", "release"):
        workflow = yaml.safe_load((ROOT / ".github/workflows" / f"{name}.yml").read_text())
        steps = [
            step["run"]
            for job in workflow["jobs"].values()
            for step in job.get("steps", [])
            if "publishing --tag" in step.get("run", "") or "scripts/publish.py --tag" in step.get("run", "")
        ]
        assert steps, name
        for run in steps:
            publications = [line for line in run.splitlines() if "--tag" in line]
            assert all('--notes-file "$RUNNER_TEMP/release-notes.md"' in line for line in publications), name
            notes = run.index("scripts/release_notes.py")
            assert notes < run.index("--tag") and '> "$RUNNER_TEMP/release-notes.md"' in run, name


def test_fixture_jobs_do_not_require_private_terms_but_real_capture_does():
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    jobs = workflow["jobs"]
    plan_tests = next(step for step in jobs["plan"]["steps"] if step.get("run") == "make tooling-check")
    coverage_tests = next(
        step for step in jobs["coverage"]["steps"] if step.get("name") == "Measure the shared developer toolkit"
    )
    assert plan_tests["env"]["CONFIDENTIALITY_REQUIRED"] == "false"
    assert coverage_tests["env"]["CONFIDENTIALITY_REQUIRED"] == "false"
    assert jobs["gallery"]["env"]["CONFIDENTIAL_TERMS"] == "${{ secrets.CONFIDENTIAL_TERMS }}"
    assert "github.event_name" in jobs["gallery"]["env"]["CONFIDENTIALITY_REQUIRED"]
    assert "coverage-floor" in jobs["ok"]["needs"]
    assert "gate-guard" in jobs["ok"]["needs"]
    assert "sonar-ratings" in jobs["ok"]["needs"]


@pytest.mark.parametrize("drift", ["none", "sha", "tag"])
def test_automatic_release_guards_execute_against_checkout_and_build(drift):
    import os
    import subprocess

    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    steps = workflow["jobs"]["build"]["steps"]
    guards = [step["run"] for step in steps if "automatic" in step.get("name", "").lower()]
    sha = subprocess.check_output(["/usr/bin/git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    selected = "heinzel-clock/v1.0"
    env = dict(
        os.environ,
        EXPECTED=sha,
        GITHUB_SHA=sha,
        GITHUB_REF="refs/heads/main",
        PLUGIN="heinzel-clock",
        RESUME="",
        TAG=selected,
    )
    if drift == "sha":
        env["EXPECTED"] = "0" * 40
    source = subprocess.run(["/bin/bash", "-ec", guards[0]], cwd=ROOT, env=env)  # noqa: S603 - exercise the repository workflow with synthetic inputs
    env.update(REVISION=sha, SELECTED=selected)
    if drift == "tag":
        env["TAG"] = "heinzel-clock/v1.1"
    version = subprocess.run(["/bin/bash", "-ec", guards[1]], cwd=ROOT, env=env)  # noqa: S603 - exercise the repository workflow with synthetic inputs
    assert (source.returncode == 0) == (drift != "sha")
    assert (version.returncode == 0) == (drift == "none")
    for job in ("publish", "github-publish"):
        assert workflow["jobs"][job]["concurrency"]["group"] == "plugin-publication-${{ needs.build.outputs.tag }}"
