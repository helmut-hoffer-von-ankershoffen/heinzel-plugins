"""Evidence for the inert focused-policy planner; not a hook bypass."""

import os
import subprocess

import pytest

from heinzel_plugin_tools import focused_policy as policy

pytestmark = pytest.mark.integration


def git(repo, *args):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    # All arguments are fixed by this disposable local Git fixture.
    return subprocess.check_output(["git", *args], cwd=repo, env=env, text=True).strip()  # noqa: S603, S607


def commit(repo, name):
    git(repo, "add", ".")
    git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", name)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def history(tmp_path, monkeypatch):
    git(tmp_path, "init", "-q")
    (tmp_path / "test.py").write_text("contract\n")
    (tmp_path / "source").write_text("base\n")
    anchor = commit(tmp_path, "anchor")
    (tmp_path / "old").write_text("old\n")
    old = commit(tmp_path, "old")
    (tmp_path / "source").write_text("feature\n")
    candidate = commit(tmp_path, "candidate")
    git(tmp_path, "checkout", "-qb", "policy", anchor)
    (tmp_path / "policy").write_text("trusted\n")
    trusted = commit(tmp_path, "policy")
    git(tmp_path, "checkout", "-q", "--detach", candidate)
    git(
        tmp_path,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "merge",
        "-q",
        "--no-ff",
        trusted,
        "-m",
        "merge",
    )
    head = git(tmp_path, "rev-parse", "HEAD")
    monkeypatch.setattr(policy, "ANCHOR", anchor)
    monkeypatch.setattr(policy, "PLANS", {old: (candidate, ("test.py",))})
    monkeypatch.setattr(policy, "POLICY_PATHS", frozenset({"policy"}))
    return tmp_path, old, head, trusted


def test_exact_reviewed_history_selects_fixed_tests(history):
    repo, old, head, trusted = history
    assert isinstance(policy.plan(repo, old, head, trusted), policy.CheckPlan)


def test_unknown_base_and_untrusted_policy_are_rejected(history):
    repo, old, head, trusted = history
    with pytest.raises(ValueError):
        policy.plan(repo, "0" * 40, head, trusted)
    with pytest.raises(ValueError):
        policy.plan(repo, old, head, old)


def test_missing_or_modified_contract_is_rejected(history):
    repo, old, _, trusted = history
    (repo / "test.py").unlink()
    new = commit(repo, "remove contract")
    with pytest.raises(ValueError):
        policy.plan(repo, old, new, trusted)


def test_modified_policy_and_unknown_changes_are_rejected(history):
    repo, old, _, trusted = history
    (repo / "policy").write_text("forged\n")
    new = commit(repo, "forge")
    with pytest.raises(ValueError):
        policy.plan(repo, old, new, trusted)
    (repo / "policy").write_text("trusted\n")
    (repo / "unknown").write_text("unknown\n")
    new = commit(repo, "unknown")
    with pytest.raises(ValueError):
        policy.plan(repo, old, new, trusted)


def test_dirty_checkout_fails_closed(history):
    repo, old, head, trusted = history
    (repo / "source").write_text("dirty\n")
    with pytest.raises(ValueError):
        policy.plan(repo, old, head, trusted)


def test_google_plan_includes_changed_tooling_contract_fixture():
    old = "39c5bcd10f675c63df1b8c1e5892a4fd3a89006f"
    assert "tests/tooling_test.py" in policy.POLICY_PATHS
    assert "tests/tooling_test.py" in policy.PLANS[old][1]


def test_gallery_policy_requires_the_separately_pinned_pushed_commit(history, monkeypatch):
    repo, old, head, trusted = history
    monkeypatch.setattr(policy, "GALLERY_ORIGINAL", old)
    with pytest.raises(ValueError, match="pinned, direct policy successor"):
        policy.plan(repo, old, head, trusted)
    # A merge of the frozen source and policy cannot impersonate its single-parent policy successor.
    with pytest.raises(ValueError, match="pinned, direct policy successor"):
        policy.plan(repo, old, head, head)


