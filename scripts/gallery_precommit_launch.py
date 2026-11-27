"""Provision this launcher in trusted Git metadata, outside candidate source.

An authorized local maintainer installs an executable `gallery-precommit` shim
there that invokes this script with a trusted Python in isolated mode. The
adjacent pin is provisioned separately from the candidate commit and policy.
"""

import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

# Load only the independently pinned package before executing the exact index checker.
CHECKER_BOOTSTRAP = (
    "import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_path(sys.argv.pop(1),run_name='__main__')"
)
PIN_NAME = "gallery-precommit.json"


def require(condition):
    if not condition:
        raise ValueError("untrusted gallery pre-commit transaction")


def regular(path, *, private=False):
    require(path.is_absolute() and path.resolve() == path)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode))
    if private:
        require(info.st_uid == os.geteuid() and info.st_mode & 0o077 == 0)
    return path


def digest(path):
    with regular(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def runtime_files(runtime):
    """Bind all checked-in package data and scripts, refusing alternate importables."""
    source = runtime / "src"
    require(source.is_dir() and source.resolve() == source)
    require({path.name for path in source.iterdir()} == {"heinzel_plugin_tools"})
    package = source / "heinzel_plugin_tools"
    require(package.is_dir() and package.resolve() == package)
    files = {}
    for path in sorted(package.rglob("*")):
        require(not path.is_symlink() and path.name != "__pycache__")
        if not path.is_dir():
            files[path.relative_to(runtime).as_posix()] = digest(path)
    for relative in ("scripts/gallery_index_guard.py", "scripts/check_confidentiality.py"):
        files[relative] = digest(runtime / relative)
    return files


def authorize(hooks, repo, phase):
    require(os.environ.get("HZ_TRUSTED_GALLERY_PRECOMMIT") == "1")
    require(
        not any(
            os.environ.get(name)
            for name in (
                "HZ_TRUSTED_FOCUSED_PUSH",
                "PRE_COMMIT_FROM_REF",
                "PRE_COMMIT_TO_REF",
                "SKIP",
                "PREK_SKIP",
                "GIT_DIR",
                "GIT_WORK_TREE",
                "GIT_COMMON_DIR",
            )
        )
    )
    pin = json.loads(regular(hooks / PIN_NAME, private=True).read_text())
    require(pin["format"] == 1 and pin["repository"] == str(repo))
    require(digest(repo / ".pre-commit-config.yaml") == pin["hook_config_sha256"])
    require(digest(hooks / "pre-commit.gallery-stock") == pin["stock_sha256"])
    git_binary = regular(Path(pin["git"]))
    require(git_binary.name == "git" and digest(git_binary) == pin["git_sha256"])
    require(str(Path(sys.executable).resolve()) == pin["interpreter"])
    runtime = Path(pin["runtime"])
    require(runtime.is_absolute() and runtime.resolve() == runtime and not runtime.is_relative_to(repo))
    require(runtime_files(runtime) == pin["runtime_files"])
    policy = regular(Path(pin["policy"]), private=True)
    require(not policy.is_relative_to(repo) and digest(policy) == pin["policy_sha256"])
    terms = regular(Path(pin["terms"]), private=True)
    require(not terms.is_relative_to(repo))
    scratch = Path(pin["scratch"])
    require(scratch.is_absolute() and scratch.resolve() == scratch and scratch.is_dir())
    require(not scratch.is_relative_to(repo) and scratch.stat().st_mode & 0o077 == 0)
    receipt = Path(pin["receipt"])
    require(receipt.parent == scratch)
    env = {
        "PATH": str(git_binary.parent),
        "HOME": str(scratch),
        "TMPDIR": str(scratch),
        "CONFIDENTIAL_TERMS_FILE": str(terms),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    if index := os.environ.get("GIT_INDEX_FILE"):
        env["GIT_INDEX_FILE"] = index

    def git(*args):
        return subprocess.check_output(
            [str(git_binary), "--no-replace-objects", "-C", str(repo), *args],
            env=env,
            text=True,
            timeout=15,
            stderr=subprocess.PIPE,
        ).rstrip("\n")

    common = git("rev-parse", "--path-format=absolute", "--git-common-dir")
    require(Path(common) / "hooks" == hooks)
    require(not git("ls-files", "--others", "--exclude-standard", "-z"))
    if phase == "after":
        proof = json.loads(regular(receipt, private=True).read_text())
        require(proof["format"] == 1 and proof["policy_sha256"] == pin["policy_sha256"])
        require(proof["head"] == git("rev-parse", "HEAD^{commit}") and proof["tree"] == git("write-tree"))
        return 0
    require(not receipt.exists() and not receipt.is_symlink())
    if phase == "before":
        return 0
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            CHECKER_BOOTSTRAP,
            str(runtime / "src"),
            str(runtime / "scripts/gallery_index_guard.py"),
            "--repository",
            str(repo),
            "--policy",
            str(policy),
            "--policy-sha256",
            pin["policy_sha256"],
            "--receipt",
            str(receipt),
        ],
        cwd=repo,
        env=env,
        timeout=120,
        check=False,
    ).returncode


def main():
    try:
        require(sys.flags.isolated and len(sys.argv) in {2, 3})
        phase = sys.argv[2] if len(sys.argv) == 3 else "owning"
        require(phase in {"before", "owning", "after"})
        os.umask(0o077)
        return authorize(Path(__file__).resolve().parent, Path(sys.argv[1]).resolve(strict=True), phase)
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print("Trusted gallery pre-commit authorization refused.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
