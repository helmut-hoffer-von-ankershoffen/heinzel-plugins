"""Screenshot authoring stays isolated, repeatable, reviewable and usable from agents."""

import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from heinzel_plugin_tools import capture, cli, planning, privacy

pytestmark = pytest.mark.unit


@pytest.fixture
def owner(tmp_path):
    (tmp_path / "src/heinzel_harbor").mkdir(parents=True)
    (tmp_path / "src/heinzel_harbor/__init__.py").write_text('raise RuntimeError("never import during checks")\n')
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="heinzel-harbor"\nversion="0.1.0"\ndescription="A fictional harbor."\n'
        '[project.entry-points."heinzel.modules"]\ntides="heinzel_harbor"\n'
    )
    return tmp_path


def recorded(owner):
    capture.write_default_plan(owner)
    plan = capture.read_plan(owner)
    shots = []
    for scene in plan["scenes"]:
        path = capture.OUTPUT / f"{scene['name']}.png"
        (owner / path).parent.mkdir(parents=True, exist_ok=True)
        (owner / path).write_bytes(b"\x89PNG\r\n\x1a\nfictional-test-capture")
        shots.append({"path": path.as_posix(), "surface": scene["surface"], "caption": scene["caption"]})
    with (owner / "pyproject.toml").open("a") as target:
        for shot in shots:
            target.write("\n[[tool.heinzel.catalog.screenshots]]\n")
            for key, value in shot.items():
                target.write(f"{key} = {json.dumps(value)}\n")
    definition = planning.record_definition(
        owner,
        plan,
        "# Synthetic test story\nTwo useful UI cases and one CLI result; no external credentials.",
        reviewer="Synthetic test source-analysis agent",
    )
    transcripts = {}
    for shot in shots:
        path = (owner / shot["path"]).with_suffix(".txt")
        path.write_text("Fictional screenshot test transcript\n")
        transcripts[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    bundle = {
        "format": 1,
        "plugin": "heinzel-harbor",
        "core_version": "0.9.8",
        "definition": definition,
        "inputs_sha256": capture.input_digest(owner, plan),
        "screenshots": shots,
        "images": {Path(s["path"]).name: hashlib.sha256((owner / s["path"]).read_bytes()).hexdigest() for s in shots},
        "transcripts": transcripts,
    }
    bundle["bundle_sha256"] = privacy.bundle_digest(bundle)
    review = {
        "format": 1,
        "bundle_sha256": bundle["bundle_sha256"],
        "reviewer": "Synthetic test privacy agent",
        "decision": "approve",
        "checked_images": sorted(bundle["images"]),
        "checks": dict.fromkeys(privacy.CHECKS, True),
        "findings": [],
    }
    manifest = {
        "format": 1,
        "plugin": bundle["plugin"],
        "core_version": bundle["core_version"],
        "inputs_sha256": capture.input_digest(owner, plan),
        "images": {s["path"]: hashlib.sha256((owner / s["path"]).read_bytes()).hexdigest() for s in shots},
        "review_bundle": bundle,
        "privacy_review": review,
    }
    (owner / capture.MANIFEST).write_text(json.dumps(manifest))
    (owner / "README.md").write_text(capture.readme_gallery("", shots))
    (owner / capture.OUTPUT / "index.html").write_text(
        capture.preview_document(bundle["plugin"], plan["scenes"], bundle["core_version"])
    )
    return shots


def test_default_plan_uses_the_declared_module_and_never_imports_plugin_code(owner):
    plan = capture.default_plan(owner)
    assert {scene["surface"] for scene in plan["scenes"]} == {"ui", "cli"}
    assert next(s for s in plan["scenes"] if s["surface"] == "cli")["command"] == ["tides", "--help"]
    assert "heinzel_harbor" not in sys.modules
    capture.write_default_plan(owner)
    assert capture.read_plan(owner) == plan
    path = owner / capture.PLAN
    original = path.read_bytes()
    capture.write_default_plan(owner)
    assert path.read_bytes() == original


def test_theme_defaults_capture_the_actual_theme_in_light_and_dark(owner):
    folder = owner / "src/heinzel_harbor/themes"
    folder.mkdir()
    (folder / "tide.toml").write_text('name="tide"\ntitle="Harbor Tide"\n')
    plan = capture.default_plan(owner)
    scenes = [s for s in plan["scenes"] if s["surface"] == "ui"]
    assert {s["appearance"] for s in scenes} == {"light", "dark"}
    assert all(s["theme"] == "tide" and s["route"] == "/" and not s["plugin_card"] for s in scenes)
    assert plan["scenes"][1]["command"] == ["system", "theme", "list"]


@pytest.mark.parametrize("mutation", ["external", "protocol-relative", "duplicate", "missing-cli", "shell", "selector"])
def test_scene_plan_rejects_unsafe_or_unusable_routes_and_actions(owner, mutation, monkeypatch):
    data = capture.default_plan(owner)
    if mutation == "external":
        data["scenes"][0]["route"] = "https://example.org/"
    elif mutation == "protocol-relative":
        data["scenes"][0]["route"] = "//example.org/"
    elif mutation == "duplicate":
        data["scenes"][1]["name"] = "ui"
    elif mutation == "missing-cli":
        data["scenes"][-1] = {**data["scenes"][0], "name": "another-ui"}
    elif mutation == "shell":
        data["scenes"][-1]["command"] = "hz tides; cat secret"
    else:
        data["scenes"][0]["steps"] = [{"action": "evaluate", "script": "alert(1)"}]
    (owner / capture.PLAN).parent.mkdir(parents=True)
    (owner / capture.PLAN).write_text("format=1\n")
    monkeypatch.setattr(capture.tomllib, "loads", lambda _: copy.deepcopy(data))
    with pytest.raises(ValueError, match="Scene|scene|gallery"):
        capture.read_plan(owner)


def test_demo_profile_cannot_inherit_normal_credentials_or_state(owner, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "not-a-real-token")
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key")
    monkeypatch.setenv("HZ_CONFIG_HOME", "/normal/private/config")
    monkeypatch.setenv("PATH", "/private/vendor/bin")
    env = capture.demo_environment(owner, owner / ".venv/bin/python")
    assert "GH_TOKEN" not in env and "OPENAI_API_KEY" not in env
    assert env["HZ_CONFIG_HOME"] == str(owner / "config_home")
    assert env["HOME"] == str(owner)
    assert env["HZ_SYSTEM_CREDENTIAL__BACKEND"] == "environment"
    assert "/private/vendor/bin" not in env["PATH"]
    assert env["HZ_ORG__EMAIL"] == "mira@example.com"
    assert os.environ["GH_TOKEN"].startswith("not-a-real-")


def test_offline_checks_detect_source_changes_without_running_or_installing_code(owner):
    recorded(owner)
    report = capture.check_capture(owner)
    assert report["ok"] and report["fresh"] and len(report["screenshots"]) == 3
    cache = owner / "src/heinzel_harbor/__pycache__/temporary.pyc"
    cache.parent.mkdir()
    cache.write_bytes(b"ignored cache")
    assert capture.check_capture(owner)["fresh"]
    source = owner / "src/heinzel_harbor/__init__.py"
    source.write_text(source.read_text() + "# Changed interface\n")
    with pytest.raises(ValueError, match="stale.*make screenshots"):
        capture.check_capture(owner)


def test_offline_check_rejects_tampered_images(owner):
    shots = recorded(owner)
    image = owner / shots[0]["path"]
    image.write_bytes(image.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="capture changed"):
        capture.check_capture(owner)


def test_checks_report_missing_captures_before_preparing_an_environment(owner, monkeypatch):
    capture.write_default_plan(owner)
    project = cli.Project(owner, "heinzel-harbor", "0.1.0", capture.project_data(owner))
    monkeypatch.setattr(cli, "prepare_environment", lambda *_: pytest.fail("check must be offline"))
    with pytest.raises(ValueError, match="No capture manifest.*make screenshots"):
        cli.check(project, None, fast=True)


def test_freshness_check_builds_view_assets_first_because_the_digest_covers_them(owner, monkeypatch):
    recorded(owner)
    (owner / "web").mkdir()
    (owner / "web/package.json").write_text(json.dumps({"scripts": {"build": "vite build"}}))
    project = cli.Project(owner, "heinzel-harbor", "0.1.0", capture.project_data(owner))
    order = []
    monkeypatch.setattr(cli, "run", lambda command, **_: order.append(("build", command[-3:])))
    monkeypatch.setattr(capture, "check_capture", lambda root: order.append(("check", root)) or {"fresh": True})
    assert cli.check_screenshots(project) == {"fresh": True}
    assert [step for step, _ in order] == ["build", "check"]
    assert order[0][1][1:] == ["run", "build"]


def test_agent_check_has_clean_json_for_success_and_actionable_stale_results(owner, monkeypatch, capsys):
    recorded(owner)
    project = cli.Project(owner, "heinzel-harbor", "0.1.0", capture.project_data(owner))
    monkeypatch.setattr(cli, "projects", lambda: [project])
    monkeypatch.setattr(sys, "argv", ["hz-plugin", "screenshots-check", "harbor", "--json"])
    assert cli.main() == 0
    assert json.loads(capsys.readouterr().out)["fresh"]
    (owner / "src/heinzel_harbor/new.py").write_text("# changed\n")
    assert cli.main() == 1
    failure = json.loads(capsys.readouterr().out)
    assert not failure["ok"] and "stale" in failure["error"]
    assert "screenshots" in failure["next"]


def test_agent_capture_passes_paths_and_options_as_individual_arguments(owner, monkeypatch):
    project = cli.Project(owner, "heinzel-harbor", "0.1.0", capture.project_data(owner))
    calls = []
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda command, **kwargs: (
            calls.append((command, kwargs)) or SimpleNamespace(returncode=0, stdout='{"ok": true}')
        ),
    )
    assert (
        cli.capture_plugin(project, "/candidate with spaces/core.whl", json_output=True, headed=True, open_preview=True)
        == 0
    )
    command, options = calls[0]
    assert command[command.index("--project") + 1] == str(owner)
    assert command[command.index("--core") + 1] == "/candidate with spaces/core.whl"
    assert {"--json", "--headed", "--open"} <= set(command)
    assert options["cwd"] == owner


