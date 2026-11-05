"""Owning CI bootstraps declared OS libraries before isolated wheel acceptance."""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit


def test_owning_browser_dependencies_use_owning_lock_before_acceptance():
    workflow = yaml.safe_load((Path(__file__).parents[1] / ".github/workflows/ci.yml").read_text())
    steps = workflow["jobs"]["plugin"]["steps"]
    setup = next(
        step for step in steps if step.get("name") == "Install declared browser runner libraries from the owning lock"
    )
    acceptance = next(
        step for step in steps if step.get("name") == "Test the installed owning wheel in the browser when declared"
    )
    assert steps.index(setup) < steps.index(acceptance)
    assert setup["env"]["DIRECTORY"] == "${{ matrix.path }}"
    assert 'npm --prefix "$DIRECTORY/tests/browser" ci --ignore-scripts --no-audit --no-fund' in setup["run"]
    assert (
        'npm --prefix "$DIRECTORY/tests/browser" run --ignore-scripts --if-present browser:install-deps' in setup["run"]
    )
    assert "heinzel-google" not in setup["run"]
