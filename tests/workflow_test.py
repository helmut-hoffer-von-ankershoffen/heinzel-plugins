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


def test_confidential_terms_are_scoped_to_real_gallery_and_policy_steps():
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    jobs = workflow["jobs"]
    real_steps = {
        ("policy", "make policies"),
        ("plugin", 'make check NAME="$PLUGIN" CORE="$CORE"'),
    }
    keys = {"CONFIDENTIAL_TERMS", "CONFIDENTIALITY_REQUIRED"}
    scoped = {}
    assert not keys.intersection(workflow.get("env", {}))
    for name, job in jobs.items():
        assert not keys.intersection(job.get("env", {}))
        for step in job.get("steps", []):
            env = step.get("env", {})
            if keys.intersection(env):
                scoped[name, step["run"]] = {key: env[key] for key in keys}
    assert set(scoped) == real_steps
    policy = scoped["policy", "make policies"]
    assert policy["CONFIDENTIAL_TERMS"] == "${{ secrets.CONFIDENTIAL_TERMS }}"
    assert "github.event.pull_request.head.repo.full_name == github.repository" in policy["CONFIDENTIALITY_REQUIRED"]
    assert "github.actor != 'dependabot[bot]'" in policy["CONFIDENTIALITY_REQUIRED"]
    assert all(env == policy for env in scoped.values())
    gallery = jobs["gallery"]
    assert all(not keys.intersection(step.get("env", {})) for step in gallery["steps"])
    assert any(step.get("run") == 'make screenshots-render-check NAME="$PLUGIN"' for step in gallery["steps"])
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


@pytest.mark.parametrize(
    ("selected", "result", "passes"),
    [
        ("True", "success", True),
        ("True", "skipped", False),
        ("True", "failure", False),
        ("True", "cancelled", False),
        ("False", "skipped", True),
        ("False", "success", True),
        ("False", "failure", False),
        ("", "success", False),
        ("true", "success", False),
    ],
)
def test_ci_ok_requires_executed_rendering_for_selected_plugins(selected, result, passes):
    import os
    import subprocess

    jobs = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())["jobs"]
    assert "gallery" in jobs["ok"]["needs"]
    assert jobs["gallery"]["if"] == "needs.plan.outputs.selected == 'True'"
    step = next(step for step in jobs["gallery"]["steps"] if "render-check" in step.get("run", ""))
    assert "if" not in step  # A selected project with no plan must fail, not skip its execution.
    assert step["env"] == {"PLUGIN": "${{ matrix.name }}"}
    assert jobs["gallery"]["permissions"] == {"contents": "read"}
    assert not any("upload-artifact" in step.get("uses", "") for step in jobs["gallery"]["steps"])
    env = dict(
        os.environ,
        EVENT="pull_request",
        POLICY="success",
        PLAN="success",
        PLUGIN="success",
        COVERAGE="success",
        FLOOR="success",
        SCREENSHOTS="success",
        SONAR="success",
        GUARD="success",
        GALLERY=result,
        GALLERY_SELECTED=selected,
    )
    completed = subprocess.run(  # noqa: S603 -- execute the actual aggregate with synthetic statuses only
        ["/bin/bash", "-e", "-c", jobs["ok"]["steps"][0]["run"]],
        env=env,
        capture_output=True,
    )
    assert (completed.returncode == 0) is passes