def test_contact_sheet_escapes_owner_text_and_uses_only_local_images():
    document = capture.preview_document(
        "<Harbor & Tide>", [{"name": "ui", "surface": "ui", "caption": "<script>bad</script>"}], "0.9.8"
    )
    assert "<script>" not in document
    assert "&lt;Harbor &amp; Tide&gt;" in document
    assert 'href="ui.png"' in document
    assert 'src="ui.png"' in document
    assert "https://" not in document


def test_browser_requests_cannot_contact_external_services():
    from types import SimpleNamespace

    calls = []

    def request(url):
        return SimpleNamespace(
            request=SimpleNamespace(url=url),
            continue_=lambda: calls.append("local"),
            abort=lambda: calls.append("blocked"),
        )

    handler = capture.local_requests("http://127.0.0.1:1234")
    handler(request("http://127.0.0.1:1234/api/schema"))
    handler(request("https://www.youtube.com/embed/example"))
    handler(request("http://127.0.0.1:12345/"))
    assert calls == ["local", "blocked", "blocked"]


def test_browser_journey_is_required_for_tooling_changes_and_ordinary_plugin_edits_stay_scoped():
    import yaml

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/ci.yml").read_text())
    assert "screenshots" in workflow["jobs"]["ok"]["needs"]
    assert workflow["jobs"]["screenshots"]["if"] == "needs.plan.outputs.tooling == 'True'"
    assert '"$SCREENSHOTS" = success' in workflow["jobs"]["ok"]["steps"][0]["run"]
    assert cli.plan(["src/heinzel_plugin_tools/capture.py"], [], root)["tooling"]
    assert not cli.plan(["plugins/heinzel-harbor/src/view.py"], [], root)["tooling"]


