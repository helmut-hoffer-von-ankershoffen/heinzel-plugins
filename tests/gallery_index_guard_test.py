"""Exercise the prototype on tiny staged Git trees and fictional private receipts."""

import importlib.util
import json
from pathlib import Path

import pytest

from heinzel_plugin_tools import capture

spec = importlib.util.spec_from_file_location(
    "gallery_index_guard", Path(__file__).parents[1] / "scripts/gallery_index_guard.py"
)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
OWNER = "heinzel-demo"
TERMS = "SyntheticNeverDisclose"
CORE = "0.9.56"
PLAN = {
    "format": 1,
    "bootstrap": "docs/screenshot_fixture.py",
    "scenes": [
        {"name": "page", "surface": "ui", "caption": "Fictional page"},
        {"name": "sheet", "surface": "ui", "caption": "Fictional sheet"},
        {"name": "result", "surface": "cli", "caption": "Fictional result", "command": ["demo", "list"]},
    ],
}


def json_file(path, value):
    path.write_text(json.dumps(value) + "\n")
    return guard.sha256(path.read_bytes())


@pytest.fixture
def case(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIDENTIAL_TERMS", TERMS)
    for name in ("GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "SKIP", "PREK_SKIP"):
        monkeypatch.delenv(name, raising=False)
    root = (tmp_path / "repository").resolve()
    root.mkdir()
    guard.git(root, "init", "--quiet", "--template=")
    guard.git(root, "config", "--local", "user.name", "Example Reviewer")
    guard.git(root, "config", "--local", "user.email", "reviewer@example.com")
    project = root / "plugins" / OWNER
    gallery = project / capture.OUTPUT
    gallery.mkdir(parents=True)
    (project / "src").mkdir()
    (project / "src" / "gallery.css").write_text("/* fixed fictional fixture */\n")
    (project / "docs" / "screenshot_fixture.py").write_text("# fictional fixture\n")
    json_file(project / capture.PLAN, PLAN)
    shots = capture.expected_shots(PLAN)
    meta = (
        '[project]\nname = "heinzel-demo"\nversion = "0.1.0"\n'
        'dependencies = ["heinzel>=0.9.56,<0.10"]\n'
        '[project.entry-points."heinzel.modules"]\ndemo = "demo:module"\n'
        "[tool.heinzel.catalog]\n"
    )
    # TOML and the catalog generator give the same scene inventory.
    for shot in shots:
        meta += "[[tool.heinzel.catalog.screenshots]]\n"
        meta += "".join(f"{field} = {json.dumps(value)}\n" for field, value in shot.items())
    (project / "pyproject.toml").write_text(meta)
    (project / "README.md").write_text(capture.readme_gallery("# Example\n", shots))

    manifest = {
        "format": 2,
        "plugin": OWNER,
        "core_version": "0.9.55",
        "inputs_sha256": capture.input_digest(
            project, PLAN, source_files=["src/gallery.css", "docs/screenshot_fixture.py"]
        ),
        "images": {},
        "transcripts": {},
    }
    for scene, shot in zip(PLAN["scenes"], shots, strict=True):
        png = b"\x89PNG\r\n\x1a\n" + scene["name"].encode()
        text = b"Fictional content.\n"
        (project / shot["path"]).write_bytes(png)
        (gallery / f"{scene['name']}.txt").write_bytes(text)
        manifest["images"][shot["path"]] = guard.sha256(png)
        manifest["transcripts"][f"{scene['name']}.txt"] = guard.sha256(text)
    json_file(project / capture.MANIFEST, manifest)
    (gallery / "index.html").write_text(capture.preview_document(OWNER, PLAN["scenes"], "0.9.55"))
    guard.git(root, "add", ".")
    guard.git(root, "commit", "--quiet", "-m", "Synthetic base")
    hosted_base = guard.git(root, "rev-parse", "HEAD").decode().strip()
    peer = root / "plugins" / "heinzel-peer"
    peer.mkdir()
    (peer / "pyproject.toml").write_text(meta.replace("heinzel-demo", "heinzel-peer"))
    (root / "scripts").mkdir()
    (root / "scripts" / "tool.py").write_text("# committed shared scope\n")
    guard.git(root, "add", ".")
    guard.git(root, "commit", "--quiet", "-m", "Synthetic composition")

    manifest["core_version"] = CORE
    json_file(project / capture.MANIFEST, manifest)
    (gallery / "index.html").write_text(capture.preview_document(OWNER, PLAN["scenes"], CORE))
    guard.git(root, "add", ".")
    draft = root.parent / "approved-draft"
    draft.mkdir()
    sidecars = {}
    for scene in PLAN["scenes"]:
        name = scene["name"]
        for suffix in ("png", "txt"):
            (draft / f"{name}.{suffix}").write_bytes((gallery / f"{name}.{suffix}").read_bytes())
        sidecars[f"{name}.scan.txt"] = guard.sha256(b"Fictional sidecar.\n")
        (draft / f"{name}.scan.txt").write_bytes(b"Fictional sidecar.\n")
    (draft / "index.html").write_bytes((gallery / "index.html").read_bytes())
    json_file(
        draft / "draft.json",
        {
            "plugin": OWNER,
            "core_version": CORE,
            "inputs_sha256": manifest["inputs_sha256"],
            "scan_text": sidecars,
            "images": {Path(path).name: digest for path, digest in manifest["images"].items()},
        },
    )
    review = root.parent / "review.json"
    policy_path = root.parent / "policy.json"
    head, tree, _index = guard.frozen_index(root)
    policy = {
        "format": 1,
        "repository": str(root),
        "head": head,
        "tree": tree,
        "hosted_base": hosted_base,
        "core_version": CORE,
        "public_core_sha256": "a" * 64,
        "browser_image": guard.IMAGE,
        "capture_platform": guard.PLATFORM,
        "scanner_terms_sha256": guard.sha256(f"{TERMS}\n".encode()),
        "owners": {},
    }
    return root, project, draft, review, policy_path, policy


def pin_case(case):
    root, _project, draft, review, path, policy = case
    manifest = guard.sha256((draft / "draft.json").read_bytes())
    checksums = "".join(f"{guard.sha256(file.read_bytes())}  ./{file.name}\n" for file in sorted(draft.iterdir()))
    bundle = guard.sha256(checksums.encode())
    review_sha = json_file(
        review,
        {
            "owner": OWNER,
            "decision": "approve",
            "draft_sha256": manifest,
            "checksum_list_sha256": bundle,
            "public_core_sha256": policy["public_core_sha256"],
        },
    )
    policy["owners"][OWNER] = {
        "review": str(review),
        "review_sha256": review_sha,
        "draft": str(draft),
        "draft_sha256": manifest,
        "checksum_list_sha256": bundle,
    }
    return root, path, json_file(path, policy)


def test_exact_index_ignores_dirty_working_copy_and_records_hosted_obligation(case):
    root, path, digest = pin_case(case)
    _, project, *_ = case
    (project / capture.MANIFEST).write_text("Unstaged corruption.")
    proof = guard.verify(root, path, digest)
    assert proof["owners"][OWNER]["scenes"] == 3
    assert list(proof["owners"]) == [OWNER]
    assert proof["hosted_required"]["owners"] == [OWNER, "heinzel-peer"]
    assert proof["hosted_required"]["tooling"] is True
    assert proof["hosted_required"]["per_owner_jobs"] == ["plugin", "gallery"]
    assert proof["hosted_required"]["requires_exact_hosted_job_inventory"] is True
    assert proof["hosted_required"]["recompute_for_tested_merge"] is True


@pytest.mark.parametrize("variant", ["source", "readme", "metadata", "new", "deleted", "mode", "sidecar"])
def test_mixed_or_unreviewed_path_refuses_narrow_route(case, variant):
    root, project, *_ = case
    if variant in {"source", "readme", "metadata", "new", "sidecar"}:
        path = {
            "source": project / "src" / "gallery.css",
            "readme": project / "README.md",
            "metadata": project / "pyproject.toml",
            "new": project / capture.OUTPUT / "surprise.png",
            "sidecar": project / capture.OUTPUT / "page.scan.txt",
        }[variant]
        with path.open("ab") as file:
            file.write(b"\n")
        guard.git(root, "add", str(path))
    else:
        path = project / capture.OUTPUT / "page.png"
        if variant == "deleted":
            guard.git(root, "rm", "--quiet", str(path))
        else:
            guard.git(root, "update-index", "--chmod=+x", str(path))
    _, path, digest = pin_case(case)
    with pytest.raises(ValueError, match="standard owner checks"):
        guard.verify(root, path, digest)


def test_policy_hash_and_alternate_index_are_required(case, monkeypatch):
    root, path, digest = pin_case(case)
    with pytest.raises(ValueError, match="policy digest differs"):
        guard.verify(root, path, "b" * 64)
    monkeypatch.setenv("GIT_INDEX_FILE", str(root.parent / "another-index"))
    with pytest.raises(ValueError, match="unsupported alternate"):
        guard.verify(root, path, digest)


def test_sidecars_are_bound_and_rescanned_even_after_a_valid_approval(case):
    _, _, draft, *_ = case
    root, path, digest = pin_case(case)
    sidecar = draft / "page.scan.txt"
    sidecar.write_text(TERMS)
    with pytest.raises(ValueError, match="approved bundle differs"):
        guard.verify(root, path, digest)
    manifest_path = draft / "draft.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["scan_text"][sidecar.name] = guard.sha256(sidecar.read_bytes())
    json_file(manifest_path, manifest)
    root, path, digest = pin_case(case)
    with pytest.raises(ValueError, match="confidential"):
        guard.verify(root, path, digest)


def test_independent_approval_hash_is_required(case):
    root, path, digest = pin_case(case)
    _, _, _, review, *_ = case
    review.write_text('{"decision":"approve"}\n')
    with pytest.raises(ValueError, match="independent review differs"):
        guard.verify(root, path, digest)


def test_valid_index_manifest_cannot_substitute_an_unapproved_blob(case):
    root, project, _, _, _, policy = case
    transcript = project / capture.OUTPUT / "result.txt"
    transcript.write_text("Different but fictional content.\n")
    manifest_path = project / capture.MANIFEST
    manifest = json.loads(manifest_path.read_bytes())
    manifest["transcripts"][transcript.name] = guard.sha256(transcript.read_bytes())
    json_file(manifest_path, manifest)
    guard.git(root, "add", str(transcript), str(manifest_path))
    _, policy["tree"], _ = guard.frozen_index(root)
    root, path, digest = pin_case(case)
    with pytest.raises(ValueError, match="index differs from approved scene bytes"):
        guard.verify(root, path, digest)


def test_index_change_during_scan_refuses_receipt(case, monkeypatch):
    root, path, digest = pin_case(case)
    _, project, *_ = case
    original = guard.validate_draft

    def changed(*args):
        count = original(*args)
        readme = project / "README.md"
        with readme.open("ab") as file:
            file.write(b"changed during scan\n")
        guard.git(root, "add", str(readme))
        return count

    monkeypatch.setattr(guard, "validate_draft", changed)
    with pytest.raises(ValueError, match="HEAD or index changed"):
        guard.verify(root, path, digest)
