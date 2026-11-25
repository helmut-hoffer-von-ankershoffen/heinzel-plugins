"""Screenshot authoring stays isolated, repeatable, reviewable and usable from agents."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from heinzel_plugin_tools import capture, cli, privacy

pytestmark = [pytest.mark.unit, pytest.mark.usefixtures("fictional_capture_terms")]


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
    shots = capture.expected_shots(plan)
    for shot in shots:
        (owner / shot["path"]).parent.mkdir(parents=True, exist_ok=True)
        (owner / shot["path"]).write_bytes(b"\x89PNG\r\n\x1a\nfictional-test-capture")
        (owner / shot["path"]).with_suffix(".txt").write_text("Fictional screenshot test transcript\n")
    with (owner / "pyproject.toml").open("a") as target:
        for shot in shots:
            target.write("\n[[tool.heinzel.catalog.screenshots]]\n")
            for key, value in shot.items():
                target.write(f"{key} = {json.dumps(value)}\n")
    manifest = {
        "format": 2,
        "plugin": "heinzel-harbor",
        "core_version": "0.9.8",
        "inputs_sha256": capture.input_digest(owner, plan),
        "images": {s["path"]: hashlib.sha256((owner / s["path"]).read_bytes()).hexdigest() for s in shots},
        "transcripts": {
            f"{scene['name']}.txt": hashlib.sha256(
                (owner / capture.OUTPUT / f"{scene['name']}.txt").read_bytes()
            ).hexdigest()
            for scene in plan["scenes"]
        },
    }
    (owner / capture.MANIFEST).write_text(json.dumps(manifest))
    (owner / "README.md").write_text(capture.readme_gallery("", shots))
    (owner / capture.OUTPUT / "index.html").write_text(
        capture.preview_document("heinzel-harbor", plan["scenes"], "0.9.8")
    )
    return shots


def draft_of(owner):
    """A private draft holding the published gallery's bytes, as a capture leaves it."""
    plan = capture.read_plan(owner)
    folder = owner / privacy.DRAFT
    folder.mkdir(parents=True)
    for scene in plan["scenes"]:
        for extension in ("png", "txt"):
            name = f"{scene['name']}.{extension}"
            (folder / name).write_bytes((owner / capture.OUTPUT / name).read_bytes())
        (folder / f"{scene['name']}.scan.txt").write_text("Fictional DOM and form values")
    draft = {
        "format": 1,
        "plugin": "heinzel-harbor",
        "core_version": "0.9.8",
        "inputs_sha256": capture.input_digest(owner, plan),
        "scan_text": {
            f"{s['name']}.scan.txt": hashlib.sha256((folder / f"{s['name']}.scan.txt").read_bytes()).hexdigest()
            for s in plan["scenes"]
        },
        "images": {
            f"{s['name']}.png": hashlib.sha256((folder / f"{s['name']}.png").read_bytes()).hexdigest()
            for s in plan["scenes"]
        },
    }
    (folder / capture.DRAFT_MANIFEST).write_text(json.dumps(draft))
    return folder


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
    (owner / capture.PLAN).write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Scene|scene|gallery"):
        capture.read_plan(owner)


def test_demo_profile_cannot_inherit_normal_credentials_or_state(owner, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "not-a-real-token")
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key")
    monkeypatch.setenv("HZ_CONFIG_HOME", "/normal/private/config")
    monkeypatch.setenv("PATH", "/private/vendor/bin")
    env = capture.demo_environment(owner, owner / ".venv/bin/python")
    assert "GH_TOKEN" not in env
    assert "OPENAI_API_KEY" not in env
    assert env["HZ_CONFIG_HOME"] == str(owner / "config_home")
    assert env["HOME"] == str(owner)
    assert env["HZ_SYSTEM_CREDENTIAL__BACKEND"] == "environment"
    assert "/private/vendor/bin" not in env["PATH"]
    assert env["HZ_ORG__EMAIL"] == "mira@example.com"
    assert os.environ["GH_TOKEN"].startswith("not-a-real-")


def test_offline_checks_detect_ui_changes_without_running_or_installing_code(owner):
    recorded(owner)
    report = capture.check_capture(owner)
    assert report["ok"]
    assert report["fresh"]
    assert len(report["screenshots"]) == 3
    source = owner / "src/heinzel_harbor/__init__.py"
    source.write_text(source.read_text() + "# Changed logic, no UI input\n")
    assert capture.check_capture(owner)["fresh"]
    view = owner / "src/heinzel_harbor/views/index.js"
    view.parent.mkdir()
    view.write_text("export const tide = 1;\n")
    with pytest.raises(privacy.StaleGallery, match="stale.*make screenshots NAME=heinzel-harbor") as stale:
        capture.check_capture(owner)
    assert stale.value.command == "make screenshots NAME=heinzel-harbor"