def test_freshness_binds_reviewed_transcripts_and_all_receipt_fields(owner):
    shots = recorded(owner)
    transcript = (owner / shots[0]["path"]).with_suffix(".txt")
    transcript.write_text("Changed after the independent review")
    with pytest.raises(ValueError, match="artifacts changed"):
        capture.check_capture(owner)


@pytest.mark.parametrize("change", ["reject", "missing-image", "wrong-digest", "incomplete-checks", "extra-field"])
def test_offline_check_never_accepts_unreviewed_or_partial_receipts(owner, change):
    recorded(owner)
    path = owner / capture.MANIFEST
    manifest = json.loads(path.read_text())
    review = manifest["privacy_review"]
    if change == "reject":
        review["decision"] = "reject"
    elif change == "missing-image":
        review["checked_images"].pop()
    elif change == "wrong-digest":
        review["bundle_sha256"] = "a" * 64
    elif change == "incomplete-checks":
        review["checks"].pop("feature_relevant")
    else:
        review["extra"] = True
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="agent|review|receipt"):
        capture.check_capture(owner)


@pytest.mark.parametrize("relative", [capture.PLAN, capture.MANIFEST, capture.OUTPUT / "ui.png"])
def test_capture_files_cannot_follow_parent_or_leaf_symlinks(owner, tmp_path, relative):
    outside = tmp_path / "outside"
    outside.mkdir()
    destination = owner / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(outside / "private")
    with pytest.raises(ValueError, match="symbolic links"):
        privacy.safe_path(owner, relative)


