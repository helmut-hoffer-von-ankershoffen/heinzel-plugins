"""A gallery is publishable only when an independent agent approved the exact image and transcript bytes."""

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from heinzel_plugin_tools import privacy

pytestmark = pytest.mark.unit

NAMES = ("overview", "tides", "terminal")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def draft(tmp_path):
    """A private draft folder with three images, their transcripts and a consistent review bundle."""
    folder = tmp_path / ".preview/screenshots/draft"
    folder.mkdir(parents=True)
    bundle = {
        "format": 1,
        "plugin": "heinzel-harbor",
        "core_version": "0.9.8",
        "inputs_sha256": "1" * 64,
        "definition": {"story": "fictional"},
        "screenshots": [],
        "images": {},
        "transcripts": {},
    }
    for name in NAMES:
        image = b"\x89PNG\r\n\x1a\nfictional " + name.encode()
        text = f"Fictional transcript for {name}\n".encode()
        (folder / f"{name}.png").write_bytes(image)
        (folder / f"{name}.txt").write_bytes(text)
        bundle["images"][f"{name}.png"] = digest(image)
        bundle["transcripts"][f"{name}.txt"] = digest(text)
        surface = "cli" if name == "terminal" else "ui"
        bundle["screenshots"].append(
            {"path": f"docs/assets/screenshots/{name}.png", "surface": surface, "caption": f"The {name} view"}
        )
    bundle["bundle_sha256"] = privacy.bundle_digest(bundle)
    return tmp_path, folder, bundle


def approval(bundle, **changes):
    review = {
        "format": 1,
        "bundle_sha256": privacy.bundle_digest(bundle),
        "reviewer": "Synthetic privacy agent",
        "decision": "approve",
        "checked_images": sorted(bundle["images"]),
        "checks": dict.fromkeys(privacy.CHECKS, True),
        "findings": [],
    }
    return review | changes


def resealed(bundle, **changes):
    changed = copy.deepcopy(bundle) | changes
    changed["bundle_sha256"] = privacy.bundle_digest(changed)
    return changed


def test_canonical_text_matches_the_commit_hooks():
    assert privacy.canonical_text("a  \r\nb\t\rc\n\n\n") == "a\nb\nc\n"
    assert privacy.canonical_text("  \n\n") == ""


@pytest.mark.parametrize("relative", ["/etc/passwd", "../outside", "docs/../../outside"])
def test_artifact_paths_cannot_leave_the_owning_project(tmp_path, relative):
    with pytest.raises(privacy.CaptureError, match="inside their owning project"):
        privacy.safe_path(tmp_path, relative)


def test_artifact_paths_refuse_to_follow_a_linked_component(tmp_path):
    (tmp_path / "real").mkdir()
    (tmp_path / "linked").symlink_to(tmp_path / "real")
    with pytest.raises(privacy.CaptureError, match="symbolic links"):
        privacy.safe_path(tmp_path, "linked/image.png")
    assert privacy.safe_path(tmp_path, "real/image.png") == tmp_path.resolve() / "real/image.png"


def test_atomic_text_replaces_a_file_and_refuses_a_linked_destination(tmp_path):
    target = tmp_path / "REVIEW.md"
    target.write_text("old")
    privacy.atomic_text(target, "new")
    assert target.read_text() == "new"
    assert [path.name for path in tmp_path.iterdir()] == ["REVIEW.md"]
    victim = tmp_path / "victim.txt"
    victim.write_text("untouched")
    link = tmp_path / "link.txt"
    link.symlink_to(victim)
    with pytest.raises(privacy.CaptureError, match="symbolic links"):
        privacy.atomic_text(link, "overwrite")
    assert victim.read_text() == "untouched"