@pytest.mark.parametrize(
    ("relative", "stale"),
    [
        ("src/heinzel_harbor/views/app.css", True),
        ("src/heinzel_harbor/static/logo.svg", True),
        ("src/heinzel_harbor/themes/harbor.toml", True),
        ("web/src/App.tsx", True),
        ("docs/screenshot_fixture.py", True),
        ("src/heinzel_harbor/logic.py", False),
        ("src/heinzel_harbor/data.toml", False),
        ("web/src/App.test.tsx", False),
        ("web/e2e/journey.mjs", False),
        ("tests/view_test.py", False),
        ("docs/NOTES.md", False),
        ("requirements.lock", False),
    ],
)
def test_only_ui_inputs_make_the_gallery_stale(owner, relative, stale):
    capture.write_default_plan(owner)
    plan_path = owner / capture.PLAN
    plan = json.loads(plan_path.read_text())
    (owner / "docs/screenshot_fixture.py").write_text("# fictional fixture\n")
    plan["bootstrap"] = "docs/screenshot_fixture.py"
    plan_path.write_text(json.dumps(plan))
    before = capture.input_digest(owner, capture.read_plan(owner))
    path = owner / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(path.read_text() + "changed\n" if path.exists() else "new\n")
    assert (capture.input_digest(owner, capture.read_plan(owner)) != before) is stale


def test_a_caption_edit_in_the_definition_makes_the_gallery_stale(owner):
    recorded(owner)
    plan_path = owner / capture.PLAN
    plan = json.loads(plan_path.read_text())
    plan["scenes"][0]["caption"] = "A new caption for the fictional harbor"
    plan_path.write_text(json.dumps(plan))
    with pytest.raises(privacy.StaleGallery):
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
    with pytest.raises(ValueError, match="no capture manifest.*make screenshots"):
        cli.check(project, None, fast=True)


def test_freshness_check_never_builds_runs_or_reviews(owner, monkeypatch):
    recorded(owner)
    (owner / "web").mkdir()
    (owner / "web/package.json").write_text(json.dumps({"scripts": {"build": "vite build"}}))
    project = cli.Project(owner, "heinzel-harbor", "0.1.0", capture.project_data(owner))
    monkeypatch.setattr(cli, "run", lambda *_a, **_k: pytest.fail("the freshness check must not build"))
    assert cli.check_screenshots(project)["fresh"]


def test_agent_check_has_clean_json_for_success_and_actionable_stale_results(owner, monkeypatch, capsys):
    recorded(owner)
    project = cli.Project(owner, "heinzel-harbor", "0.1.0", capture.project_data(owner))
    monkeypatch.setattr(cli, "projects", lambda: [project])
    monkeypatch.setattr(sys, "argv", ["hz-plugin", "screenshots-check", "harbor", "--json"])
    assert cli.main() == 0
    assert json.loads(capsys.readouterr().out)["fresh"]
    (owner / "src/heinzel_harbor/new.py").write_text("# changed logic only\n")
    assert cli.main() == 0
    capsys.readouterr()
    (owner / "src/heinzel_harbor/new.css").write_text("main { color: teal; }\n")
    assert cli.main() == 1
    failure = json.loads(capsys.readouterr().out)
    assert not failure["ok"]
    assert "stale" in failure["error"]
    assert failure["stale"] is True
    assert failure["command"] == failure["next"] == "make screenshots NAME=heinzel-harbor"


def test_check_all_lists_every_stale_gallery_with_its_command(owner, monkeypatch, capsys):
    recorded(owner)
    project = cli.Project(owner, "heinzel-harbor", "0.1.0", capture.project_data(owner))
    monkeypatch.setattr(cli, "projects", lambda: [project])
    monkeypatch.setattr(sys, "argv", ["hz-plugin", "screenshots-check", "--all", "--json"])
    assert cli.main() == 0
    assert json.loads(capsys.readouterr().out) == {"ok": True, "fresh": ["heinzel-harbor"], "stale": [], "failed": []}
    (owner / "src/heinzel_harbor/new.css").write_text("main { color: teal; }\n")
    assert cli.main() == 1
    report = json.loads(capsys.readouterr().out)
    assert [item["command"] for item in report["stale"]] == ["make screenshots NAME=heinzel-harbor"]


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