def test_publication_rejects_linked_target_before_writing_any_gallery(owner, tmp_path):
    shots = recorded(owner)
    target = owner / capture.OUTPUT
    bundle = json.loads((owner / capture.MANIFEST).read_text())["review_bundle"]
    folder = owner / privacy.DRAFT
    folder.mkdir(parents=True)
    for path in target.iterdir():
        if path.suffix in {".png", ".txt"}:
            (folder / path.name).write_bytes(path.read_bytes())
    privacy.prepare_review(folder, bundle)
    receipt = folder / "privacy-review.json"
    receipt.write_text(json.dumps(json.loads((owner / capture.MANIFEST).read_text())["privacy_review"]))
    external = tmp_path / "external-file"
    external.write_text("Do not overwrite")
    (target / Path(shots[0]["path"]).name).unlink()
    (target / Path(shots[0]["path"]).name).symlink_to(external)
    with pytest.raises(ValueError, match="symbolic links"):
        capture.publish_draft(owner, receipt)
    assert external.read_text() == "Do not overwrite"


def test_generated_readme_gallery_is_owned_escaped_and_does_not_make_itself_stale(owner):
    shots = recorded(owner)
    (owner / "README.md").write_text("# Harbor\n\nA useful fictional harbor.\n")
    before = capture.input_digest(owner, capture.read_plan(owner))
    updated = capture.readme_gallery((owner / "README.md").read_text(), shots)
    (owner / "README.md").write_text(updated)
    assert capture.input_digest(owner, capture.read_plan(owner)) == before
    assert updated.count("<!-- screenshots:start -->") == 1
    assert updated.count("<img ") == 3
    assert "<details>" in updated
    assert capture.readme_gallery(updated, shots) == updated


def test_error_output_does_not_repeat_provider_secrets_or_private_paths():
    for error in [
        ValueError("Bearer fictional-secret-value-123456"),
        RuntimeError("https://localhost/#token=fictional-session"),
        ValueError("/Users/fictional-person/private/state"),
    ]:
        message = capture.safe_failure_message(error)
        assert "fictional-secret" not in message
        assert "fictional-session" not in message
        assert "/Users/" not in message


@pytest.mark.parametrize("value", ["2026-11-02T09:00:00Z", "2026-11-02T10:00:00+01:00"])
def test_fixed_browser_clock_and_motion_preferences_are_validated(owner, value):
    plan = capture.default_plan(owner)
    plan["browser_time"] = value
    plan["scenes"][0]["reduced_motion"] = "no-preference"
    plan["scenes"][0]["steps"] = [{"action": "wait-webgl"}]
    assert capture.validate_plan(owner, plan)["browser_time"] == value
    plan["browser_time"] = "2026-11-02T09:00:00"
    with pytest.raises(ValueError, match="timezone"):
        capture.validate_plan(owner, plan)


def test_first_publication_of_catalog_metadata_preserves_input_identity(owner):
    capture.write_default_plan(owner)
    plan = capture.read_plan(owner)
    before = capture.input_digest(owner, plan)
    path = owner / "pyproject.toml"
    path.write_text(
        path.read_text() + '\n[[tool.heinzel.catalog.screenshots]]\npath="docs/assets/screenshots/ui.png"\n'
        'surface="ui"\ncaption="A reviewed fictional feature"\n'
    )
    assert capture.input_digest(owner, plan) == before


