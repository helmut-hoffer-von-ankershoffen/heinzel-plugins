"""Local-maintainer pin checks for an installed focused pre-push companion.

The adjacent JSON pin is provisioned outside the candidate checkout by a local
maintainer. This design does not defend against a hostile same-UID process.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path


def clean_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    return env


def digest(path: Path) -> str:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{path}: expected regular file")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_executables(files: dict, hook_dir: Path, repo: Path) -> None:
    for name, item in files.items():
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ValueError(f"invalid {name} pin")
        path = Path(item["path"])
        if not path.is_absolute() or digest(path) != item["sha256"]:
            raise ValueError(f"{name} executable differs from its pin")
        if name in {"guard", "shim", "prek", "guard_python", "dispatcher_python"} and not path.stat().st_mode & 0o111:
            raise ValueError(f"{name} is not executable")
    if (
        Path(files["guard"]["path"]) != hook_dir / "pre-push.legacy"
        or Path(files["shim"]["path"]) != hook_dir / "pre-push"
    ):
        raise ValueError("pins do not name the installed hook files")
    if Path(files["trust"]["path"]).resolve() != Path(__file__).resolve():
        raise ValueError("active trust loader differs from its pin")
    for name, relative in (
        ("dispatcher", "scripts/focused_dispatch.py"),
        ("hook", "scripts/focused_hook.py"),
        ("materializer", "scripts/focused_materialize.py"),
    ):
        if digest(repo / relative) != files[name]["sha256"]:
            raise ValueError(f"active candidate {name} differs from its pin")


def _read_pin(hook_dir: Path, repo: Path, remote_name: str, remote_url: str) -> dict:
    pin_path = hook_dir / "focused-policy.json"
    info = pin_path.lstat()
    if pin_path.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError("focused policy pin must be private, owned and regular")
    pin = json.loads(pin_path.read_text())
    required = {"repo", "remote_name", "remote_url", "destination", "policy_commit", "files"}
    if not isinstance(pin, dict) or set(pin) != required:
        raise ValueError("invalid focused policy pin")
    if pin["repo"] != str(repo.resolve()) or pin["remote_name"] != remote_name or pin["remote_url"] != remote_url:
        raise ValueError("repository or remote does not match the pin")
    return pin


def load(hook_dir: Path, repo: Path, remote_name: str, remote_url: str, old: str, new: str, role: str):
    pin = _read_pin(hook_dir, repo, remote_name, remote_url)
    files = pin["files"]
    if not isinstance(files, dict) or set(files) != {
        "guard",
        "shim",
        "prek",
        "guard_python",
        "dispatcher_python",
        "policy",
        "dispatcher",
        "trust",
        "hook",
        "materializer",
    }:
        raise ValueError("incomplete executable pins")
    _check_executables(files, hook_dir, repo)
    version = subprocess.check_output([files["prek"]["path"], "--version"], env=clean_env(), text=True, timeout=30)
    if not version.startswith("prek 0.5.7 "):
        raise ValueError("unsupported prek version")
    if role not in {"guard", "dispatcher"}:
        raise ValueError("unknown trust role")
    if Path(sys.executable).resolve() != Path(files[f"{role}_python"]["path"]).resolve():
        raise ValueError("unexpected interpreter")
    policy_path = Path(files["policy"]["path"])
    spec = importlib.util.spec_from_file_location("trusted_focused_policy", policy_path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load pinned policy")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return pin, module.plan(repo, old, new, pin["policy_commit"])