def test_freshness_binds_transcripts_and_scans_them_again(owner):
    shots = recorded(owner)
    transcript = (owner / shots[0]["path"]).with_suffix(".txt")
    transcript.write_text("Changed after capture")
    with pytest.raises(ValueError, match="transcript artifacts changed"):
        capture.check_capture(owner)


def test_the_offline_check_refuses_a_committed_transcript_with_a_secret(owner):
    shots = recorded(owner)
    transcript = (owner / shots[0]["path"]).with_suffix(".txt")
    transcript.write_text("token ghp_" + "q" * 36 + "\n")
    manifest = json.loads((owner / capture.MANIFEST).read_text())
    manifest["transcripts"][transcript.name] = hashlib.sha256(transcript.read_bytes()).hexdigest()
    (owner / capture.MANIFEST).write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="credential"):
        capture.check_capture(owner)


@pytest.mark.parametrize("change", ["old-format", "missing-transcript", "extra-field", "other-plugin"])
def test_offline_check_refuses_a_manifest_that_does_not_describe_the_gallery(owner, change):
    recorded(owner)
    path = owner / capture.MANIFEST
    manifest = json.loads(path.read_text())
    if change == "old-format":
        manifest["format"] = 1
    elif change == "missing-transcript":
        manifest["transcripts"].popitem()
    elif change == "extra-field":
        manifest["privacy_review"] = {"decision": "approve"}
    else:
        manifest["plugin"] = "heinzel-other"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="manifest|names another plugin"):
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
    draft_of(owner)
    external = tmp_path / "external-file"
    external.write_text("Do not overwrite")
    (target / Path(shots[0]["path"]).name).unlink()
    (target / Path(shots[0]["path"]).name).symlink_to(external)
    with pytest.raises(ValueError, match="symbolic links"):
        capture.publish_draft(owner)
    assert external.read_text() == "Do not overwrite"


def test_a_fresh_draft_publishes_without_any_review_and_checks_fresh(owner):
    recorded(owner)
    (owner / capture.MANIFEST).unlink()
    draft_of(owner)
    report = capture.publish_draft(owner)
    assert report["fresh"]
    assert set(json.loads((owner / capture.MANIFEST).read_text())) == capture.MANIFEST_KEYS


def test_a_draft_with_an_unsafe_transcript_publishes_nothing(owner):
    recorded(owner)
    folder = draft_of(owner)
    (folder / "cli.txt").write_text("Signed in as someone@realmail.de\n")
    before = (owner / capture.MANIFEST).read_bytes()
    with pytest.raises(ValueError, match="personal identity"):
        capture.publish_draft(owner)
    assert (owner / capture.MANIFEST).read_bytes() == before


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
    draft_of(owner)
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
        capture.publish_draft(owner)
    assert {path.name: path.read_bytes() for path in target.iterdir()} == old
    assert (owner / "pyproject.toml").read_bytes() == metadata_before
    assert (owner / "README.md").read_bytes() == readme_before


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
    plan = json.loads(plan_path.read_text())
    plan["scenes"][0]["focus"] = {"role": "region", "name": "Tides", "padding": padding}
    plan_path.write_text(json.dumps(plan))
    with pytest.raises(capture.CaptureError, match="focus padding"):
        capture.read_plan(owner)


def with_dependencies(owner, dependencies='"heinzel>=0.9,<0.10", "httpx>=0.28"'):
    path = owner / "pyproject.toml"
    path.write_text(
        path.read_text().replace(
            'description="A fictional harbor."\n', f'description="A fictional harbor."\ndependencies=[{dependencies}]\n'
        )
    )
    (owner / "requirements.lock").write_text("httpx==0.28.1 --hash=sha256:00\nhatchling==1.29.0 --hash=sha256:00\n")
    (owner / "plugin-lock.json").write_text('{"format": 2}\n')


def edit(path, old, new):
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))


