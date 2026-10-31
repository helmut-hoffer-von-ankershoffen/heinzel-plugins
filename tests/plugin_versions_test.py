"""A version bump that ships nothing broke app-v0.9.9's composition; it must fail at merge time instead."""

import importlib.util
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("plugin_versions", ROOT / "scripts/plugin_versions.py")
versions = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(versions)
PROJECT = '[project]\nname = "heinzel-a"\nversion = "{version}"\n{extra}'


def git(*arguments, cwd):
    # A pre-push hook exports GIT_DIR and friends, and global hooks would scan these throwaway commits.
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    return subprocess.run(  # noqa: S603 - fixed git in a temporary test repository
        ["git", "-c", "core.hooksPath=/dev/null", *arguments],  # noqa: S607
        cwd=cwd,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout


def repository(tmp_path, monkeypatch):
    for key in [key for key in os.environ if key.startswith("GIT_")]:
        monkeypatch.delenv(key)
    plugin = tmp_path / "plugins/heinzel-a"
    (plugin / "src").mkdir(parents=True)
    (plugin / "docs").mkdir()
    (plugin / "pyproject.toml").write_text(PROJECT.format(version="0.1.0", extra=""))
    (plugin / "src/a.py").write_text("a = 1\n")
    (plugin / "docs/a.md").write_text("one\n")
    git("init", "-q", "-b", "main", cwd=tmp_path)
    git("add", ".", cwd=tmp_path)
    git("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "base", cwd=tmp_path)
    git("tag", "base", cwd=tmp_path)
    monkeypatch.chdir(tmp_path)
    return plugin


def commit(tmp_path):
    git("add", ".", cwd=tmp_path)
    git("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "change", cwd=tmp_path)


def test_a_docs_change_cannot_bump_a_version(tmp_path, monkeypatch):
    plugin = repository(tmp_path, monkeypatch)
    (plugin / "docs/a.md").write_text("two\n")
    (plugin / "pyproject.toml").write_text(PROJECT.format(version="0.1.1", extra=""))
    commit(tmp_path)
    assert versions.unjustified_bumps("base") == ["heinzel-a"]
    assert versions.main(["check", "base"]) == 1


def test_a_source_change_may_bump_a_version(tmp_path, monkeypatch):
    plugin = repository(tmp_path, monkeypatch)
    (plugin / "src/a.py").write_text("a = 2\n")
    (plugin / "pyproject.toml").write_text(PROJECT.format(version="0.1.1", extra=""))
    commit(tmp_path)
    assert versions.main(["check", "base"]) == 0


def test_a_metadata_change_may_bump_a_version(tmp_path, monkeypatch):
    plugin = repository(tmp_path, monkeypatch)
    (plugin / "pyproject.toml").write_text(PROJECT.format(version="0.1.1", extra='description = "new"\n'))
    commit(tmp_path)
    assert versions.unjustified_bumps("base") == []


def test_docs_without_a_bump_pass(tmp_path, monkeypatch):
    plugin = repository(tmp_path, monkeypatch)
    (plugin / "docs/a.md").write_text("two\n")
    commit(tmp_path)
    assert versions.unjustified_bumps("base") == []


def test_unreleased_lists_versions_without_a_tag(tmp_path, monkeypatch):
    repository(tmp_path, monkeypatch)
    assert versions.unreleased(tmp_path, set()) == ["heinzel-a"]
    assert versions.unreleased(tmp_path, {"heinzel-a/v0.1.0"}) == []