def test_reviewed_gallery_runtime_paths_do_not_extend_historical_policy(history, monkeypatch):
    repo, old, _, _ = history
    candidate, _ = policy.PLANS[old]
    git(repo, "checkout", "-q", "--detach", candidate)
    for path in (".python-version", "pyproject.toml", "uv.lock", ".github/workflows/ci.yml"):
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("reviewed CPython 3.15 tooling input\n")
    new = commit(repo, "pin gallery runtime")
    with pytest.raises(ValueError, match="unknown change after frozen candidate"):
        policy.plan(repo, old, new, new)
    monkeypatch.setattr(policy, "GALLERY_ORIGINAL", old)
    monkeypatch.setattr(
        policy,
        "GALLERY_RUNTIME_BLOBS",
        {path: git(repo, "rev-parse", f"{new}:{path}") for path in policy.GALLERY_RUNTIME_BLOBS},
    )
    assert isinstance(policy.plan(repo, old, new, new), policy.CheckPlan)
    lock = repo / "uv.lock"
    approved_lock = lock.read_text()
    lock.write_text("unreviewed dependency bytes\n")
    git(repo, "add", "uv.lock")
    git(
        repo,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "--amend",
        "--no-edit",
        "-q",
    )
    new = git(repo, "rev-parse", "HEAD")
    with pytest.raises(ValueError, match="gallery runtime input differs from its reviewed blob: uv.lock"):
        policy.plan(repo, old, new, new)
    lock.write_text(approved_lock)
    (repo / "source").write_text("unreviewed source change\n")
    git(repo, "add", "source", "uv.lock")
    git(
        repo,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "--amend",
        "--no-edit",
        "-q",
    )
    new = git(repo, "rev-parse", "HEAD")
    with pytest.raises(ValueError, match="unknown change after frozen candidate"):
        policy.plan(repo, old, new, new)


def test_gallery_plan_covers_every_published_owner_and_named_clock_view():
    _, targets = policy.PLANS[policy.GALLERY_ORIGINAL]
    assert all(path.startswith(("plugins/", "tests/")) for path in targets)
    assert {path.split("/")[1] for path in targets if path.startswith("plugins/") and "/tests/" in path} == {
        "heinzel-atlassian",
        "heinzel-clock",
        "heinzel-example",
        "heinzel-github",
        "heinzel-google",
        "heinzel-issues",
        "heinzel-resource",
        "heinzel-slack",
        "heinzel-tailscale",
        "heinzel-theme",
        "heinzel-weather",
        "heinzel-zoom",
    }
    assert [p for p in targets if "/web/" in p] == ["plugins/heinzel-clock/web/src/ClockPanel.test.tsx"]


@pytest.mark.parametrize("reviewed_head", ["GALLERY_HOSTED_HEAD", "GALLERY_CLOCK_HEAD"])
def test_gallery_hosted_repair_requires_exact_parent_and_reviewed_blobs(history, monkeypatch, reviewed_head):
    repo, original, _, _ = history
    candidate, _ = policy.PLANS[original]
    git(repo, "checkout", "-q", "--detach", candidate)
    (repo / "policy").write_text("first hosted candidate\n")
    hosted = commit(repo, "hosted")
    metadata = "plugins/heinzel-weather/pyproject.toml"
    updated = repo / metadata
    updated.parent.mkdir(parents=True)
    updated.write_text('version = "0.5.9"\n')
    fixture = repo / policy.GALLERY_CAPTURE_FIXTURE
    fixture.parent.mkdir()
    fixture.write_text("reviewed fixture\n")
    receipt = repo / "clock-capture.json"
    if reviewed_head == "GALLERY_CLOCK_HEAD":
        receipt.write_text("reviewed capture\n")
    repair = commit(repo, "exact repair")
    monkeypatch.setattr(policy, "GALLERY_ORIGINAL", original)
    monkeypatch.setattr(policy, reviewed_head, hosted)
    monkeypatch.setattr(policy, "GALLERY_RUNTIME_BLOBS", {})
    monkeypatch.setattr(policy, "GALLERY_POLICY_PATHS", policy.GALLERY_POLICY_PATHS | {"policy"})
    monkeypatch.setattr(
        policy,
        "GALLERY_FORWARD_BLOBS",
        {path: git(repo, "rev-parse", f"{repair}:{path}") for path in (metadata, policy.GALLERY_CAPTURE_FIXTURE)},
    )
    if reviewed_head == "GALLERY_CLOCK_HEAD":
        monkeypatch.setattr(
            policy, "GALLERY_CLOCK_BLOBS", {receipt.name: git(repo, "rev-parse", f"{repair}:{receipt.name}")}
        )
    assert policy.GALLERY_CAPTURE_FIXTURE in policy.plan(repo, hosted, repair, repair).tooling
    with pytest.raises(ValueError, match="pinned, direct policy successor"):
        policy.plan(repo, original, repair, repair)
    git(repo, "checkout", "-q", "--detach", hosted)
    updated.parent.mkdir(parents=True, exist_ok=True)
    updated.write_text('version = "0.5.10"\n')
    fixture.parent.mkdir(exist_ok=True)
    fixture.write_text("reviewed fixture\n")
    if reviewed_head == "GALLERY_CLOCK_HEAD":
        receipt.write_text("reviewed capture\n")
    differently_versioned = commit(repo, "unreviewed package version")
    with pytest.raises(ValueError, match="gallery runtime input differs from its reviewed blob"):
        policy.plan(repo, hosted, differently_versioned, differently_versioned)


