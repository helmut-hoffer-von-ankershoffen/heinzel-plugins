import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from heinzel import Config, HeinzelError, Kernel, ModuleRecord, Settings
from heinzel.heads import api, web
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
    client = _signed_in(kernel)
    working = client.get("/api/issues/list").json()["reports"][0]
    assert working["status"] == "Being worked on"
    assert working["body"] == "The footer clock jumps\nIt moves by a pixel."
    assert working["attachments"] == ["shot.png"]
    assert [step["label"] for step in working["history"]] == ["Sent", "Being worked on"]
    assert working["history"][1]["at"] is not None  # Beads records when work started

    run([bd, "close", task_id, "--reason", "Fixed in #7"], folder)
    done = client.get("/api/issues/list").json()["reports"][0]
    assert done["state"] == "done"
    assert done["release"]["version"] == "0.9.27"
    assert done["status"].startswith("Released in 0.9.27 on ")
    assert [step["label"] for step in done["history"]] == ["Sent", "Being worked on", "Done", "Released in 0.9.27"]

    shown = CliRunner().invoke(cli, ["issues", "show", task_id, "--json"])
    assert json.loads(shown.stdout)["details"]["pull_requests"][0]["number"] == 7

    run([bd, "create", "Someone else's chore", "--json"], folder)
    assert len(json.loads(CliRunner().invoke(cli, ["issues", "list", "--json"]).stdout)["reports"]) == 1


TOKEN = "t" * 43


def _signed_in(kernel):
    """The app's own client: the web head with its session token, as the Issues page calls it."""
    client = TestClient(web.build(kernel, port=8000, token=TOKEN, static=None), base_url="http://127.0.0.1:8000")
    client.headers["Authorization"] = f"Bearer {TOKEN}"
    return client


HOSTILE = [
    "--title=Injected title",
    "--file=/etc/passwd",
    "--db=/tmp/elsewhere.db",
    "-p0",
    "--labels=other",
    "--parent=demo-1\n--assignee=nobody",
    "-- --force",
]
"""First lines that `bd` would read as options of its own if they were ever passed bare."""


def _probes(kernel, folder, bd):
    """What a reviewer tried against a real database: option-like text, other work, other people, no login."""
    from heinzel import CurrentUser  # noqa: PLC0415 - after the plugin is importable

    from heinzel_issues import BeadsBoard, IssuesService  # noqa: PLC0415 - after the plugin is importable
    from heinzel_issues._identity import authenticated  # noqa: PLC0415 - after the plugin is importable

    cli = build(kernel)
    service = kernel.resolve(IssuesService)
    board = BeadsBoard(service.settings.beads)
    current = kernel.resolve(CurrentUser)
    for text in HOSTILE:
        with current.local("cli"), authenticated(current):
            through_the_board = service.submit(f"{text}\n{text}", board=board)
            through_the_connector = service.submit(text)
        assert through_the_board.title == through_the_connector.title == text.splitlines()[0]
        assert through_the_board.body == f"{text}\n{text}"
        board.note(through_the_board.details.id, text, "builder")
        assert board.close(through_the_board.details.id, "builder", text).state == "closed"
    rows = json.loads(run([bd, "list", "--all", "--json"], folder))
    assert len(rows) == 2 * len(HOSTILE)  # one item each, nothing else was created or read in
    assert {row["title"] for row in rows} == {text.splitlines()[0] for text in HOSTILE}
    assert all(row["labels"] == ["heinzel-issues"] for row in rows)

    def created(*args):
        data = json.loads(run([bd, "create", *args, "--json"], folder))
        return (data[0] if isinstance(data, list) else data)["id"]

    private = created("--title=Private coordinator bead")
    theirs = created("--title=Their report", "--labels=heinzel-issues", "--actor=someone-else")
    for item in (private, theirs, "demo-404"):
        shown = CliRunner().invoke(cli, ["issues", "show", item, "--json"])
        assert shown.exit_code != 0
        assert f"There is no item {item}." in shown.output  # other work, other people and no such id read the same
        assert "Private" not in shown.output
        assert "Their report" not in shown.output
    listed = CliRunner().invoke(cli, ["issues", "list", "--json"]).stdout
    assert "Private" not in listed
    assert "Their report" not in listed
    assert len(json.loads(listed)["reports"]) == 2 * len(HOSTILE)
    for write in (
        lambda: board.note(private, "x", "builder"),
        lambda: board.claim(private, "builder"),
        lambda: board.transition(private, "in_progress", "builder"),
        lambda: board.attach(private, "a.txt", b"a", "text/plain", "builder"),
        lambda: board.close(private, "builder", "x"),
        lambda: board.transition(theirs, "--claim", "builder"),
        lambda: board.create("heinzel-issues", "x", "x", "mira", ["--db=x"]),
    ):
        with pytest.raises(HeinzelError):
            write()
    assert json.loads(run([bd, "show", private, "--json"], folder))[0]["status"] == "open"

    signed_in = _signed_in(kernel)
    assert signed_in.get("/api/issues/list").status_code == 200
    for anonymous in (
        TestClient(api.build(kernel), base_url="http://localhost").get("/issues/list"),
        TestClient(api.build(kernel), base_url="http://localhost").get(f"/issues/show?id={private}"),
        TestClient(web.build(kernel, port=8000, token=TOKEN, static=None), base_url="http://127.0.0.1:8000").get(
            "/api/issues/list"
        ),
    ):
        assert anonymous.status_code != 200  # without a login nothing is read out
        assert "reports" not in anonymous.text
        assert "Private" not in anonymous.text


@pytest.fixture
def probes():
    """The hostile inputs both the fake and the real `bd` must withstand."""
    return _probes


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
        # CI installs a pinned bd and sets HZ_ISSUES_REQUIRE_BD=1, so there a missing bd fails instead of skipping.
        if os.environ.get("HZ_ISSUES_REQUIRE_BD") == "1":
            pytest.fail("HZ_ISSUES_REQUIRE_BD=1 but the bd program is not installed")
        pytest.skip("the bd program is not installed")
    return REAL_BD
