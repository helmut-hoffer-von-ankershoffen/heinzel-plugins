"""Release notes come from the changelogs and never silently drop a plugin from a plugin or app release."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_notes", ROOT / "scripts/release_notes.py")
notes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(notes)


def plugin(root, name, version, changelog):
    directory = root / "plugins" / name
    directory.mkdir(parents=True)
    (directory / "pyproject.toml").write_text(f'[project]\nname = "{name}"\nversion = "{version}"\n')
    if changelog is not None:
        (directory / "CHANGELOG.md").write_text(changelog)


def profile(version, **plugins):
    artifacts = [{"name": "heinzel", "version": version}]
    artifacts += [{"name": name, "version": plugin_version} for name, plugin_version in plugins.items()]
    return {"format": 2, "sdk": 1, "core_version": version, "artifacts": artifacts}


@pytest.fixture
def root(tmp_path):
    plugin(
        tmp_path,
        "heinzel-clock",
        "0.3.0",
        "# Changelog\n\n## Unreleased\n\n## 0.3.0\n\n- Three.\n\n## 0.2.0\n\n- Two.\n\n## 0.1.0\n\n- One.\n",
    )
    plugin(tmp_path, "heinzel-weather", "0.5.0", "# Changelog\n\n## 0.5.0\n\n- Rain.\n")
    return tmp_path


def test_plugin_notes_print_the_version_section(root, capsys):
    assert notes.main(["plugin", "heinzel-clock"], root) == 0
    assert capsys.readouterr().out == "- Three.\n"
    assert notes.main(["plugin", "clock", "--version", "0.2.0"], root) == 0
    assert capsys.readouterr().out == "- Two.\n"


@pytest.mark.parametrize("arguments", [["heinzel-clock", "--version", "0.9.0"], ["heinzel-missing"]])
def test_plugin_notes_fail_without_a_section(root, capsys, arguments):
    assert notes.main(["plugin", *arguments], root) == 1
    assert capsys.readouterr().out == ""


def test_app_notes_list_changes_with_every_skipped_section_and_unchanged_plugins(root):
    body = notes.app_notes(
        root,
        "1.2.0",
        profile("1.2.0", **{"heinzel-clock": "0.3.0", "heinzel-weather": "0.5.0"}),
        profile("1.1.0", **{"heinzel-clock": "0.1.0", "heinzel-weather": "0.5.0", "heinzel-gone": "0.1.0"}),
        "app-v1.1.0",
    )
    assert "https://github.com/helmut-hoffer-von-ankershoffen/heinzel/releases/tag/v1.2.0" in body
    assert "app-v1.1.0" in body
    assert "### heinzel-clock 0.1.0 -> 0.3.0" in body
    assert body.index("- Three.") < body.index("- Two.")
    assert "- One." not in body
    assert "- heinzel-weather 0.5.0\n" in body
    assert "- heinzel-gone 0.1.0 -> removed" in body
    assert "Rain" not in body


def test_without_a_previous_app_every_plugin_is_new(root):
    body = notes.app_notes(
        root, "1.2.0", profile("1.2.0", **{"heinzel-clock": "0.3.0", "heinzel-weather": "0.5.0"}), None
    )
    assert "every plugin is listed as new" in body
    assert "### heinzel-clock new -> 0.3.0" in body
    assert "### heinzel-weather new -> 0.5.0" in body
    assert "Unchanged" not in body


def test_an_edge_app_links_its_edge_core():
    assert notes.core_link("1.3.0.dev4").endswith("/releases/tag/edge-v1.3.0.dev4")


@pytest.mark.parametrize("version", ["0.4.0", None])
def test_a_changed_plugin_without_its_section_stops_the_app_notes(root, version):
    if version is None:
        (root / "plugins/heinzel-weather/CHANGELOG.md").unlink()
        current = profile("1.2.0", **{"heinzel-weather": "0.5.0"})
    else:
        current = profile("1.2.0", **{"heinzel-clock": version})
    with pytest.raises(notes.NotesError):
        notes.app_notes(root, "1.2.0", current, profile("1.1.0"), "app-v1.1.0")


def test_oversized_notes_keep_every_plugin_line(root, monkeypatch, capsys):
    (root / "plugins/heinzel-weather/CHANGELOG.md").write_text("## 0.5.0\n\n" + "- Rain.\n" * 100)
    current = profile("1.2.0", **{"heinzel-clock": "0.3.0", "heinzel-weather": "0.5.0"})
    compact = notes.app_notes(root, "1.2.0", current, None, compact=True)
    assert len(compact) < len(notes.app_notes(root, "1.2.0", current, None))
    monkeypatch.setattr(notes, "BODY_LIMIT", len(compact))
    body = notes.app_notes(root, "1.2.0", current, None)
    assert body == compact
    assert "without its changelog text" in capsys.readouterr().err
    assert "### heinzel-clock new -> 0.3.0" in body
    assert "### heinzel-weather new -> 0.5.0" in body
    assert "- Three." not in body
    assert "plugins/heinzel-clock/CHANGELOG.md" in body


def test_app_cli_refuses_a_profile_for_another_version(root, tmp_path, capsys):
    current = tmp_path / "standard.json"
    current.write_text(json.dumps(profile("1.1.0")))
    assert notes.main(["app", "1.2.0", "--profile", str(current), "--previous", str(current)], root) == 1
    assert "not 1.2.0" in capsys.readouterr().err


def test_previous_final_app_skips_drafts_prereleases_and_newer_apps(monkeypatch):
    content = json.dumps(profile("1.1.0", **{"heinzel-clock": "0.1.0"})).encode()
    asset = {"name": "standard.json", "digest": "sha256:" + hashlib.sha256(content).hexdigest()}
    releases = [
        {"tag_name": "app-v1.3.0", "assets": [asset]},
        {"tag_name": "app-v1.2.0", "assets": [asset]},
        {"tag_name": "app-v1.1.5", "prerelease": True, "assets": [asset]},
        {"tag_name": "app-v1.1.4", "draft": True, "assets": [asset]},
        {"tag_name": "heinzel-clock/v0.2.0", "assets": []},
        {"tag_name": "app-v1.1.0", "assets": [asset]},
        {"tag_name": "app-v1.0.0", "assets": [asset]},
    ]
    fetched = []
    monkeypatch.setattr(notes, "api", lambda path, **_: releases if "page=1" in path else [])
    monkeypatch.setattr(notes, "fetch_bytes", lambda url, **_: fetched.append(url) or (url, content))
    tag, previous = notes.previous_final_app("example/plugins", "1.2.0")
    assert tag == "app-v1.1.0"
    assert previous["core_version"] == "1.1.0"
    assert fetched == ["https://github.com/example/plugins/releases/download/app-v1.1.0/standard.json"]


def test_previous_final_app_with_a_different_profile_digest_fails(monkeypatch):
    releases = [{"tag_name": "app-v1.1.0", "assets": [{"name": "standard.json", "digest": "sha256:" + "0" * 64}]}]
    monkeypatch.setattr(notes, "api", lambda *_, **__: releases)
    monkeypatch.setattr(notes, "fetch_bytes", lambda url, **_: (url, b"{}"))
    with pytest.raises(notes.NotesError, match="digest"):
        notes.previous_final_app("example/plugins", "1.2.0")


def test_no_previous_final_app(monkeypatch):
    monkeypatch.setattr(notes, "api", lambda *_, **__: [])
    assert notes.previous_final_app("example/plugins", "1.2.0") == (None, None)


def test_notes_that_cannot_fit_stop(root, monkeypatch):
    monkeypatch.setattr(notes, "BODY_LIMIT", 10)
    with pytest.raises(notes.NotesError, match="limit"):
        notes.app_notes(root, "1.2.0", profile("1.2.0", **{"heinzel-clock": "0.3.0"}), None)


def test_a_github_failure_stops_the_app_notes_cleanly(root, tmp_path, monkeypatch, capsys):
    current = tmp_path / "standard.json"
    current.write_text(json.dumps(profile("1.2.0")))
    monkeypatch.setenv("GH_REPO", "example/plugins")

    def api(path, **_):
        raise ValueError(f"GitHub request failed for {path}: HTTP 502")

    monkeypatch.setattr(notes, "api", api)
    assert notes.main(["app", "1.2.0", "--profile", str(current)], root) == 1
    assert "Release notes stopped: GitHub request failed" in capsys.readouterr().err
