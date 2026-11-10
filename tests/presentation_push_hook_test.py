"""The installed hook preserves the complete Git stream and fails closed for the diagnostic."""

import hashlib
import importlib
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
HEAD = "a" * 40


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    return importlib.import_module("install_push_hook"), importlib.import_module("presentation_push")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def stock_hook(tmp_path, modules):
    installer, _ = modules
    runner = tmp_path / "prek"
    runner.write_text(
        "#!/bin/sh\n"
        'cat "$HZ_PLUGINS_PUSH_REFS_FILE" > "$TMPDIR/captured"\n'
        'cat > "$TMPDIR/replayed"\n'
        'printf "%s" "$HZ_PLUGINS_PUSH_REFS_FILE" > "$TMPDIR/capture-path"\n'
        'exit "${FIXTURE_EXIT:-0}"\n'
    )
    runner.chmod(0o755)
    hook = tmp_path / "pre-push"
    hook.write_text(installer.SHIM.replace("{runner}", str(runner)))
    hook.chmod(0o755)
    return hook


@pytest.mark.parametrize("stream", [b"", b"one\nsecond\n", b"trailing\n\n", b"partial", b"\x00\xff"])
@pytest.mark.parametrize("exit_code", [0, 7])
def test_private_capture_replaces_spoofed_env_and_replays_all_bytes(stock_hook, tmp_path, modules, stream, exit_code):
    installer, _ = modules
    installer.replace_hook(stock_hook, digest(stock_hook))
    inherited = tmp_path / "spoof"
    inherited.write_bytes(b"caller input")
    result = subprocess.run(  # noqa: S603 - run the disposable installed shim
        [stock_hook, "origin", "fixture"],
        input=stream,
        env={
            "PATH": os.environ["PATH"],
            "TMPDIR": str(tmp_path),
            installer.REFS: str(inherited),
            "FIXTURE_EXIT": str(exit_code),
        },
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == exit_code
    assert (tmp_path / "captured").read_bytes() == (tmp_path / "replayed").read_bytes() == stream
    assert inherited.read_bytes() == b"caller input"
    assert not Path((tmp_path / "capture-path").read_text()).exists()
    assert not list(tmp_path.glob("hz-plugins-push.*"))


def test_install_is_idempotent_and_exactly_reversible(stock_hook, modules):
    installer, _ = modules
    original = stock_hook.read_bytes()
    before, after = installer.replace_hook(stock_hook, digest(stock_hook))
    assert installer.replace_hook(stock_hook, after) == (after, after)
    assert installer.replace_hook(stock_hook, after, restore=True) == (after, before)
    assert stock_hook.read_bytes() == original and stock_hook.stat().st_mode & 0o777 == 0o755


def test_wrong_hash_and_unfamiliar_shims_are_preserved(stock_hook, modules):
    installer, _ = modules
    before = digest(stock_hook)
    with pytest.raises(ValueError, match="reviewed hash"):
        installer.replace_hook(stock_hook, "0" * 64)
    assert digest(stock_hook) == before
    stock_hook.write_text(stock_hook.read_text() + "exit 0\n")
    before = digest(stock_hook)
    with pytest.raises(ValueError, match="recognized prek shim"):
        installer.replace_hook(stock_hook, before)
    assert digest(stock_hook) == before


@pytest.mark.parametrize(("admission_exit", "expected"), [(9, 9), (0, 1)])
def test_scoped_hook_refuses_failed_admission_or_missing_check(stock_hook, tmp_path, modules, admission_exit, expected):
    installer, _ = modules
    installer.replace_hook(stock_hook, digest(stock_hook))
    python = tmp_path / "python3"
    python.write_text(f"#!/bin/sh\nexit {admission_exit}\n")
    python.chmod(0o755)
    result = subprocess.run(  # noqa: S603 - run the disposable installed shim
        [stock_hook, "origin", "fixture"],
        input=b"fixture stream",
        env={"PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}", "TMPDIR": str(tmp_path), installer.SCOPE: HEAD},
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == expected
    assert (tmp_path / "replayed").exists() == (admission_exit == 0)
    assert not list(tmp_path.glob("hz-plugins-push.*"))


def stream_for(scope):
    return f"{scope.LOCAL} {HEAD} {scope.DESTINATION} {'0' * 40}\n".encode()


@pytest.mark.parametrize("kind", ["empty", "multi", "deleted", "malformed", "existing", "other-ref", "other-head"])
def test_scope_requires_one_exact_new_ref(tmp_path, modules, kind):
    _, scope = modules
    capture = tmp_path / "refs"
    correct = stream_for(scope)
    variants = {
        "empty": b"",
        "multi": correct + correct,
        "deleted": b"(delete) " + b"0" * 40 + b" " + scope.DESTINATION.encode() + b" " + HEAD.encode() + b"\n",
        "malformed": correct[:-1],
        "existing": correct.replace(b"0" * 40, b"b" * 40),
        "other-ref": correct.replace(scope.DESTINATION.encode(), b"refs/heads/main"),
        "other-head": correct.replace(HEAD.encode(), b"b" * 40),
    }
    capture.write_bytes(variants[kind])
    with pytest.raises(ValueError, match="exactly one new diagnostic"):
        scope.verify_stream(capture, HEAD)


def test_capture_requires_the_installed_wrapper_and_private_files(stock_hook, tmp_path, monkeypatch, modules):
    installer, scope = modules
    directory = tmp_path / "hz-plugins-push.fixture"
    directory.mkdir(mode=0o700)
    capture = directory / "refs"
    capture.write_bytes(stream_for(scope))
    capture.chmod(0o600)
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv(installer.REFS, str(capture))
    monkeypatch.setattr(scope, "hook_path", lambda: stock_hook)
    with pytest.raises(ValueError, match="wrapper first"):
        scope.capture_path()
    installer.replace_hook(stock_hook, digest(stock_hook))
    assert scope.capture_path() == capture
    capture.chmod(0o644)
    with pytest.raises(ValueError, match="permissions"):
        scope.capture_path()
    monkeypatch.delenv(installer.REFS)
    with pytest.raises(ValueError, match="complete ref stream"):
        scope.capture_path()


@pytest.fixture
def checkout(modules, monkeypatch):
    _, scope = modules
    diff = ("diff", "--name-status", "--no-renames")
    responses = {
        ("symbolic-ref", "HEAD"): scope.LOCAL,
        ("rev-parse", "HEAD"): HEAD,
        ("status", "--porcelain", "--untracked-files=all"): "",
        ("rev-parse", "refs/remotes/origin/main"): scope.BASE,
        ("rev-list", "--parents", "-n", "1", HEAD): f"{HEAD} {scope.DIAGNOSTIC}",
        ("rev-list", "--parents", "-n", "1", scope.DIAGNOSTIC): f"{scope.DIAGNOSTIC} {scope.BASE}",
        (*diff, scope.BASE, scope.DIAGNOSTIC, "--"): f"M\t{scope.WORKFLOW}\nM\t{scope.PRESENTATION_TEST}",
        (*diff, scope.DIAGNOSTIC, HEAD, "--"): "\n".join(scope.SUPPORT_CHANGES),
        ("rev-parse", f"{HEAD}:{scope.WORKFLOW}"): scope.WORKFLOW_BLOB,
        ("diff", "--check", scope.BASE, HEAD): "",
        (
            "-c",
            "credential.helper=",
            "-c",
            "http.extraHeader=",
            "ls-remote",
            "--exit-code",
            "--refs",
            scope.REMOTE,
            "refs/heads/main",
        ): f"{scope.BASE}\trefs/heads/main",
    }
    monkeypatch.setattr(scope, "git", lambda *args: responses[args])
    return scope, responses


def test_admission_requires_fresh_main_and_exact_checkout(tmp_path, checkout):
    scope, responses = checkout
    capture = tmp_path / "refs"
    capture.write_bytes(stream_for(scope))
    scope.admit(capture, HEAD, ["origin", scope.REMOTE])
    key = next(key for key in responses if "ls-remote" in key)
    responses[key] = "stale"
    with pytest.raises(ValueError, match="Remote main changed"):
        scope.admit(capture, HEAD, ["origin", scope.REMOTE])


@pytest.mark.parametrize(
    ("key", "new_value", "reason"),
    [
        (("symbolic-ref", "HEAD"), "refs/heads/main", "local branch"),
        (("rev-parse", "HEAD"), "b" * 40, "reviewed head"),
        (("status", "--porcelain", "--untracked-files=all"), "M dirty", "must be clean"),
        (("rev-parse", "refs/remotes/origin/main"), "b" * 40, "local main pin"),
    ],
)
def test_checkout_refuses_mismatch(checkout, key, new_value, reason):
    scope, responses = checkout
    responses[key] = new_value
    with pytest.raises(ValueError, match=reason):
        scope.verify_checkout(HEAD)


def test_checkout_refuses_plugin_changes(checkout):
    scope, responses = checkout
    responses[("diff", "--name-status", "--no-renames", scope.DIAGNOSTIC, HEAD, "--")] += "\nM\tplugins/extra.py"
    with pytest.raises(ValueError, match="outside the diagnostic"):
        scope.verify_checkout(HEAD)


def test_checkout_refuses_unreviewed_workflow_bytes(checkout):
    scope, responses = checkout
    responses[("rev-parse", f"{HEAD}:{scope.WORKFLOW}")] = "b" * 40
    with pytest.raises(ValueError, match="workflow bytes changed"):
        scope.verify_checkout(HEAD)


def test_focused_checks_require_matching_prek_and_fixed_test_paths(tmp_path, checkout, monkeypatch):
    scope, _ = checkout
    capture = tmp_path / "refs"
    capture.write_bytes(stream_for(scope))
    names = {
        "PRE_COMMIT_FROM_REF": scope.BASE,
        "PRE_COMMIT_TO_REF": HEAD,
        "PRE_COMMIT_REMOTE_NAME": "origin",
        "PRE_COMMIT_REMOTE_URL": scope.REMOTE,
        "PRE_COMMIT_LOCAL_BRANCH": scope.LOCAL,
        "PRE_COMMIT_REMOTE_BRANCH": scope.DESTINATION,
    }
    for key, value in names.items():
        monkeypatch.setenv(key, value)
    commands = []
    monkeypatch.setattr(scope.subprocess, "run", lambda command, *, check: commands.append(command))
    scope.check(capture, HEAD)
    assert [command[command.index("pytest") + 1 :] for command in commands if "pytest" in command] == [
        (scope.TEST, scope.HOOK_TEST, "-q")
    ]
    assert capture.with_name("checked").is_file()
    monkeypatch.setenv("PRE_COMMIT_REMOTE_BRANCH", "refs/heads/main")
    with pytest.raises(ValueError, match="prek range"):
        scope.check(capture, HEAD)
