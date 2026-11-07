import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from heinzel import Config, Kernel, ModuleRecord, Settings
from heinzel.heads import api
from heinzel.heads.cli import build
from heinzel.kernel import Origin, discover
from typer.testing import CliRunner


@pytest.fixture
def make_kernel():
    def make(*, builtins=False, settings_=None, config=None, **modules):
        config = config or Config.empty()
        records = discover(plugins=False)[0] if builtins else []
        records += [
            ModuleRecord(
                qualname=name.replace("__", "."),
                module=module,
                origin=Origin("heinzel-contract-fixture", "1.0.0", builtin=False),
            )
            for name, module in modules.items()
        ]
        return Kernel(settings_ or config.settings(Settings, "hz"), records, config=config)

    return make


# A git hook running these tests exports GIT_DIR and friends; the fixtures' own repositories must not see them.
QUIET = {
    **{key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
    "BD_NON_INTERACTIVE": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
}
REAL_BD = shutil.which("bd") or next((p for p in ("/opt/homebrew/bin/bd",) if os.access(p, os.X_OK)), None)


def run(args, cwd):
    return subprocess.run(args, cwd=cwd, env=QUIET, check=True, capture_output=True, text=True, timeout=60).stdout  # noqa: S603 - test commands


@pytest.fixture
def fake_bd(tmp_path):
    """A `bd` with the same JSON shapes, so the connector is tested where Beads is not installed."""
    shim = tmp_path / "bin" / "bd"
    shim.parent.mkdir()
    shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{Path(__file__).parent / "fake_bd.py"}" "$@"\n')
    shim.chmod(0o755)
    return str(shim)


@pytest.fixture
def clone(tmp_path):
    """A git clone with two squash merges and a release tag after each."""
    folder = tmp_path / "harbor"
    folder.mkdir()
    ident = ["-c", "user.name=Ada Example", "-c", "user.email=ada@example.invalid"]
    run(["git", "init", "-q", "-b", "main"], folder)
    run(["git", *ident, "commit", "-q", "--allow-empty", "-m", "feat: start (#1)"], folder)
    run(["git", *ident, "tag", "-a", "v0.9.26", "-m", "0.9.26"], folder)
    run(["git", *ident, "commit", "-q", "--allow-empty", "-m", "fix(web): keep the clock steady (#7)"], folder)
    run(["git", *ident, "tag", "-a", "v0.9.27", "-m", "0.9.27"], folder)
    return folder


@pytest.fixture
def issues_kernel(make_kernel, clone, tmp_path):
    """A kernel with Issues on a Beads folder, using the given `bd` program."""
    import heinzel_issues

    def make(folder, bd):
        settings = {
            "issues": {
                "tracker": "beads",
                "beads": {"path": str(folder), "bd": bd},
                "releases": [{"path": str(clone), "ref": "main"}],
            },
            "hz": {"state_dir": str(tmp_path / "state")},
        }
        return make_kernel(builtins=True, config=Config(files=(), data=settings), issues=heinzel_issues.module)

    return make


def _journey(kernel, folder, bd, tmp_path):
    cli = build(kernel)
    shot = tmp_path / "shot.png"
    shot.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    sent = CliRunner().invoke(
        cli, ["issues", "submit", "The footer clock jumps\nIt moves by a pixel.", "--attachment", str(shot), "--json"]
    )
    assert sent.exit_code == 0, sent.output
    report = json.loads(sent.stdout)
    assert report["status"] == "Received"
    assert report["title"] == "The footer clock jumps"
    task_id = report["details"]["id"]
    assert (folder / ".beads" / "attachments" / task_id / "shot.png").read_bytes().startswith(b"\x89PNG")

    listed = CliRunner().invoke(cli, ["issues", "list"])
    assert listed.exit_code == 0, listed.output
    assert "The footer clock jumps" in listed.stdout
    assert "Received" in listed.stdout
    assert task_id not in listed.stdout  # ids are for experts and --json only

    run([bd, "update", task_id, "--status", "in_progress"], folder)
    client = TestClient(api.build(kernel), base_url="http://localhost")
    assert client.get("/issues/list").json()["reports"][0]["status"] == "Being worked on"

    run([bd, "close", task_id, "--reason", "Fixed in #7"], folder)
    done = client.get("/issues/list").json()["reports"][0]
    assert done["state"] == "done"
    assert done["release"]["version"] == "0.9.27"
    assert done["status"].startswith("Released in 0.9.27 on ")

    shown = CliRunner().invoke(cli, ["issues", "show", task_id, "--json"])
    assert json.loads(shown.stdout)["details"]["pull_requests"][0]["number"] == 7

    run([bd, "create", "Someone else's chore", "--json"], folder)
    assert len(json.loads(CliRunner().invoke(cli, ["issues", "list", "--json"]).stdout)["reports"]) == 1


@pytest.fixture
def journey():
    """One journey both the fake and the real `bd` must pass: submit, work, finish, release."""
    return _journey


@pytest.fixture
def bd_run():
    return run


@pytest.fixture
def real_bd():
    if REAL_BD is None:
        pytest.skip("the bd program is not installed")
    return REAL_BD
