"""The same journey against a real temporary Beads database, when `bd` is installed."""

import pytest

pytestmark = pytest.mark.e2e


def test_submit_work_finish_and_release_with_real_beads(issues_kernel, real_bd, bd_run, journey, tmp_path):
    folder = tmp_path / "board"
    folder.mkdir()
    bd_run(["git", "init", "-q"], folder)
    bd_run([real_bd, "init", "--prefix", "demo", "--stealth", "--skip-agents"], folder)
    journey(issues_kernel(folder, real_bd), folder, real_bd, tmp_path)
