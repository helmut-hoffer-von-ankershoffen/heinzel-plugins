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