@pytest.mark.parametrize(
    "change",
    [
        lambda owner: edit(owner / "requirements.lock", "httpx==0.28.1", "httpx==0.28.2"),  # a security relock
        lambda owner: (owner / "plugin-lock.json").write_text('{"format": 2, "relocked": true}\n'),
        lambda owner: edit(owner / "pyproject.toml", 'version="0.1.0"', 'version="0.1.1"'),  # a bump
        lambda owner: edit(owner / "pyproject.toml", '"httpx>=0.28"', '"httpx>=0.28.2"'),  # a security floor
        lambda owner: edit(owner / "requirements.lock", "hatchling==1.29.0", "hatchling==1.30.0"),  # no build hook
        lambda owner: edit(owner / "pyproject.toml", '"httpx>=0.28"', '"httpx>=0.28", "heinzel-lighthouse>=1"'),
        lambda owner: (owner / "hatch_build.py").write_text("# builds the views\n"),
    ],
)
def test_a_relock_bump_floor_or_dependency_leaves_the_gallery_fresh(owner, change):
    with_dependencies(owner)
    recorded(owner)
    change(owner)
    assert capture.check_capture(owner)["fresh"]


@pytest.mark.parametrize(
    ("text", "renders"),
    [("v0.1.0", True), ("0.1.0 ready", True), ("0.1.01", False), ("10.1.0", False), ("0.1.0.1", False)],
)
def test_a_transcript_may_not_render_the_plugin_version_the_digest_leaves_out(owner, text, renders):
    shots = recorded(owner)
    (owner / shots[0]["path"]).with_suffix(".txt").write_text(f"Harbor {text}\n")
    if renders:
        with pytest.raises(ValueError, match="renders the plugin version 0.1.0"):
            capture.check_capture(owner)
    else:
        capture.unrendered_version(owner, "0.9.8")


def test_a_plugin_version_equal_to_the_rendered_core_version_is_not_mistaken_for_the_plugin(owner):
    shots = recorded(owner)
    (owner / shots[0]["path"]).with_suffix(".txt").write_text("Heinzelmännchen v0.1.0\n")
    capture.unrendered_version(owner, "0.1.0")
    with pytest.raises(ValueError, match="renders the plugin version"):
        capture.unrendered_version(owner, "0.9.8")


REPOSITORY = Path(__file__).resolve().parents[1]


def test_every_committed_gallery_is_fresh_under_the_ui_input_rule():
    """No pins and no migration: each committed gallery's digest is today's digest of its UI inputs."""
    for directory in sorted((REPOSITORY / "plugins").glob("*/")):
        if (directory / capture.MANIFEST).is_file():
            plan = capture.read_plan(directory)
            recorded = json.loads((directory / capture.MANIFEST).read_text())["inputs_sha256"]
            assert capture.input_digest(directory, plan) == recorded, f"run make screenshots NAME={directory.name}"


def test_a_version_only_relock_keeps_a_committed_gallery_fresh(tmp_path):
    plugin = tmp_path / "heinzel-example"
    shutil.copytree(REPOSITORY / "plugins/heinzel-example", plugin, ignore=shutil.ignore_patterns(".venv"))
    lock = plugin / "requirements.lock"
    relocked, moved = re.subn(r"^(opentelemetry-api==\S+) ", r"\1.post1 ", lock.read_text(), flags=re.MULTILINE)
    assert moved == 1
    lock.write_text(relocked)
    assert capture.check_capture(plugin)["fresh"]


@pytest.mark.parametrize("state", ["fresh", "stale", "missing", "corrupt", "malformed"])
def test_all_checks_real_galleries_and_preserves_failure_types(owner, monkeypatch, capsys, state):
    shots = recorded(owner)
    if state == "stale":
        (owner / "src/heinzel_harbor/new.css").write_text("main {color: teal}\n")
    elif state == "missing":
        (owner / capture.MANIFEST).unlink()
    elif state == "corrupt":
        image = owner / shots[0]["path"]
        image.write_bytes(image.read_bytes() + b"tampered")
    elif state == "malformed":
        (owner / capture.MANIFEST).write_text("not JSON")
    project = cli.Project(owner, "heinzel-harbor", "0.1.0", capture.project_data(owner))
    monkeypatch.setattr(cli, "projects", lambda: [project])
    monkeypatch.setattr(cli, "prepare_environment", lambda *_: pytest.fail("must not install or run the plugin"))
    assert cli.screenshot_main(["--all", "--json"], check=True) == (0 if state == "fresh" else 1)
    report = json.loads(capsys.readouterr().out)
    category = "fresh" if state == "fresh" else "stale" if state in {"stale", "missing"} else "failed"
    assert len(report[category]) == 1
    assert sum(len(report[key]) for key in ("fresh", "stale", "failed")) == 1
    assert report["ok"] is (state == "fresh")
    if category == "stale":
        assert report[category][0]["command"] == "make screenshots NAME=heinzel-harbor"


