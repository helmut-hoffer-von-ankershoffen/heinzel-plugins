"""Exact pre-upgrade public galleries remain inspectable, without admitting old evidence to any write path."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from heinzel_plugin_tools import capture, privacy
from heinzel_plugin_tools._historical_galleries import MANIFESTS, PUBLIC_BASE, PUBLIC_TREE

pytestmark = pytest.mark.unit
REPO = Path(__file__).resolve().parents[1]
# The whole pre-relock Zoom plugin, frozen: the live plugin carries a current format-2 gallery.
ZOOM_ORIGINAL = REPO / "tests/fixtures/historical_zoom_plugin"
RECAPTURED = (
    "heinzel-clock",
    "heinzel-resource",
    "heinzel-tailscale",
    "heinzel-theme",
    "heinzel-google",
    "heinzel-github",
    "heinzel-weather",
    "heinzel-example",
    "heinzel-atlassian",
)


def file_hashes(folder):
    return {
        p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in folder.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("plugin", sorted(MANIFESTS))
def test_exact_authenticated_historical_gallery_integrity_is_read_only(plugin, monkeypatch):
    if plugin == "heinzel-zoom":
        folder = ZOOM_ORIGINAL / capture.OUTPUT
    elif plugin in RECAPTURED:
        folder = REPO / "tests/fixtures/historical_galleries" / plugin
    else:
        folder = REPO / "plugins" / plugin / capture.OUTPUT
    manifest_bytes = (folder / capture.MANIFEST.name).read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == MANIFESTS[plugin]
    assert PUBLIC_BASE == "3be4b072ca2c78c6558298434319e30550e91a23"
    assert PUBLIC_TREE == "4bd7c172d84526497cceba28b9c20e714897922d"
    before = file_hashes(folder)
    monkeypatch.setattr(privacy, "run_agent", lambda *a, **kw: pytest.fail("read-only check cannot start an agent"))
    privacy.validate_historical_gallery(manifest_bytes, folder, plugin)
    assert before == file_hashes(folder)
    assert (folder / capture.MANIFEST.name).read_bytes() == manifest_bytes


@pytest.fixture
def historical(tmp_path):
    owner = tmp_path / "weather"
    shutil.copytree(
        ZOOM_ORIGINAL,
        owner,
        ignore=shutil.ignore_patterns("node_modules", ".venv", ".preview", "__pycache__"),
    )
    assert capture.check_capture(owner)["fresh"]
    return owner


def test_current_source_and_historical_review_are_labeled_without_claiming_a_story_bundle_review(historical):
    report = capture.check_capture(historical)
    assert report["fresh"] and report["privacy_reviewed"]
    assert report["review_bundle_format"] == 1
    assert report["source_story_bundle_reviewed"] is False


@pytest.mark.parametrize(
    "change",
    [
        "source",
        "plan",
        "story",
        "definition",
        "image",
        "transcript",
        "receipt",
        "caption",
        "contact-sheet",
        "readme-gallery",
    ],
)
def test_historical_validation_rejects_every_changed_bound_input(historical, change):
    owner = historical
    manifest_path = owner / capture.MANIFEST
    manifest = json.loads(manifest_path.read_bytes())
    if change == "source":
        path = owner / "src/heinzel_zoom/__init__.py"
        path.write_text(path.read_text() + "\n# changed source\n")
    elif change == "plan":
        path = owner / capture.PLAN
        path.write_text(path.read_text().replace("caption = ", 'caption = "Changed " # ', 1))
    elif change == "story":
        path = owner / "docs/SCREENSHOT_STORY.md"
        path.write_text(path.read_text() + "\nChanged story terms.\n")
    elif change == "definition":
        path = owner / "docs/screenshot-definition.json"
        value = json.loads(path.read_text())
        value["reviewer"] = "Different reviewer"
        path.write_text(json.dumps(value))
    elif change == "image":
        path = owner / next(iter(manifest["images"]))
        path.write_bytes(path.read_bytes() + b"changed")
    elif change == "transcript":
        path = owner / capture.OUTPUT / next(iter(manifest["review_bundle"]["transcripts"]))
        path.write_text(path.read_text() + "Changed transcript\n")
    elif change == "receipt":
        manifest["privacy_review"]["reviewer"] = "Different reviewer"
        manifest_path.write_text(json.dumps(manifest))
    elif change == "caption":
        manifest["review_bundle"]["screenshots"][0]["caption"] = "Changed caption"
        manifest_path.write_text(json.dumps(manifest))
    elif change == "contact-sheet":
        path = owner / capture.OUTPUT / "index.html"
        path.write_text(path.read_text() + "changed")
    else:
        path = owner / "README.md"
        path.write_text(path.read_text().replace("<!-- screenshots:start -->", "<!-- screenshots:start -->changed", 1))
    with pytest.raises((privacy.CaptureError, ValueError)):
        capture.check_capture(owner)


def test_cross_plugin_substitution_and_unknown_or_rewritten_manifests_are_refused(historical):
    owner = historical
    raw = (owner / capture.MANIFEST).read_bytes()
    with pytest.raises(privacy.CaptureError, match="not pinned"):
        privacy.validate_historical_gallery(raw, owner / capture.OUTPUT, "heinzel-theme")
    with pytest.raises(privacy.CaptureError, match="not pinned"):
        privacy.validate_historical_gallery(raw, owner / capture.OUTPUT, "heinzel-unknown")
    # Re-serialization retains the same semantic bundle/receipt but is not the authenticated entire manifest.
    rewritten = json.dumps(json.loads(raw), sort_keys=True).encode()
    with pytest.raises(privacy.CaptureError, match="not pinned"):
        privacy.validate_historical_gallery(rewritten, owner / capture.OUTPUT, "heinzel-zoom")


@pytest.mark.parametrize("route", ["bundle", "review", "prepare", "agent", "canonicalize", "publish"])
def test_pinned_legacy_evidence_is_rejected_by_every_draft_or_admission_route(historical, monkeypatch, route):
    owner = historical
    manifest = json.loads((owner / capture.MANIFEST).read_bytes())
    bundle, review = manifest["review_bundle"], manifest["privacy_review"]
    folder = owner / privacy.DRAFT
    shutil.copytree(owner / capture.OUTPUT, folder)
    (folder / "review-input.json").write_text(json.dumps(bundle))
    receipt = folder / "original-privacy-review.json"
    receipt.write_text(json.dumps(review))
    before = file_hashes(folder)
    monkeypatch.setattr(
        privacy.subprocess, "run", lambda *a, **kw: pytest.fail("legacy evidence cannot admit an agent")
    )
    actions = {
        "bundle": lambda: privacy.validate_bundle(bundle, folder),
        "review": lambda: privacy.validate_review(bundle, review),
        "prepare": lambda: privacy.prepare_review(folder, bundle),
        "agent": lambda: privacy.run_agent(owner, bundle, receipt),
        "canonicalize": lambda: privacy.canonicalize_draft(folder),
        "publish": lambda: capture.publish_draft(owner, receipt),
    }
    with pytest.raises(privacy.CaptureError, match="format is invalid"):
        actions[route]()
    assert file_hashes(folder) == before
    assert (owner / capture.MANIFEST).read_bytes() == (ZOOM_ORIGINAL / capture.MANIFEST).read_bytes()


def test_original_receipt_cannot_be_reused_after_constructing_a_format2_story_bundle(historical):
    owner = historical
    manifest = json.loads((owner / capture.MANIFEST).read_bytes())
    bundle = manifest["review_bundle"]
    folder = owner / privacy.DRAFT
    shutil.copytree(owner / capture.OUTPUT, folder)
    bundle["format"] = 2
    bundle["source_story"] = {"path": privacy.SOURCE_STORY, "sha256": bundle["definition"]["story_sha256"]}
    shutil.copyfile(owner / "docs/SCREENSHOT_STORY.md", folder / privacy.SOURCE_STORY)
    bundle["bundle_sha256"] = privacy.bundle_digest(bundle)
    (folder / "review-input.json").write_text(json.dumps(bundle))
    receipt = folder / "original-privacy-review.json"
    receipt.write_text(json.dumps(manifest["privacy_review"]))
    privacy.validate_bundle(bundle, folder)
    before = file_hashes(owner / capture.OUTPUT)
    with pytest.raises(privacy.CaptureError, match="does not match"):
        capture.publish_draft(owner, receipt)
    assert before == file_hashes(owner / capture.OUTPUT)