@pytest.mark.parametrize("problem", ["version", "compatibility", "missing-package"])
def test_explicit_prepared_interpreters_must_match_the_owner_and_sdk_requirement(owner, monkeypatch, problem):
    versions = {"owner": "0.1.0", "core": "0.9.8", "compatible": True}
    if problem == "version":
        versions["owner"] = "0.2.0"
    elif problem == "compatibility":
        versions["compatible"] = False
    monkeypatch.setattr(
        capture.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(
            returncode=1 if problem == "missing-package" else 0,
            stdout=json.dumps(versions),
            stderr="untrusted provider text",
        ),
    )
    with pytest.raises(ValueError, match="version differs|compatibility|compatible"):
        capture.prepared_version(Path(sys.executable), capture.project_data(owner))


@pytest.mark.parametrize("phase", ["before-swap", "after-swap"])
def test_gallery_publication_rolls_back_without_deleting_the_previous_gallery(owner, monkeypatch, phase):
    recorded(owner)
    target = owner / capture.OUTPUT
    old = {path.name: path.read_bytes() for path in target.iterdir()}
    metadata_before = (owner / "pyproject.toml").read_bytes()
    readme_before = (owner / "README.md").read_bytes()
    bundle = json.loads((owner / capture.MANIFEST).read_text())["review_bundle"]
    receipt = json.loads((owner / capture.MANIFEST).read_text())["privacy_review"]
    folder = owner / privacy.DRAFT
    folder.mkdir(parents=True)
    for filename in [*bundle["images"], *bundle["transcripts"]]:
        (folder / filename).write_bytes((target / filename).read_bytes())
    privacy.prepare_review(folder, bundle)
    receipt_path = folder / "test-review.json"
    receipt_path.write_text(json.dumps(receipt))
    if phase == "before-swap":
        rename = Path.rename

        def failed_swap(path, destination):
            if path == target:
                raise PermissionError("Synthetic failure before the previous gallery moved")
            return rename(path, destination)

        monkeypatch.setattr(Path, "rename", failed_swap)
        expected = PermissionError
    else:

        def failed_check(_):
            raise ValueError("Synthetic failure after publication staging")

        monkeypatch.setattr(capture, "check_capture", failed_check)
        expected = ValueError
    with pytest.raises(expected, match="Synthetic failure"):
        capture.publish_draft(owner, receipt_path)
    assert {path.name: path.read_bytes() for path in target.iterdir()} == old
    assert (owner / "pyproject.toml").read_bytes() == metadata_before
    assert (owner / "README.md").read_bytes() == readme_before


def test_private_draft_canonicalization_preserves_images_and_requires_review_of_new_text_bytes(owner):
    recorded(owner)
    manifest = json.loads((owner / capture.MANIFEST).read_text())
    bundle = manifest["review_bundle"]
    folder = owner / privacy.DRAFT
    folder.mkdir(parents=True)
    original_images = {}
    for filename in bundle["images"]:
        data = (owner / capture.OUTPUT / filename).read_bytes()
        (folder / filename).write_bytes(data)
        original_images[filename] = data
    for filename in bundle["transcripts"]:
        data = b"Fictional transcript   \r\nTable row\t\r\n\r\n"
        (folder / filename).write_bytes(data)
        bundle["transcripts"][filename] = hashlib.sha256(data).hexdigest()
    bundle["bundle_sha256"] = privacy.bundle_digest(bundle)
    original_digest = bundle["bundle_sha256"]
    (folder / "review-input.json").write_text(json.dumps(bundle))
    (folder / "index.html").write_text("<html>Safe fictional gallery</html>")
    (folder / "privacy-review.json").write_text(json.dumps({"decision": "approve", "bundle_sha256": original_digest}))
    with pytest.raises(ValueError, match="canonical whitespace"):
        privacy.validate_bundle(bundle, folder)
    report = privacy.canonicalize_draft(folder)
    updated = json.loads((folder / "review-input.json").read_text())
    assert report["review_required"]
    assert report["bundle_sha256"] != original_digest
    assert not (folder / "privacy-review.json").exists()
    assert (folder / "index.html").read_bytes().endswith(b"\n")
    for filename in updated["transcripts"]:
        assert (folder / filename).read_bytes() == b"Fictional transcript\nTable row\n"
    assert all((folder / filename).read_bytes() == data for filename, data in original_images.items())
    privacy.validate_bundle(updated, folder)
    repeated = privacy.canonicalize_draft(folder)
    assert repeated["changed_transcripts"] == []
    assert repeated["review_required"]