def test_all_continues_after_failure_and_skips_only_unconfigured_galleries(tmp_path, monkeypatch, capsys):
    projects = []
    for name in ("broken", "fresh", "stale", "absent", "linked"):
        root = tmp_path / name
        root.mkdir()
        if name != "absent":
            (root / capture.PLAN).parent.mkdir()
            if name == "linked":
                (root / capture.PLAN).symlink_to(root / "missing-plan")
            else:
                (root / capture.PLAN).write_text("# synthetic plan\n")
        projects.append(cli.Project(root, f"heinzel-{name}", "0.1.0", {}))
    seen = []

    def check(project):
        seen.append(project.name)
        if project.name in {"heinzel-broken", "heinzel-linked"}:
            raise privacy.CaptureError("Invalid gallery")
        if project.name == "heinzel-stale":
            raise privacy.StaleGallery("Regenerate gallery", "make screenshots NAME=heinzel-stale")
        return {"ok": True}

    monkeypatch.setattr(cli, "projects", lambda: projects)
    monkeypatch.setattr(cli, "check_screenshots", check)
    assert cli.screenshot_main(["--check", "--all", "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert seen == ["heinzel-broken", "heinzel-fresh", "heinzel-stale", "heinzel-linked"]
    assert report["fresh"] == ["heinzel-fresh"]
    assert [item["plugin"] for item in report["failed"]] == ["heinzel-broken", "heinzel-linked"]
    assert [item["plugin"] for item in report["stale"]] == ["heinzel-stale"]


@pytest.mark.parametrize("arguments", [["--all"], ["harbor", "--all", "--check"], ["--all", "--init"]])
def test_all_refuses_capture_or_ambiguous_selection_before_inventory(monkeypatch, capsys, arguments):
    monkeypatch.setattr(cli, "projects", lambda: pytest.fail("invalid options must not inspect galleries"))
    assert cli.screenshot_main([*arguments, "--json"]) == 1
    assert not json.loads(capsys.readouterr().out)["ok"]


def test_all_empty_and_text_reports_are_complete(monkeypatch, capsys):
    monkeypatch.setattr(cli, "projects", lambda: [])
    assert cli.screenshot_main(["--all", "--check"]) == 0
    assert capsys.readouterr().out == "0 fresh, 0 stale, 0 failed\n"


@pytest.mark.parametrize("state", ["default", "malformed", "dangling", "catalog-only", "linked-plan", "bad-plan"])
def test_all_checks_manifest_only_and_catalog_galleries(owner, monkeypatch, capsys, state):
    recorded(owner)
    (owner / capture.PLAN).unlink()
    if state == "linked-plan":
        (owner / capture.PLAN).symlink_to(owner / "missing-plan")
    elif state == "bad-plan":
        (owner / capture.PLAN).write_text("not valid TOML]")
    elif state == "malformed":
        (owner / capture.MANIFEST).write_text("not JSON")
    elif state in {"dangling", "catalog-only"}:
        (owner / capture.MANIFEST).unlink()
        if state == "dangling":
            (owner / capture.MANIFEST).symlink_to(owner / "missing-manifest")
    project = cli.Project(owner, "heinzel-harbor", "0.1.0", capture.project_data(owner))
    monkeypatch.setattr(cli, "projects", lambda: [project])
    assert cli.screenshot_main(["--all", "--json"], check=True) == 1
    report = json.loads(capsys.readouterr().out)
    key = "failed"  # deterministic format requires an explicit definition, never silently skips media
    assert len(report[key]) == 1
    assert sum(len(report[key]) for key in ("fresh", "stale", "failed")) == 1


@pytest.mark.parametrize("indication", ["plan", "manifest", "linked-plan", "linked-manifest", "catalog"])
def test_single_and_aggregate_use_the_same_gallery_discovery(owner, monkeypatch, capsys, indication):
    if indication == "catalog":
        metadata = {"tool": {"heinzel": {"catalog": {"screenshots": [{"path": "missing.png"}]}}}}
    else:
        metadata = {}
        relative = capture.PLAN if indication.endswith("plan") else capture.MANIFEST
        path = owner / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if indication.startswith("linked"):
            path.symlink_to(owner / "missing-input")
        else:
            path.write_text("malformed input")
    project = cli.Project(owner, "heinzel-harbor", "0.1.0", metadata)
    called = []

    def checked(item):
        called.append(item)
        raise privacy.CaptureError("Broken configured gallery")

    monkeypatch.setattr(cli.vendor, "project", lambda *_: None)
    monkeypatch.setattr(cli, "check_screenshots", checked)
    with pytest.raises(privacy.CaptureError, match="Broken configured gallery"):
        cli.check(project, None, fast=True)
    assert cli.check_all_screenshots([project], json_output=True) == 1
    assert called == [project, project]
    assert json.loads(capsys.readouterr().out)["failed"][0]["plugin"] == project.name


def test_canonical_capture_requires_external_terms(monkeypatch):
    from heinzel_plugin_tools import capture_linux

    monkeypatch.setattr(capture_linux, "_confidentiality_module", lambda: None)
    with pytest.raises(privacy.CaptureError, match="configured confidential terms"):
        capture_linux.configured_terms()


@pytest.mark.parametrize(("failed", "private_text"), [(False, False), (True, False), (False, True)])
def test_canonical_linux_runs_exact_image_without_host_state_and_keeps_all_text(
    owner, monkeypatch, failed, private_text
):
    from heinzel_plugin_tools import capture as capture_module
    from heinzel_plugin_tools import capture_linux

    recorded(owner)
    wheel = owner / "heinzel-0.9.8-py3-none-any.whl"
    wheel.write_bytes(b"fictional wheel")
    (owner / ".venv").mkdir()
    (owner / ".venv/host-secret").write_text("not an input")
    (owner / ".env").write_text("host-only")
    before = (owner / capture.MANIFEST).read_bytes()
    calls = []
    first_scene = capture.read_plan(owner)["scenes"][0]["name"]
    monkeypatch.setattr(capture_linux, "configured_terms", lambda: "fictional-private-term\n")

    def run(argv, *, cwd, capture=False, capture_stderr=False, timeout=900):
        calls.append(argv)
        if argv[1] == "rm":
            assert argv[2] == "--force" and argv[3].startswith("hz-gallery-")
            return SimpleNamespace(returncode=0)
        assert argv[1:3] == ["run", "--rm"]
        assert capture_linux.IMAGE in argv
        assert argv[argv.index("--hostname") + 1] == "demo-host"
        assert argv[argv.index("--user") + 1] == f"{os.getuid()}:{os.getgid()}"
        assert "HOME=/capture/home" in argv and "UV_CACHE_DIR=/capture/cache" in argv
        assert (cwd / "home").is_dir() and (cwd / "bootstrap").is_dir()
        assert argv[argv.index("--platform") + 1] == "linux/amd64"
        assert str(owner) not in " ".join(argv)
        assert "fictional-private-term" not in " ".join(argv)
        assert "CONFIDENTIALITY_REQUIRED=false" in argv
        assert "CONFIDENTIAL_TERMS_FILE=/dev/null" in argv
        assert not (cwd / "terms").exists()
        assert not any("docker.sock" in item or "/Applications" in item for item in argv)
        assert "--verify" in argv and "--container-worker" in argv
        assert not (cwd / "project/.venv").exists()
        assert not (cwd / "project/.env").exists()
        assert (cwd / "core" / wheel.name).read_bytes() == wheel.read_bytes()
        folder = draft_of(cwd / "project")
        # An untrusted renderer must never arrange host-side Git execution.
        config = cwd / "project/.git/config"
        config.parent.mkdir()
        config.write_text("[core]\nfsmonitor = /untrusted-worker-command\n")
        original_inventory = capture_module.candidate_files

        def inventory(path):
            assert path != cwd / "project", "Host discovery must not read worker-controlled Git metadata"
            return original_inventory(path)

        monkeypatch.setattr(capture_module, "candidate_files", inventory)
        (folder / "index.html").write_text("Fictional contact sheet")
        if private_text:
            (folder / (first_scene + ".txt")).write_text("fictional-capture-canary-8329")
        return SimpleNamespace(
            returncode=1 if failed else 0,
            stdout=json.dumps(
                {
                    "ok": not failed,
                    "error": "a real scene differs",
                    "verified": True,
                    "preview": "/capture/project/.preview/screenshots/draft/index.html",
                }
            ),
        )

    monkeypatch.setattr(capture_linux, "command", run)
    args = SimpleNamespace(project=owner, core=str(wheel), headed=False, verify=True, draft=False, strict_images=False)
    if private_text:
        with pytest.raises(privacy.CaptureError):
            capture_linux.run(args)
        assert not (owner / capture.DRAFT).exists()
    elif failed:
        with pytest.raises(privacy.CaptureError, match="real scene differs"):
            capture_linux.run(args)
    else:
        assert capture_linux.run(args)["capture_platform"] == "linux/amd64"
    assert len(calls) == 2
    assert (owner / capture.MANIFEST).read_bytes() == before
    if not private_text:
        for scene in capture.read_plan(owner)["scenes"]:
            assert (
                owner / capture.DRAFT / (scene["name"] + ".txt")
            ).read_text() == "Fictional screenshot test transcript\n"


def test_imported_linux_draft_refuses_destination_links_before_writing_any_scene(owner, tmp_path):
    from heinzel_plugin_tools import capture_linux

    recorded(owner)
    source = owner.parent / (owner.name + "-isolated")
    shutil.copytree(owner, source)
    draft = draft_of(source)
    (draft / "index.html").write_text("Fictional contact sheet")
    target = owner / capture.DRAFT
    target.mkdir(parents=True)
    outside = tmp_path / "unrelated"
    outside.write_text("unchanged")
    plan = capture.read_plan(owner)
    (target / f"{plan['scenes'][-1]['name']}.txt").symlink_to(outside)
    with pytest.raises(privacy.CaptureError, match="symbolic links"):
        capture_linux.copy_draft(source, owner, plan)
    assert outside.read_text() == "unchanged"
    assert not (target / f"{plan['scenes'][0]['name']}.png").exists()


def test_installed_tooling_keeps_the_exact_external_terms_scanner(tmp_path, monkeypatch):
    package = tmp_path / "installed/heinzel_plugin_tools"
    package.mkdir(parents=True)
    original = Path(privacy.__file__).resolve().parents[2] / "scripts/check_confidentiality.py"
    bundled = package / "_confidentiality.py"
    bundled.write_bytes(original.read_bytes())
    monkeypatch.setattr(privacy, "__file__", str(package / "privacy.py"))
    monkeypatch.setenv("CONFIDENTIAL_TERMS", "fictional-secret-marker")
    scanner = privacy._confidentiality_module()
    assert Path(scanner.__file__) == bundled
    assert scanner.load_terms() == ["fictional-secret-marker"]
    with pytest.raises(privacy.CaptureError):
        capture.scan_text("FICTIONAL-SECRET-MARKER")


@pytest.mark.parametrize("failed", [False, True])
def test_zero_secret_render_check_never_reads_policy_or_publishes_unscanned_data(owner, monkeypatch, failed):
    from heinzel_plugin_tools import capture_linux

    recorded(owner)
    before = (owner / capture.MANIFEST).read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("the untrusted render path must not access private policy or publish")

    monkeypatch.setattr(capture_linux, "configured_terms", forbidden)
    monkeypatch.setattr(capture, "check_capture", forbidden)
    monkeypatch.setattr(capture_linux, "copy_draft", forbidden)
    monkeypatch.setattr(capture, "publish_draft", forbidden)

    def run(argv, *, cwd, capture=False, capture_stderr=False, timeout=900):
        if argv[1] == "rm":
            return SimpleNamespace(returncode=0)
        assert capture_stderr
        assert "CONFIDENTIALITY_REQUIRED=false" in argv
        assert "CONFIDENTIAL_TERMS_FILE=/dev/null" in argv and not (cwd / "terms").exists()
        assert "--verify" in argv
        return SimpleNamespace(
            returncode=int(failed),
            stdout=json.dumps(
                {
                    "ok": True,
                    "verified": True,
                    "screenshots": [{"caption": "unscanned-caption"}],
                    "transcripts_differ": [],
                    "images_differ": [],
                    "error": "unscanned-error",
                }
            ),
        )

    monkeypatch.setattr(capture_linux, "command", run)
    args = SimpleNamespace(
        project=owner, core=None, headed=False, verify=True, draft=False, strict_images=False, render_check=True
    )
    if failed:
        with pytest.raises(privacy.CaptureError, match="Zero-secret rendering comparison failed"):
            capture_linux.run(args)
    else:
        report = capture_linux.run(args)
        assert report["render_verified"] is True and report["private_scan"] is False
        assert "verified" not in report and report["scope"] == "render-only"
        assert "unscanned" not in json.dumps(report) and report["fresh"] is False
    assert (owner / capture.MANIFEST).read_bytes() == before and not (owner / capture.DRAFT).exists()


def test_render_check_failure_never_reads_host_private_policy_or_prints_unscanned_error(owner, monkeypatch, capsys):
    from heinzel_plugin_tools import capture_linux

    def fail(args):
        raise privacy.CaptureError("unscanned-provider-output")

    def forbidden(*args, **kwargs):
        raise AssertionError("render-only failure must not read confidential policy")

    monkeypatch.setattr(capture_linux, "run", fail)
    monkeypatch.setattr(capture, "safe_failure_message", forbidden)
    monkeypatch.setattr(sys, "argv", ["capture", "--project", str(owner), "--render-check", "--json"])
    assert capture.main() == 1
    shown = capsys.readouterr()
    report = json.loads(shown.out)
    assert report["scope"] == "render-only" and report["private_scan"] is False
    assert "unscanned-provider-output" not in shown.out + shown.err


def test_capture_retains_full_private_dom_evidence_without_changing_visible_transcript(tmp_path, monkeypatch):
    class Page:
        url = "http://127.0.0.1/fixture"

        def locator(self, selector):
            return SimpleNamespace(inner_text=lambda: "Visible body", evaluate_all=lambda script: "form-only-value")

        def title(self):
            return "Fixture title"

        def screenshot(self, *, path, **kwargs):
            Path(path).write_bytes(b"\x89PNG\r\n\x1a\nfixture")

    monkeypatch.setattr(capture, "redact_auth_presentation", lambda *a, **k: None)
    sidecar = tmp_path / "scene.scan.txt"
    body = capture.safe_screenshot(Page(), tmp_path / "scene.png", scan_path=sidecar)
    assert body == "Visible body"
    assert sidecar.read_text() == "Visible body\nform-only-value\nFixture title\nhttp://127.0.0.1/fixture"
    assert sidecar.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("tamper_hash", [False, True])
def test_private_form_sidecar_blocks_publication_even_when_body_is_clean(owner, tamper_hash):
    recorded(owner)
    folder = draft_of(owner)
    plan = capture.read_plan(owner)
    sidecar = folder / f"{plan['scenes'][0]['name']}.scan.txt"
    sidecar.write_text("fictional-capture-canary-8329")
    manifest = json.loads((folder / capture.DRAFT_MANIFEST).read_text())
    if not tamper_hash:
        manifest["scan_text"][sidecar.name] = hashlib.sha256(sidecar.read_bytes()).hexdigest()
        (folder / capture.DRAFT_MANIFEST).write_text(json.dumps(manifest))
    before = (owner / capture.MANIFEST).read_bytes()
    with pytest.raises(privacy.CaptureError):
        capture.publish_draft(owner)
    assert (owner / capture.MANIFEST).read_bytes() == before
    assert not list((owner / capture.OUTPUT).glob("*.scan.txt"))


def test_successful_publication_never_publishes_private_scan_evidence(owner):
    recorded(owner)
    folder = draft_of(owner)
    capture.publish_draft(owner)
    assert list(folder.glob("*.scan.txt"))
    assert not list((owner / capture.OUTPUT).glob("*.scan.txt"))
    assert "scan_text" not in json.loads((owner / capture.MANIFEST).read_text())


def test_canonical_snapshot_preserves_declared_inputs_and_ignores_build_output(owner, tmp_path):
    capture.write_default_plan(owner)
    view = owner / "src/heinzel_harbor/views"
    view.mkdir()
    tracked = view / "[original].js"
    tracked.write_text("original view")
    (owner / ".gitignore").write_text("src/heinzel_harbor/views/\n")
    subprocess.run(["git", "init", "--quiet", "--template=", str(owner)], check=True)  # noqa: S603,S607 -- fixed fixture Git command
    subprocess.run(["git", "-C", str(owner), "add", "--force", str(tracked)], check=True)  # noqa: S603,S607 -- fixed fixture Git command
    plan = capture.read_plan(owner)
    before = capture.input_digest(owner, plan)
    project = tmp_path / "copy"
    shutil.copytree(owner, project, ignore=shutil.ignore_patterns(".git", "copy"))
    source_files = capture.candidate_files(owner)
    assert not (project / ".git").exists()
    (project / "src/heinzel_harbor/views/generated.js").write_text("built asset")
    assert capture.input_digest(project, plan, source_files=source_files) == before
    assert "src/heinzel_harbor/views/[original].js" in source_files
    (project / "src/heinzel_harbor/views/[original].js").write_text("changed source")
    assert capture.input_digest(project, plan, source_files=source_files) != before
