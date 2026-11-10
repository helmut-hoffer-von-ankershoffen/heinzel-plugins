"""Run the fixed reviewed plan; the installed legacy guard validates the transaction.

This dispatcher is opt-in. Its installed companion must see Git's original
pre-push stdin and veto multi-ref transactions before prek dispatches this script.
The independent pin is a local-maintainer trust boundary, not a security boundary
against hostile processes running as the same OS user.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def git(*args: str) -> str:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    return subprocess.check_output(["git", "--no-replace-objects", *args], env=env, text=True, timeout=30).strip()


def run(command: list[str], cwd: Path) -> None:
    blocked = ("GIT_", "PYTHON", "PYTEST", "PRE_COMMIT_", "PLUGIN_", "PIP_", "HZ_", "UV_")
    env = {key: value for key, value in os.environ.items() if not key.startswith(blocked)}
    env.pop("VIRTUAL_ENV", None)
    env.pop("NODE_OPTIONS", None)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["UV_OFFLINE"] = "1"
    env["PLUGIN_SOURCE_ROOT"] = str(cwd)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(command, cwd=cwd, env=env, check=True, timeout=600)  # noqa: S603 - fixed reviewed plan, no shell


def load_installed_trust(hook_dir: Path):
    spec = importlib.util.spec_from_file_location("installed_focused_trust", hook_dir / "focused_trust.py")
    if spec is None or spec.loader is None:
        raise ValueError("installed focused trust loader is missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dispatch(mode: str = "all") -> None:
    if mode not in {"all", "tooling", "owners"}:
        raise ValueError("invalid focused check mode")
    repo = Path(git("rev-parse", "--show-toplevel")).resolve()
    hook_dir = Path(git("rev-parse", "--git-path", "hooks")).resolve()
    trust = load_installed_trust(hook_dir)
    # The remote name and URL were checked against the same independently pinned
    # values by pre-push.legacy with Git's unmodified transaction input.
    pin = __import__("json").loads((hook_dir / "focused-policy.json").read_text())
    checked_pin, plan = trust.load(
        hook_dir,
        repo,
        pin["remote_name"],
        pin["remote_url"],
        os.environ.get("PRE_COMMIT_FROM_REF", ""),
        os.environ.get("PRE_COMMIT_TO_REF", ""),
        "dispatcher",
    )
    materializer_spec = importlib.util.spec_from_file_location(
        "installed_focused_materialize", checked_pin["files"]["materializer"]["path"]
    )
    if materializer_spec is None or materializer_spec.loader is None:
        raise ValueError("installed materializer is missing")
    materializer = importlib.util.module_from_spec(materializer_spec)
    materializer_spec.loader.exec_module(materializer)
    with materializer.materialized(repo, os.environ["PRE_COMMIT_TO_REF"]) as tree:
        uv = ["uv", "run", "--no-env-file", "--project", str(tree), "--frozen", "--no-build", "--group", "tooling"]
        if mode in {"all", "tooling"}:
            run([*uv, "ruff", "check", "scripts", "tests", "src/heinzel_plugin_tools"], tree)
            run([*uv, "ruff", "format", "--check", "scripts", "tests", "src/heinzel_plugin_tools"], tree)
            run([*uv, "--extra", "checks", "pytest", *plan.tooling, "-q", "-n", "2"], tree)
            run([*uv, "python", "scripts/tools.py", "run", "actionlint"], tree)
            run([*uv, "zizmor", "--offline", "--quiet", ".github"], tree)
        if mode in {"all", "owners"}:
            owner_code = (
                "import sys; from heinzel_plugin_tools.cli import projects,check; "
                "p=next(x for x in projects() if x.name==sys.argv[1]); "
                "check(p,None,fast=True,test_targets=tuple(sys.argv[2:]),frontend=False)"
            )
            for owner, tests in plan.owners:
                run([*uv, "python", "-c", owner_code, owner, *tests], tree)
            for owner, test_path in plan.frontend:
                web = tree / "plugins" / owner / "web"
                build = str(web / "build.py")
                run(["uv", "run", "--no-env-file", "--no-project", "--script", build, "run", "typecheck"], tree)
                relative = str(Path(test_path).relative_to(Path("plugins") / owner / "web"))
                run(
                    [
                        "uv",
                        "run",
                        "--no-env-file",
                        "--no-project",
                        "--script",
                        build,
                        "run",
                        "test",
                        "--",
                        relative,
                        "--maxWorkers=2",
                    ],
                    tree,
                )


if __name__ == "__main__":
    try:
        dispatch(sys.argv[1] if len(sys.argv) == 2 else "all")
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"focused check refused: {exc}", file=sys.stderr)
        sys.exit(1)