def test_canonicalization_refuses_to_rebind_tampered_images_or_modify_public_galleries(owner):
    recorded(owner)
    with pytest.raises(ValueError, match="private screenshot draft"):
        privacy.canonicalize_draft(owner / capture.OUTPUT)


def test_generated_text_matches_end_of_file_and_trailing_whitespace_hook_contract():
    assert privacy.canonical_text("one  \r\n\t two\t\n\n") == "one\n\t two\n"
    assert privacy.canonical_text(" \t\n\n") == ""
    assert privacy.canonical_text("already canonical\n") == "already canonical\n"
    document = capture.preview_document(
        "Harbor", [{"name": "ui", "surface": "ui", "caption": "Fictional harbor"}], "0.9.8"
    )
    assert privacy.canonical_text(document) == document


@pytest.mark.parametrize("change", ["remove-block", "remove-file", "change-caption", "change-image", "reorder-images"])
def test_offline_freshness_requires_the_exact_generated_readme_gallery(owner, change):
    shots = recorded(owner)
    path = owner / "README.md"
    text = path.read_text()
    if change == "remove-block":
        path.write_text("")
    elif change == "remove-file":
        path.unlink()
    elif change == "change-caption":
        path.write_text(text.replace(shots[0]["caption"], "A different unreviewed claim"))
    elif change == "change-image":
        path.write_text(text.replace(shots[0]["path"], "docs/assets/other.png"))
    else:
        first, second = shots[0]["path"], shots[1]["path"]
        path.write_text(text.replace(first, "TEMPORARY").replace(second, first).replace("TEMPORARY", second))
    with pytest.raises(ValueError, match="README gallery"):
        capture.check_capture(owner)


@pytest.mark.parametrize("change", ["duplicate", "reverse", "incomplete"])
def test_readme_generator_rejects_invalid_marker_count_or_order(owner, change):
    shots = recorded(owner)
    text = (owner / "README.md").read_text()
    start, end = "<!-- screenshots:start -->", "<!-- screenshots:end -->"
    if change == "duplicate":
        text += start
    elif change == "reverse":
        text = text.replace(start, "TEMPORARY").replace(end, start).replace("TEMPORARY", end)
    else:
        text = text.replace(end, "")
    with pytest.raises(ValueError, match="README screenshot markers"):
        capture.readme_gallery(text, shots)


@pytest.mark.parametrize("change", ["remove", "caption", "provenance", "script"])
def test_offline_freshness_requires_the_exact_safe_contact_sheet(owner, change):
    shots = recorded(owner)
    path = owner / capture.OUTPUT / "index.html"
    text = path.read_text()
    if change == "remove":
        path.unlink()
    elif change == "caption":
        path.write_text(text.replace(shots[0]["caption"], "An unreviewed claim"))
    elif change == "provenance":
        path.write_text(text.replace("0.9.8", "0.9.9"))
    else:
        path.write_text(text + "<script>unreviewedCode()</script>\n")
    with pytest.raises(ValueError, match="contact sheet differs"):
        capture.check_capture(owner)


@pytest.mark.parametrize("padding", [15, 161, True, "48"])
def test_detail_focus_rejects_unbounded_padding(owner, padding):
    capture.write_default_plan(owner)
    plan_path = owner / capture.PLAN
    raw = json.dumps(padding).lower() if isinstance(padding, bool) else json.dumps(padding)
    plan_path.write_text(plan_path.read_text() + f'\n[scenes.focus]\nrole="region"\nname="Tides"\npadding={raw}\n')
    with pytest.raises(capture.CaptureError, match="focus padding"):
        capture.read_plan(owner)