def test_gallery_theme_diagnostic_accepts_only_reviewed_bytes_on_the_clock_successor(history, monkeypatch):
    repo, original, _, _ = history
    candidate, tests = policy.PLANS[original]
    git(repo, "checkout", "-q", "--detach", candidate)
    fixture = repo / policy.GALLERY_CAPTURE_FIXTURE
    fixture.parent.mkdir()
    fixture.write_text("retained hosted fixture\n")
    receipt = repo / "clock-capture.json"
    receipt.write_text("retained Clock receipt\n")
    hosted = commit(repo, "published Clock repair")
    monkeypatch.setattr(policy, "GALLERY_ORIGINAL", original)
    monkeypatch.setattr(policy, "GALLERY_THEME_HEAD", hosted)
    monkeypatch.setattr(policy, "GALLERY_RUNTIME_BLOBS", {})
    monkeypatch.setattr(
        policy, "GALLERY_FORWARD_BLOBS", {policy.GALLERY_CAPTURE_FIXTURE: git(repo, "hash-object", fixture)}
    )
    monkeypatch.setattr(policy, "GALLERY_CLOCK_BLOBS", {receipt.name: git(repo, "hash-object", receipt)})
    test_path = "tests/capture_test.py"
    monkeypatch.setitem(policy.PLANS, original, (candidate, (*tests, test_path)))
    pins = {}
    for path in policy.GALLERY_THEME_BLOBS:
        file = repo / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(f"reviewed diagnostic for {path}\n")
        pins[path] = git(repo, "hash-object", file)
    monkeypatch.setattr(policy, "GALLERY_THEME_BLOBS", pins)
    approved = commit(repo, "reviewed diagnostic")
    assert policy.plan(repo, hosted, approved, approved).tooling == (test_path, policy.GALLERY_CAPTURE_FIXTURE)
    with pytest.raises(ValueError, match="pinned, direct policy successor"):
        policy.plan(repo, original, approved, approved)
    with monkeypatch.context() as previous:
        previous.setattr(policy, "GALLERY_THEME_HEAD", "0" * 40)
        previous.setattr(policy, "GALLERY_CLOCK_HEAD", hosted)
        with pytest.raises(ValueError, match="unknown change after frozen candidate"):
            policy.plan(repo, hosted, approved, approved)

    for path in (*pins, policy.GALLERY_CAPTURE_FIXTURE, receipt.name, "scripts/focused_dispatch.py"):
        git(repo, "checkout", "-q", "--detach", hosted)
        git(repo, "checkout", approved, "--", ".")
        changed = repo / path
        changed.parent.mkdir(parents=True, exist_ok=True)
        changed.write_text("different bytes\n")
        rejected = commit(repo, "unreviewed replacement")
        reason = "differs from its reviewed blob" if path in pins else "outside its reviewed scope"
        with pytest.raises(ValueError, match=reason):
            policy.plan(repo, hosted, rejected, rejected)


@pytest.fixture(
    params=[
        ("GALLERY_CAPTURE", "GALLERY_THEME", "capture_host.py"),
        ("GALLERY_SCENE", "GALLERY_CAPTURE", "capture_scene.py"),
    ],
    ids=["capture-inventory", "fixed-scene-launch"],
)
def repair_stage(request):
    return request.param


