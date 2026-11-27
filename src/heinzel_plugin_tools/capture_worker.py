"""Trusted canonical-worker storage bootstrap (no project imports)."""

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from heinzel_plugin_tools import capture, capture_linux
from heinzel_plugin_tools.privacy import CaptureError, regular_bytes, safe_path

FILE_LIMIT = 20 * 1024 * 1024
TOTAL_LIMIT = 256 * 1024 * 1024
FILE_COUNT = 10000


def inventory(path: Path) -> list[str]:
    """Read only the bounded parent-produced inventory."""
    names = json.loads(regular_bytes(path, 1024 * 1024))
    if not isinstance(names, list) or not names or len(names) > FILE_COUNT:
        raise CaptureError("Invalid canonical source inventory")
    if any(
        not isinstance(name, str)
        or not name
        or Path(name).is_absolute()
        or ".." in Path(name).parts
        or Path(name).as_posix() != name
        or set(Path(name).parts) & (capture.IGNORED | {"run-home", "cache", ".cache"})
        for name in names
    ) or len(set(names)) != len(names):
        raise CaptureError("Invalid canonical source inventory")
    return names


def fingerprints(root: Path, names: list[str]) -> dict[str, dict]:
    """Require every expected source to remain a bounded regular file."""
    if root.is_symlink() or not root.is_dir():
        raise CaptureError("Canonical worker project was replaced")
    total = 0
    result = {}
    for name in names:
        path = safe_path(root, name)
        data = regular_bytes(path, FILE_LIMIT)
        metadata = path.stat()
        if len(data) > FILE_LIMIT or metadata.st_nlink != 1:
            raise CaptureError("Canonical source must be a bounded unaliased regular file")
        total += len(data)
        if total > TOTAL_LIMIT:
            raise CaptureError("Canonical source snapshot exceeds transfer limit")
        result[name] = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "mode": stat.S_IMODE(metadata.st_mode),
            "uid": metadata.st_uid,
            "gid": metadata.st_gid,
        }
    return result


def reconcile(
    project: Path, shared: Path, names: list[str], expected: dict, shared_expected: dict, plan: dict, digest: str
) -> None:
    """Keep source in place and return only a complete validated draft."""
    if fingerprints(project, names) != expected or fingerprints(shared, names) != shared_expected:
        raise CaptureError("The isolated source snapshot differs from the owning screenshot inputs")
    if capture.input_digest(project, plan, source_files=names) != digest:
        raise CaptureError("The isolated source snapshot differs from the owning screenshot inputs")
    draft = safe_path(project, capture.DRAFT)
    if not draft.exists():
        return
    allowed = {capture.DRAFT_MANIFEST, "index.html"}
    allowed.update(f"{scene['name']}.{ext}" for scene in plan["scenes"] for ext in ("png", "txt", "scan.txt"))
    # Enumeration is bounded by the required output count; never walk generated trees.
    with os.scandir(draft) as entries:
        actual = set()
        for entry in entries:
            if entry.name not in allowed or not entry.is_file(follow_symlinks=False):
                raise CaptureError("Unexpected canonical draft material")
            if entry.stat(follow_symlinks=False).st_nlink != 1:
                raise CaptureError("Canonical draft files cannot be aliases")
            actual.add(entry.name)
    if actual != allowed:
        raise CaptureError("Incomplete canonical draft")
    capture_linux.copy_draft(project, shared, plan)


def run(argv: list[str], *, shared: Path = Path("/capture/project")) -> int:
    """Run on native storage without returning worker-generated directory trees."""
    names = inventory(shared.parent / "source-files.json")
    digest = regular_bytes(shared.parent / "source-digest.txt", 64).decode("ascii")
    manifest = json.loads(regular_bytes(shared.parent / "source-state.json", 4 * 1024 * 1024))
    if not isinstance(manifest, dict) or set(manifest) != set(names):
        raise CaptureError("Invalid canonical source state")
    # Record guest-visible ownership before copying or running project code.
    # A bind mount need not expose host IDs as the worker process IDs.
    shared_expected = fingerprints(shared, names)
    for name in names:
        state = manifest[name]
        if (
            not isinstance(state, dict)
            or set(state) != {"sha256", "mode"}
            or state["mode"] not in {0o644, 0o645, 0o654, 0o655, 0o744, 0o745, 0o754, 0o755}
            or not isinstance(state["sha256"], str)
            or len(state["sha256"]) != 64
        ):
            raise CaptureError("Invalid canonical source state")
        if any(shared_expected[name][key] != state[key] for key in ("sha256", "mode")):
            raise CaptureError("Canonical source state differs from parent snapshot")
    plan = capture.read_plan(shared)
    if capture.input_digest(shared, plan, source_files=names) != digest:
        raise CaptureError("Canonical source digest differs from parent inventory")
    command = list(argv)
    index = command.index("--project") + 1
    if command[index] != str(shared):
        raise CaptureError("Unexpected canonical worker project")
    with tempfile.TemporaryDirectory(prefix="hz-gallery-worker-", dir="/tmp") as temporary:
        project = Path(temporary) / "project"
        # Record the native allocation owner/group independently of copied files.
        # macOS inherits the parent group; Linux native /tmp uses the process
        # group (or an inherited setgid group), reflected in this new directory.
        allocation = Path(temporary).stat()
        expected = {name: {**manifest[name], "uid": allocation.st_uid, "gid": allocation.st_gid} for name in names}
        capture_linux.copy_snapshot(shared, project, names)
        if fingerprints(project, names) != expected or fingerprints(shared, names) != shared_expected:
            raise CaptureError("Canonical source state differs before execution")
        command[index] = str(project)
        result = subprocess.run(command, cwd=project, check=False)
        reconcile(project, shared, names, expected, shared_expected, plan, digest)
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
