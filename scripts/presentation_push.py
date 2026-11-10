"""Admit one independently reviewed Plugins presentation diagnostic ref."""

import os
import re
import stat
import subprocess
import sys
from pathlib import Path

from install_push_hook import CAPTURE, REFS, SCOPE, hook_path, stock_source

BASE = "f94dbc0d5ecf18b605ed917317d91eb5144eec4f"
DIAGNOSTIC = "8417b22af875828f834463b8b21414dafbedcf09"
LOCAL = "refs/heads/fix/plugins-full-push-refs"
DESTINATION = "refs/heads/validation/plugins-presentation-prep"
REMOTE = "https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins.git"
WORKFLOW = ".github/workflows/ci.yml"
PRESENTATION_TEST = "tests/presentation_test.py"
HOOK_TEST = "tests/presentation_push_hook_test.py"
SUPPORT_CHANGES = {
    "M\t.pre-commit-config.yaml",
    "A\tscripts/install_push_hook.py",
    "A\tscripts/presentation_push.py",
    f"A\t{HOOK_TEST}",
}
TEST = PRESENTATION_TEST + "::test_only_exact_owning_path_text_changes_and_all_doctor_rows_statuses_and_details_remain"
UV = ("uv", "run", "--frozen", "--no-build", "--group", "tooling")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}, text=True, timeout=30
    ).strip()


def capture_path() -> Path:
    hook = hook_path()
    require(not hook.is_symlink(), "The installed hook must be the ordinary wrapper.")
    source = hook.read_text(encoding="utf-8")
    require(stock_source(source) != source and CAPTURE in source, "Install the reviewed full-ref wrapper first.")
    value = os.environ.get(REFS)
    require(bool(value), "The installed hook must capture the complete ref stream.")
    capture = Path(value)
    directory = capture.parent
    require(
        capture.is_absolute()
        and capture.name == "refs"
        and directory.name.startswith("hz-plugins-push.")
        and directory.parent.resolve() == Path(os.environ.get("TMPDIR") or "/tmp").resolve(),  # noqa: S108 - check the installer's private directory beneath its temp root
        "The ref capture is outside the installed hook's private directory.",
    )
    for path, mode in ((directory, stat.S_IFDIR | 0o700), (capture, stat.S_IFREG | 0o600)):
        details = path.lstat()
        require(
            details.st_mode == mode and details.st_uid == os.geteuid(),
            "The installed hook's capture permissions are invalid.",
        )
    return capture


def verify_stream(capture: Path, head: str) -> None:
    require(bool(re.fullmatch(r"[0-9a-f]{40}", head)), "Supply the independently reviewed diagnostic SHA.")
    expected = f"{LOCAL} {head} {DESTINATION} {'0' * 40}\n".encode()
    with capture.open("rb") as stream:
        require(
            stream.read(len(expected) + 1) == expected, "Expected exactly one new diagnostic ref at the reviewed SHA."
        )


def verify_checkout(head: str) -> None:
    require(git("symbolic-ref", "HEAD") == LOCAL, "The local branch is outside the diagnostic scope.")
    require(git("rev-parse", "HEAD") == head, "The checkout differs from the independently reviewed head.")
    require(not git("status", "--porcelain", "--untracked-files=all"), "The diagnostic checkout must be clean.")
    require(git("rev-parse", "refs/remotes/origin/main") == BASE, "The local main pin changed.")
    require(
        git("rev-list", "--parents", "-n", "1", head) == f"{head} {DIAGNOSTIC}"
        and git("rev-list", "--parents", "-n", "1", DIAGNOSTIC) == f"{DIAGNOSTIC} {BASE}",
        "The reviewed diagnostic ancestry changed.",
    )
    diff = ("diff", "--name-status", "--no-renames")
    require(
        set(git(*diff, BASE, DIAGNOSTIC, "--").splitlines()) == {f"M\t{WORKFLOW}", f"M\t{PRESENTATION_TEST}"}
        and set(git(*diff, DIAGNOSTIC, head, "--").splitlines()) == SUPPORT_CHANGES,
        "The ref includes changes outside the diagnostic and hook support.",
    )
    git("diff", "--check", BASE, head)


def admit(capture: Path, head: str, args: list[str]) -> None:
    require(args == ["origin", REMOTE], "The diagnostic remote differs from the reviewed repository.")
    require(not any(os.environ.get(name) for name in ("SKIP", "PREK_SKIP")), "Hook overrides are not allowed.")
    verify_stream(capture, head)
    verify_checkout(head)
    require(
        git(
            "-c",
            "credential.helper=",
            "-c",
            "http.extraHeader=",
            "ls-remote",
            "--exit-code",
            "--refs",
            REMOTE,
            "refs/heads/main",
        )
        == f"{BASE}\trefs/heads/main",
        "Remote main changed.",
    )


def check(capture: Path, head: str) -> None:
    verify_stream(capture, head)
    verify_checkout(head)
    expected = {
        "PRE_COMMIT_FROM_REF": BASE,
        "PRE_COMMIT_TO_REF": head,
        "PRE_COMMIT_REMOTE_NAME": "origin",
        "PRE_COMMIT_REMOTE_URL": REMOTE,
        "PRE_COMMIT_LOCAL_BRANCH": LOCAL,
        "PRE_COMMIT_REMOTE_BRANCH": DESTINATION,
    }
    require(
        all(os.environ.get(key) == value for key, value in expected.items()), "The prek range differs from Git's ref."
    )
    python_sources = ("scripts", "tests", "src/heinzel_plugin_tools")
    for command in (
        (*UV, "ruff", "check", *python_sources),
        (*UV, "ruff", "format", "--check", *python_sources),
        (*UV, "--extra", "checks", "pytest", TEST, HOOK_TEST, "-q"),
        (*UV, "python", "scripts/tools.py", "run", "actionlint", WORKFLOW),
        (*UV, "zizmor", "--offline", "--quiet", WORKFLOW),
        (*UV, "python", "scripts/check_confidentiality.py", "--text", DESTINATION),
        (*UV, "python", "scripts/check_confidentiality.py", "--messages", f"{BASE}..{head}"),
    ):
        subprocess.run(command, check=True)
    capture.with_name("checked").touch(exist_ok=False)


def main() -> None:
    head = os.environ.get(SCOPE, "")
    try:
        capture = capture_path()
        match sys.argv[1:]:
            case ["admit", *remote]:
                admit(capture, head, remote)
            case ["check"]:
                check(capture, head)
            case _:
                raise ValueError("Expected diagnostic admit or check.")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()
