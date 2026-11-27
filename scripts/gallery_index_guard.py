"""Opt-in prototype for a trusted controller's gallery-only pre-commit check.

The installed hook is deliberately unchanged. A future controller must load this
code, Git and its scanner from an independently pinned environment, supply the
approved policy digest, and leave the other normal hooks in the commit transaction.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from heinzel_plugin_tools import capture
from heinzel_plugin_tools.capture_linux import IMAGE, PLATFORM, configured_terms
from heinzel_plugin_tools.cli import plan as hosted_plan
from heinzel_plugin_tools.cli import projects, supports_core

OWNER = r"heinzel-[a-z][a-z0-9-]*"
GALLERY_PATH = re.compile(rf"plugins/({OWNER})/docs/assets/screenshots/([a-z][a-z0-9.-]*)")
METADATA_PATH = re.compile(rf"plugins/{OWNER}/pyproject\.toml")
OBJECT_ID = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")
MAX_BLOB = 20 * 1024 * 1024
MAX_OWNER_SNAPSHOT = 64 * 1024 * 1024


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def git(root, *args):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS="0")
    return subprocess.check_output(
        ["git", "--no-replace-objects", "-C", str(root), *args], env=env, stderr=subprocess.PIPE, timeout=30
    )


def frozen_index(root):
    require(Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel").rstrip(b"\n"))) == root, "require worktree root")
    require(
        not any(os.environ.get(key) for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR")), "Git context override"
    )
    require(not any(os.environ.get(key) for key in ("SKIP", "PREK_SKIP")), "hook skip override")
    index = Path(os.fsdecode(git(root, "rev-parse", "--path-format=absolute", "--git-path", "index").rstrip(b"\n")))
    supplied = os.environ.get("GIT_INDEX_FILE")
    require(not supplied or (root / supplied).resolve() == index, "unsupported alternate Git index")
    require(index.is_file() and not index.is_symlink(), "invalid Git index")
    merge_head = git(root, "rev-parse", "--path-format=absolute", "--git-path", "MERGE_HEAD").rstrip(b"\n")
    require(not Path(os.fsdecode(merge_head)).exists(), "merge commit needs standard checks")
    head = git(root, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    tree = git(root, "write-tree").decode().strip()
    require(OBJECT_ID.fullmatch(head) and OBJECT_ID.fullmatch(tree), "invalid HEAD or index tree")
    return head, tree, index


def classify_index(root, head, tree):
    fields = git(root, "diff", "--no-ext-diff", "--raw", "-z", "--no-renames", head, tree, "--").split(b"\0")[:-1]
    require(fields and len(fields) % 2 == 0, "empty or invalid staged changes")
    owners = {}
    for raw, path in zip(fields[::2], fields[1::2], strict=True):
        old_mode, new_mode, _old, _new, status = raw.decode("ascii").split()
        item = GALLERY_PATH.fullmatch(path.decode("utf-8"))
        require(item and (old_mode, new_mode, status) == (":100644", "100644", "M"), "requires standard owner checks")
        owner, name = item.groups()
        owners.setdefault(owner, set()).add(name)
    return owners


def external(root, path):
    require(
        path.is_absolute() and path.resolve() == path and not path.is_relative_to(root), "require external exact path"
    )
    return path


def read_policy(root, path, pinned_sha, head, tree):
    require(DIGEST.fullmatch(pinned_sha), "require controller-pinned policy digest")
    content = capture.regular_bytes(external(root, path), 256 * 1024)
    require(sha256(content) == pinned_sha, "policy digest differs")
    policy = json.loads(content)
    require(policy["format"] == 1 and policy["repository"] == str(root), "policy scope differs")
    require(policy["head"] == head and policy["tree"] == tree, "policy HEAD or index tree differs")
    require(OBJECT_ID.fullmatch(policy["hosted_base"]), "require exact hosted base")
    require(git(root, "cat-file", "-t", policy["hosted_base"]) == b"commit\n", "require hosted base commit")
    require(DIGEST.fullmatch(policy["public_core_sha256"]), "require public Core wheel digest")
    require(policy["browser_image"] == IMAGE and policy["capture_platform"] == PLATFORM, "renderer differs")
    require(sha256(configured_terms().encode()) == policy["scanner_terms_sha256"], "scanner policy differs")
    return policy


def tree_entries(root, tree, path):
    entries = {}
    for row in git(root, "ls-tree", "-r", "-z", "-l", tree, "--", path).split(b"\0")[:-1]:
        metadata, name = row.split(b"\t", 1)
        mode, kind, object_id, size = metadata.decode("ascii").split()
        entries[name.decode("utf-8")] = (mode, kind, object_id, size)
    return entries


def materialize(root, target, entries, names):
    total = 0
    for name in sorted(names):
        mode, kind, object_id, size = entries[name]
        require(mode in {"100644", "100755"} and kind == "blob", "snapshot requires regular blobs")
        total += int(size)
        require(int(size) <= MAX_BLOB and total <= MAX_OWNER_SNAPSHOT, "snapshot exceeds size limit")
        path = capture.safe_path(target, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(git(root, "cat-file", "blob", object_id))


def validate_draft(root, project, definition, authorization, policy):
    approval_bytes = capture.regular_bytes(external(root, Path(authorization["review"])), 256 * 1024)
    require(sha256(approval_bytes) == authorization["review_sha256"], "independent review differs")
    approval = json.loads(approval_bytes)
    require(
        approval["decision"] == "approve"
        and approval["owner"] == project.name
        and approval["public_core_sha256"] == policy["public_core_sha256"]
        and approval["draft_sha256"] == authorization["draft_sha256"]
        and approval["checksum_list_sha256"] == authorization["checksum_list_sha256"],
        "independent visual/privacy approval required",
    )
    source = external(root, Path(authorization["draft"]))
    require(source.is_dir(), "approved private draft missing")
    names = {capture.DRAFT_MANIFEST, "index.html"}
    scenes = [scene["name"] for scene in definition["scenes"]]
    names.update(f"{scene}.{extension}" for scene in scenes for extension in ("png", "txt", "scan.txt"))
    require({path.name for path in source.iterdir()} == names, "approved draft inventory differs")
    target = project / capture.DRAFT
    target.mkdir(parents=True)
    checksums = []
    for name in sorted(names):
        data = capture.regular_bytes(capture.safe_path(source, name), capture.MAX_IMAGE)
        checksums.append(f"{sha256(data)}  ./{name}\n")
        (target / name).write_bytes(data)
        if name.endswith(".png") or (name.endswith(".txt") and not name.endswith(".scan.txt")):
            require(data == (project / capture.OUTPUT / name).read_bytes(), "index differs from approved scene bytes")
    require(sha256("".join(checksums).encode()) == authorization["checksum_list_sha256"], "approved bundle differs")
    manifest_bytes = (target / capture.DRAFT_MANIFEST).read_bytes()
    require(sha256(manifest_bytes) == authorization["draft_sha256"], "approved manifest differs")
    manifest = json.loads(manifest_bytes)
    require(
        manifest["plugin"] == project.name and manifest["core_version"] == policy["core_version"],
        "draft identity differs",
    )
    require(
        manifest["inputs_sha256"] == json.loads((project / capture.MANIFEST).read_bytes())["inputs_sha256"],
        "draft inputs differ from the indexed capture",
    )
    capture.draft_artifacts(project, definition, manifest)
    return len(scenes)


def validate_owner(root, tree, owner, changed, snapshot, policy, metadata):
    prefix = f"plugins/{owner}/"
    project = snapshot / prefix
    entries = {name.removeprefix(prefix): data for name, data in tree_entries(root, tree, prefix).items()}
    materialize(root, project, entries, {capture.PLAN.as_posix()})
    unchecked = capture.load_definition(project)
    require(isinstance(unchecked, dict), "indexed scene definition missing")
    if (bootstrap := unchecked.get("bootstrap")) is not None:
        require(isinstance(bootstrap, str) and bootstrap in entries, "require indexed fixture script")
        materialize(root, project, entries, {bootstrap})
    definition = capture.read_plan(project)
    expected = {capture.MANIFEST.name, "index.html"}
    expected.update(f"{scene['name']}.{suffix}" for scene in definition["scenes"] for suffix in ("png", "txt"))
    require(changed <= expected, "unlisted gallery artifact needs standard owner checks")
    output = capture.OUTPUT.as_posix() + "/"
    require(
        {name for name in entries if name.startswith(output)} == {output + name for name in expected},
        "indexed gallery is incomplete or has extra files",
    )
    require(supports_core(metadata, policy["core_version"]), "Core version is incompatible")
    names = set(capture.ui_inputs(project, definition, source_files=list(entries)))
    names.update({capture.README_FILE, *(output + name for name in expected)})
    materialize(root, project, entries, names)
    capture.check_capture(project, source_files=list(entries))
    manifest = json.loads((project / capture.MANIFEST).read_bytes())
    require(manifest["core_version"] == policy["core_version"], "indexed Core version differs")
    scenes = validate_draft(root, project, definition, policy["owners"][owner], policy)
    return {
        "scenes": scenes,
        "manifest_sha256": sha256((project / capture.MANIFEST).read_bytes()),
        "private_bundle_sha256": policy["owners"][owner]["checksum_list_sha256"],
        "independent_review_sha256": policy["owners"][owner]["review_sha256"],
    }


def verify(root, policy_path, pinned_sha):
    initial = frozen_index(root)
    head, tree, _index = initial
    owners = classify_index(root, head, tree)
    policy = read_policy(root, policy_path, pinned_sha, head, tree)
    require(set(policy["owners"]) == owners.keys(), "require exact approvals for every changed owner")
    with tempfile.TemporaryDirectory(prefix="gallery-index-") as temporary:
        snapshot = Path(temporary)
        entries = tree_entries(root, tree, "plugins")
        metadata = {name for name in entries if METADATA_PATH.fullmatch(name)}
        materialize(root, snapshot, entries, metadata)
        inventory = {project.name: project for project in projects(snapshot)}
        require(owners.keys() <= inventory.keys(), "unknown staged gallery owner")
        require(
            all(inventory[owner].directory == snapshot / "plugins" / owner for owner in owners),
            "staged owner disagrees with indexed distribution metadata",
        )
        validated = {
            owner: validate_owner(root, tree, owner, changed, snapshot, policy, inventory[owner])
            for owner, changed in sorted(owners.items())
        }
        changes = git(root, "diff", "--no-ext-diff", "--name-only", "-z", "--no-renames", policy["hosted_base"], tree)
        selection = hosted_plan(changes.decode("utf-8").split("\0")[:-1], list(inventory.values()), snapshot)
    require(frozen_index(root) == initial, "HEAD or index changed during verification")
    hosted_owners = [item["name"] for item in selection["include"]]
    require(set(owners) <= set(hosted_owners), "hosted plan omitted a staged owner")
    return {
        "format": 1,
        "head": head,
        "tree": tree,
        "policy_sha256": pinned_sha,
        "public_core_sha256": policy["public_core_sha256"],
        "owners": validated,
        "hosted_required": {
            "base": policy["hosted_base"],
            "tooling": selection["tooling"],
            "owners": hosted_owners,
            "per_owner_jobs": ["plugin", "gallery"],
            "requires_exact_hosted_job_inventory": True,
            "recompute_for_tested_merge": True,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--policy-sha256", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.repository.resolve(strict=True)
        receipt = external(root, args.receipt)
        record = verify(root, args.policy, args.policy_sha256)
        with receipt.open("x", encoding="utf-8") as file:
            json.dump(record, file, indent=2)
            file.write("\n")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        # Private paths, disallowed scene text and Git stderr are never echoed.
        parser.exit(1, "Gallery index proof refused. Use the standard owner checks or repair the private proof.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