def test_a_consistent_bundle_validates_against_its_files(draft):
    _, folder, bundle = draft
    privacy.validate_bundle(bundle, folder)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda b: b.pop("definition"), "format is invalid"),
        (lambda b: b.update(format=True), "format is invalid"),
        (lambda b: b.update(plugin="Harbor"), "provenance is invalid"),
        (lambda b: b.update(core_version="x" * 81), "provenance is invalid"),
        (lambda b: b.update(inputs_sha256="short"), "provenance is invalid"),
        (lambda b: b["images"].pop("tides.png"), "three to eight images"),
        (lambda b: b["screenshots"].pop(), "three to eight images"),
        (lambda b: b["transcripts"].pop("tides.txt"), "exact transcript"),
        (lambda b: b["screenshots"][0].update(surface="mobile"), "captions and paths are invalid"),
        (lambda b: b["screenshots"][0].update(caption=""), "captions and paths are invalid"),
        (lambda b: b["screenshots"][0].update(caption="x" * 181), "captions and paths are invalid"),
        (lambda b: b["screenshots"][0].update(path="elsewhere/overview.png"), "captions and paths are invalid"),
        (lambda b: b["screenshots"][0].update(extra=1), "captions and paths are invalid"),
        (lambda b: b["screenshots"][0].update(path="docs/assets/screenshots/other.png"), "do not match"),
        (lambda b: b.update(bundle_sha256="0" * 64), "identity does not match"),
    ],
)
def test_a_malformed_or_inconsistent_bundle_is_refused(draft, change, message):
    _, _, bundle = draft
    broken = copy.deepcopy(bundle)
    change(broken)
    with pytest.raises(privacy.CaptureError, match=message):
        privacy.validate_bundle(broken)


def test_bundle_must_be_a_mapping():
    with pytest.raises(privacy.CaptureError, match="format is invalid"):
        privacy.validate_bundle(["not", "a", "bundle"])  # type: ignore[arg-type]


@pytest.mark.parametrize("filename", ["Upper.png", "../escape.png", "has space.png", "a" * 61 + ".png"])
def test_unbounded_artifact_filenames_are_refused(draft, filename):
    _, _, bundle = draft
    images = {filename if key == "overview.png" else key: value for key, value in bundle["images"].items()}
    shots = copy.deepcopy(bundle["screenshots"])
    shots[0]["path"] = "docs/assets/screenshots/" + Path(filename).name
    transcripts = {
        (Path(filename).stem + ".txt") if key == "overview.txt" else key: value
        for key, value in bundle["transcripts"].items()
    }
    broken = resealed(bundle, images=images, screenshots=shots, transcripts=transcripts)
    with pytest.raises(privacy.CaptureError):
        privacy.validate_bundle(broken)


def test_a_bad_digest_identity_is_refused(draft):
    _, _, bundle = draft
    images = bundle["images"] | {"overview.png": "NOT-HEX"}
    with pytest.raises(privacy.CaptureError, match="SHA-256 identities"):
        privacy.validate_bundle(resealed(bundle, images=images))


def test_a_changed_image_invalidates_the_review(draft):
    _, folder, bundle = draft
    (folder / "tides.png").write_bytes(b"\x89PNG\r\n\x1a\nretouched after review")
    with pytest.raises(privacy.CaptureError, match="Re-capture and re-review"):
        privacy.validate_bundle(bundle, folder)


def test_an_oversized_image_is_refused_even_when_its_hash_matches(draft):
    _, folder, bundle = draft
    big = b"\x89PNG\r\n\x1a\n" + b"0" * (500 * 1024)
    (folder / "tides.png").write_bytes(big)
    bundle = resealed(bundle, images=bundle["images"] | {"tides.png": digest(big)})
    with pytest.raises(privacy.CaptureError, match="Re-capture"):
        privacy.validate_bundle(bundle, folder)


def test_an_image_that_is_not_a_png_is_refused(draft):
    _, folder, bundle = draft
    fake = b"GIF89a not a png"
    (folder / "tides.png").write_bytes(fake)
    bundle = resealed(bundle, images=bundle["images"] | {"tides.png": digest(fake)})
    with pytest.raises(privacy.CaptureError, match="bounded PNG"):
        privacy.validate_bundle(bundle, folder)


