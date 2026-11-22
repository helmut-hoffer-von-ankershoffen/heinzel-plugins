"""The gate guard fails a pull request that changes a guarded gate input, unless the owner labelled it."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gate_guard", ROOT / "scripts" / "gate_guard.py")
assert spec
assert spec.loader
guard = importlib.util.module_from_spec(spec)
sys.modules["gate_guard"] = guard
spec.loader.exec_module(guard)

pytestmark = pytest.mark.unit

BASE = "b" * 40
STARTED = "2026-11-22T10:00:00Z"
WORKFLOW = """jobs:
  coverage:
    steps:
      - with:
          MINIMUM_ORANGE: 80
  coverage-floor:
    steps:
      - run: python3 -I scripts/coverage_floor.py
  policy:
    steps:
      - run: make policies
  ok:
    needs: [coverage, coverage-floor]
"""
PYPROJECT = (
    "[project]\nname = 'x'\n[tool.coverage.run]\nsource = ['a']\n[tool.pytest.ini_options]\nx = 1\n[tool.ruff]\n"
)


class Fake:
    """GitHub's answers about one pull request."""

    def __init__(self, labels=(), events=()):
        self.labels, self.events = list(labels), list(events)

    def get(self, path):
        if path == "pulls/7":
            return {"labels": [{"name": name} for name in self.labels]}
        if path == "actions/runs/99":
            return {"created_at": STARTED}
        if path.startswith("issues/7/events"):
            return self.events if path.endswith("page=1") else []
        raise AssertionError(path)


def _files(**changes):
    base = {guard.WORKFLOW: WORKFLOW, "pyproject.toml": PYPROJECT, "scripts/coverage_floor.py": "judge\n"}
    return base, {**base, **changes}


def _run(tmp_path, head_changes, github=None):
    base, head = _files(**head_changes)

    def read_at(revision, path):
        return (base if revision == BASE else head).get(path)

    env = {
        "BASE_SHA": BASE,
        "PR_NUMBER": "7",
        "GITHUB_REPOSITORY_OWNER": "owner",
        "GITHUB_RUN_ID": "99",
        "GITHUB_OUTPUT": str(tmp_path / "out"),
    }
    code = guard.main(env, github or Fake(), read_at)
    return code, (tmp_path / "out").read_text(encoding="utf-8")


def _labelled(at="2026-11-22T10:05:00Z", by="owner"):
    return Fake(
        [guard.LABEL], [{"event": "labeled", "label": {"name": guard.LABEL}, "actor": {"login": by}, "created_at": at}]
    )


def test_unguarded_changes_pass(tmp_path):
    workflow = WORKFLOW.replace("make policies", "make policies NAME=x")
    code, output = _run(tmp_path, {guard.WORKFLOW: workflow, "README.md": "new"})
    assert code == 0
    assert output == "verdict=Gate guard passed: no guarded fact changed\n"


@pytest.mark.parametrize(
    "case",
    [
        ({guard.WORKFLOW: WORKFLOW.replace("MINIMUM_ORANGE: 80", "MINIMUM_ORANGE: 10")}, "ci.yml job coverage"),
        ({guard.WORKFLOW: WORKFLOW.replace("  coverage-floor:\n", "  floor-gone:\n")}, "ci.yml job coverage-floor"),
        ({guard.WORKFLOW: WORKFLOW.replace("[coverage, coverage-floor]", "[coverage]")}, "ci.yml job ok"),
        ({"scripts/coverage_floor.py": "pass\n"}, "file scripts/coverage_floor.py"),
        ({"scripts/gate_guard.py": "new\n"}, "file scripts/gate_guard.py"),
        ({"pyproject.toml": PYPROJECT.replace("source = ['a']", "omit = ['*']")}, "pyproject.toml [tool.coverage*]"),
        ({"pyproject.toml": PYPROJECT.replace("x = 1", "x = 2")}, "pyproject.toml [tool.pytest*]"),
    ],
)
def test_a_guarded_change_fails_without_the_owners_label(tmp_path, case):
    changes, fact = case
    code, output = _run(tmp_path, changes)
    assert code == 1
    assert output.startswith("verdict=Gate guard FAILED (not approved): 1 guarded fact(s) changed (")
    assert fact in output
    assert guard.LABEL in output


@pytest.mark.parametrize(
    ("github", "passes"),
    [
        (_labelled(), True),
        (_labelled(at="2026-11-22T09:59:00Z"), False),  # labelled before this run's push: the new head is unreviewed
        (_labelled(by="someone"), False),
        (Fake([], _labelled().events), False),  # the label was removed again
        (Fake([guard.LABEL], []), False),
    ],
)
def test_only_the_owners_label_after_this_run_started_approves(tmp_path, github, passes):
    code, output = _run(tmp_path, {"scripts/coverage_floor.py": "pass\n"}, github)
    assert code == (0 if passes else 1)
    assert ("approved by the owner's label" in output) is passes


def test_missing_inputs_are_a_tool_error(tmp_path):
    env = {"GITHUB_OUTPUT": str(tmp_path / "out")}
    assert guard.main(env, Fake(), lambda *_: None) == 2
    assert "TOOL ERROR" in (tmp_path / "out").read_text(encoding="utf-8")


def test_the_job_blocks_and_sections_are_read_exactly():
    assert guard.job_block(WORKFLOW, "coverage-floor") == (
        "  coverage-floor:\n    steps:\n      - run: python3 -I scripts/coverage_floor.py"
    )
    assert guard.job_block(WORKFLOW, "absent") is None
    assert guard.sections(PYPROJECT, "coverage") == "[tool.coverage.run]\nsource = ['a']"


def test_git_reads_this_checkout_and_absent_files(tmp_path, monkeypatch):
    identity = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    (tmp_path / "a.txt").write_text("one\n", encoding="utf-8")
    for args in (["init", "-q"], ["add", "a.txt"], [*identity, "commit", "-qm", "c"]):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, timeout=30)  # noqa: S603, S607 - git, fixed args
    monkeypatch.chdir(tmp_path)
    assert guard.show("HEAD", "a.txt") == "one\n"
    assert guard.show("HEAD", "missing.txt") is None
    with pytest.raises(guard.ToolError):
        guard.show("f" * 40, "a.txt")


def test_ci_ok_requires_the_guard_and_the_sonar_ratings_on_pull_requests():
    import yaml

    jobs = yaml.safe_load((ROOT / guard.WORKFLOW).read_text(encoding="utf-8"))["jobs"]
    for job in ("gate-guard", "sonar-ratings"):
        assert job in jobs["ok"]["needs"]
        assert jobs[job]["if"] == "github.event_name == 'pull_request'"
    run = jobs["gate-guard"]["steps"][-1]["run"]
    assert 'git show "$BASE_SHA:scripts/gate_guard.py"' in run
    assert 'BASE_SHA="$(git rev-parse HEAD^1)"' in run
    assert 'pr_only "$SONAR" && pr_only "$GUARD"' in jobs["ok"]["steps"][0]["run"]
    assert set(guard.GUARDED_JOBS) <= set(jobs)