@pytest.fixture
def capture_repair(history, monkeypatch, repair_stage):
    repo, original, _, _ = history
    candidate, tests = policy.PLANS[original]
    git(repo, "checkout", "-q", "--detach", candidate)
    inherited = ("GALLERY_RUNTIME_BLOBS", "GALLERY_FORWARD_BLOBS", "GALLERY_CLOCK_BLOBS", "GALLERY_THEME_BLOBS")
    stage, prior, module = repair_stage
    if prior == "GALLERY_CAPTURE":
        inherited += ("GALLERY_CAPTURE_BLOBS",)
    introduced = f"src/heinzel_plugin_tools/{module}"
    repair_blobs = getattr(policy, f"{stage}_BLOBS")
    prior_paths = {p for group in inherited for p in getattr(policy, group)}
    for name in prior_paths | (repair_blobs.keys() - {introduced}):
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"before repair: {name}\n")
    hosted = commit(repo, "published repair parent")
    for group in inherited:
        pins = {p: git(repo, "rev-parse", f"{hosted}:{p}") for p in getattr(policy, group)}
        monkeypatch.setattr(policy, group, pins)

    pins = {}
    for name in repair_blobs:
        path = repo / name
        path.write_text(f"reviewed capture repair: {name}\n")
        pins[name] = git(repo, "hash-object", name)
    approved = commit(repo, "capture repair")
    monkeypatch.setattr(policy, "GALLERY_ORIGINAL", original)
    monkeypatch.setattr(policy, f"{stage}_HEAD", hosted)
    monkeypatch.setattr(policy, f"{stage}_BLOBS", pins)
    selected = ("tests/capture_test.py", "tests/cli_commands_test.py", "tests/presentation_test.py")
    monkeypatch.setitem(policy.PLANS, original, (candidate, (*tests, *selected)))
    return repo, hosted, approved, introduced, selected


def test_capture_repair_preserves_inventory_and_requires_direct_reviewed_parent(
    capture_repair, repair_stage, monkeypatch
):
    repo, hosted, approved, _, selected = capture_repair
    assert policy.plan(repo, hosted, approved, approved).tooling == (*selected, policy.GALLERY_CAPTURE_FIXTURE)
    stage, prior, _ = repair_stage
    with monkeypatch.context() as previous:
        previous.setattr(policy, f"{stage}_HEAD", "0" * 40)
        previous.setattr(policy, f"{prior}_HEAD", hosted)
        with pytest.raises(ValueError, match="outside its reviewed scope|exact reviewed path set"):
            policy.plan(repo, hosted, approved, approved)
    (repo / "intermediate").write_text("unreviewed descendant\n")
    later = commit(repo, "second successor")
    with pytest.raises(ValueError, match="pinned, direct policy successor"):
        policy.plan(repo, hosted, later, later)


def test_capture_repair_refuses_modified_omitted_extra_and_executable_inputs(capture_repair, repair_stage):
    repo, hosted, approved, introduced, _ = capture_repair
    stage, _, _ = repair_stage
    for name in getattr(policy, f"{stage}_BLOBS"):
        git(repo, "checkout", "-q", "--detach", hosted)
        git(repo, "checkout", approved, "--", ".")
        (repo / name).write_text("different bytes\n")
        rejected = commit(repo, "unreviewed replacement")
        with pytest.raises(ValueError, match="differs from its reviewed blob"):
            policy.plan(repo, hosted, rejected, rejected)
    for change in ("omitted", "extra", "executable"):
        git(repo, "checkout", "-q", "--detach", hosted)
        git(repo, "checkout", approved, "--", ".")
        if change == "omitted":
            (repo / introduced).unlink()
        elif change == "extra":
            (repo / "src/heinzel_plugin_tools/privacy.py").write_text("unapproved change to prior diagnostic\n")
        else:
            (repo / introduced).chmod(0o755)
        rejected = commit(repo, change)
        reason = "differs from its reviewed blob" if change == "executable" else "exact reviewed path set"
        with pytest.raises(ValueError, match=reason):
            policy.plan(repo, hosted, rejected, rejected)