def test_transcripts_must_be_canonical_unless_migrating(draft):
    _, folder, bundle = draft
    messy = b"trailing space  \r\n"
    (folder / "tides.txt").write_bytes(messy)
    bundle = resealed(bundle, transcripts=bundle["transcripts"] | {"tides.txt": digest(messy)})
    with pytest.raises(privacy.CaptureError, match="canonical whitespace"):
        privacy.validate_bundle(bundle, folder)
    privacy.validate_bundle(bundle, folder, require_canonical=False)


def test_an_approval_of_this_bundle_is_accepted(draft):
    _, _, bundle = draft
    privacy.validate_review(bundle, approval(bundle))


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"format": 2}, "does not match these captures"),
        ({"format": True}, "does not match these captures"),
        ({"bundle_sha256": "0" * 64}, "does not match these captures"),
        ({"reviewer": ""}, "identify its reviewing agent"),
        ({"reviewer": "bad <script>"}, "identify its reviewing agent"),
        ({"checked_images": ["overview.png"]}, "inspect every image"),
        ({"checked_images": "overview.png"}, "inspect every image"),
        ({"checks": "all"}, "checks must be a JSON object"),
        ({"decision": "reject"}, "has not approved"),
        ({"findings": ["token visible in overview.png"]}, "has not approved"),
        ({"checks": dict.fromkeys(privacy.CHECKS, True) | {"tokens_absent": False}}, "has not approved"),
        ({"extra": "field"}, "only the documented review fields"),
        ({"checks": dict.fromkeys(privacy.CHECKS, True) | {"bonus": True}}, "only the documented review fields"),
    ],
)
def test_a_review_that_does_not_clearly_approve_this_bundle_is_refused(draft, change, message):
    _, _, bundle = draft
    with pytest.raises(privacy.CaptureError, match=message):
        privacy.validate_review(bundle, approval(bundle, **change))


def test_a_review_must_be_a_json_object(draft):
    _, _, bundle = draft
    with pytest.raises(privacy.CaptureError, match="JSON object"):
        privacy.validate_review(bundle, ["approve"])  # type: ignore[arg-type]


def test_the_bundle_digest_ignores_its_own_field_but_binds_every_other(draft):
    _, _, bundle = draft
    assert privacy.bundle_digest(bundle) == privacy.bundle_digest(bundle | {"bundle_sha256": "ignored"})
    assert privacy.bundle_digest(bundle) != privacy.bundle_digest(bundle | {"core_version": "0.9.9"})


def test_the_review_prompt_binds_the_exact_bundle_and_lists_every_image(draft):
    _, _, bundle = draft
    prompt = privacy.review_prompt(bundle)
    assert privacy.bundle_digest(bundle) in prompt
    assert all(name in prompt for name in bundle["images"])


def test_prepare_review_writes_the_private_brief_and_schema(draft):
    _, folder, bundle = draft
    privacy.prepare_review(folder, bundle)
    assert json.loads((folder / "review-input.json").read_text()) == bundle
    assert json.loads((folder / "review.schema.json").read_text())["required"] == privacy.SCHEMA["required"]
    assert privacy.bundle_digest(bundle) in (folder / "REVIEW.md").read_text()


def test_a_supplied_receipt_is_validated_before_it_is_trusted(draft, tmp_path):
    root, _, bundle = draft
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps(approval(bundle)))
    assert privacy.run_agent(root, bundle, receipt)["decision"] == "approve"
    receipt.write_text(json.dumps(approval(bundle, decision="reject")))
    with pytest.raises(privacy.CaptureError, match="has not approved"):
        privacy.run_agent(root, bundle, receipt)


def test_without_codex_the_author_is_told_how_to_continue(draft, monkeypatch):
    root, folder, bundle = draft
    monkeypatch.setattr(privacy.shutil, "which", lambda name: None)
    with pytest.raises(privacy.CaptureError, match="--review-receipt") as stopped:
        privacy.run_agent(root, bundle)
    assert str(folder / "REVIEW.md") in str(stopped.value)


def test_a_failed_agent_run_preserves_the_draft_and_names_the_escape_hatch(draft, monkeypatch):
    root, folder, bundle = draft
    monkeypatch.setattr(privacy.shutil, "which", lambda name: "/fake/codex")
    monkeypatch.setattr(privacy.subprocess, "run", lambda command, **options: subprocess.CompletedProcess(command, 3))
    with pytest.raises(privacy.CaptureError, match="draft is preserved"):
        privacy.run_agent(root, bundle)
    assert (folder / "overview.png").is_file()


def test_the_codex_agent_runs_read_only_with_every_image_and_its_verdict_is_validated(draft, monkeypatch, capsys):
    root, folder, bundle = draft
    seen = {}
    monkeypatch.setattr(privacy.shutil, "which", lambda name: "/fake/codex")

    def run(command, **options):
        seen.update(command=command, options=options)
        (folder / "privacy-review.json").write_text(json.dumps(approval(bundle)))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(privacy.subprocess, "run", run)
    review = privacy.run_agent(root, bundle)
    command = seen["command"]
    assert command[command.index("--sandbox") + 1] == "read-only"
    images = [command[i + 1] for i, part in enumerate(command) if part == "--image"]
    assert sorted(Path(image).name for image in images) == sorted(bundle["images"])
    assert privacy.bundle_digest(bundle) in seen["options"]["input"]
    assert review["decision"] == "approve"
    assert "privacy agent" in capsys.readouterr().err


def test_an_agent_verdict_that_rejects_the_gallery_is_surfaced(draft, monkeypatch):
    root, folder, bundle = draft
    monkeypatch.setattr(privacy.shutil, "which", lambda name: "/fake/codex")

    def run(command, **options):
        rejected = approval(bundle, decision="reject", findings=["token visible in tides.png"])
        (folder / "privacy-review.json").write_text(json.dumps(rejected))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(privacy.subprocess, "run", run)
    with pytest.raises(privacy.CaptureError, match="has not approved"):
        privacy.run_agent(root, bundle)


def test_canonicalizing_a_draft_rewrites_only_transcripts_and_invalidates_old_receipts(draft):
    root, folder, bundle = draft
    messy = b"Fictional transcript  \r\nsecond line\r\n\r\n"
    (folder / "tides.txt").write_bytes(messy)
    bundle = resealed(bundle, transcripts=bundle["transcripts"] | {"tides.txt": digest(messy)})
    privacy.atomic_text(folder / "review-input.json", json.dumps(bundle))
    (folder / "index.html").write_text("<p>sheet</p>  \r\n\r\n")
    stale = folder / "privacy-review.json"
    stale.write_text(json.dumps(approval(bundle)))
    untouched_image = (folder / "tides.png").read_bytes()

    report = privacy.canonicalize_draft(folder)

    assert report["changed_transcripts"] == ["tides.txt"]
    assert report["review_required"] is True
    assert report["images_preserved"] == sorted(bundle["images"])
    assert (folder / "tides.txt").read_text() == "Fictional transcript\nsecond line\n"
    assert (folder / "index.html").read_text() == "<p>sheet</p>\n"
    assert (folder / "tides.png").read_bytes() == untouched_image
    assert not stale.exists()
    refreshed = json.loads((folder / "review-input.json").read_text())
    privacy.validate_bundle(refreshed, folder)
    assert refreshed["bundle_sha256"] == report["bundle_sha256"] != bundle["bundle_sha256"]


def test_canonicalizing_a_clean_draft_keeps_a_valid_receipt(draft):
    _, folder, bundle = draft
    privacy.prepare_review(folder, bundle)
    (folder / "privacy-review.json").write_text(json.dumps(approval(bundle)))
    (folder / "notes.json").write_text("not json at all")
    report = privacy.canonicalize_draft(folder)
    assert report["changed_transcripts"] == []
    assert report["review_required"] is False
    assert (folder / "privacy-review.json").is_file()


def test_canonicalization_is_limited_to_private_preview_folders(tmp_path):
    public = tmp_path / "docs/assets/screenshots"
    public.mkdir(parents=True)
    with pytest.raises(privacy.CaptureError, match="private screenshot draft folders"):
        privacy.canonicalize_draft(public)
