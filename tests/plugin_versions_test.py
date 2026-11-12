"""A version bump that ships nothing broke app-v0.9.9's composition, and a shipped change without a bump never
reached a release; both must fail at merge time instead."""

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

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


def changelog(*versions):
    return "# Changelog\n\n" + "".join(f"## {version}\n\n- Change {version}.\n\n" for version in versions)


def bump(plugin, version="0.1.1", extra="", notes=True):
    (plugin / "pyproject.toml").write_text(PROJECT.format(version=version, extra=extra))
    if notes:
        (plugin / "CHANGELOG.md").write_text(changelog(version, "0.1.0"))


def repository(tmp_path, monkeypatch):
    for key in [key for key in os.environ if key.startswith("GIT_")]:
        monkeypatch.delenv(key)
    plugin = tmp_path / "plugins/heinzel-a"
    (plugin / "src").mkdir(parents=True)
    (plugin / "docs").mkdir()
    (plugin / "pyproject.toml").write_text(PROJECT.format(version="0.1.0", extra=""))
    (plugin / "src/a.py").write_text("a = 1\n")
    (plugin / "docs/a.md").write_text("one\n")
    (plugin / "CHANGELOG.md").write_text(changelog("0.1.0"))
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
    bump(plugin)
    commit(tmp_path)
    assert versions.unjustified_bumps("base") == ["heinzel-a"]
    assert versions.main(["check", "base"]) == 1


def test_a_source_change_may_bump_a_version(tmp_path, monkeypatch):
    plugin = repository(tmp_path, monkeypatch)
    (plugin / "src/a.py").write_text("a = 2\n")
    bump(plugin)
    commit(tmp_path)
    assert versions.main(["check", "base"]) == 0


def test_a_metadata_change_may_bump_a_version(tmp_path, monkeypatch):
    plugin = repository(tmp_path, monkeypatch)
    bump(plugin, extra='description = "new"\n')
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


def test_a_revision_cannot_be_read_as_a_git_option():
    with pytest.raises(ValueError, match="plain commit"):
        versions.unjustified_bumps("--output=/tmp/x")


def test_a_source_change_without_a_bump_fails(tmp_path, monkeypatch):
    plugin = repository(tmp_path, monkeypatch)
    (plugin / "src/a.py").write_text("a = 2\n")
    commit(tmp_path)
    assert versions.unbumped_changes("base") == ["heinzel-a"]
    assert versions.main(["check", "base"]) == 1


def test_a_shipped_metadata_change_without_a_bump_fails(tmp_path, monkeypatch):
    plugin = repository(tmp_path, monkeypatch)
    (plugin / "pyproject.toml").write_text(PROJECT.format(version="0.1.0", extra='description = "new"\n'))
    commit(tmp_path)
    assert versions.unbumped_changes("base") == ["heinzel-a"]


def test_a_source_change_with_a_bump_passes(tmp_path, monkeypatch):
    plugin = repository(tmp_path, monkeypatch)
    (plugin / "src/a.py").write_text("a = 2\n")
    bump(plugin)
    commit(tmp_path)
    assert versions.unbumped_changes("base") == []
    assert versions.main(["check", "base"]) == 0


def test_docs_and_tests_never_need_a_bump(tmp_path, monkeypatch):
    plugin = repository(tmp_path, monkeypatch)
    (plugin / "docs/a.md").write_text("two\n")
    (plugin / "tests").mkdir()
    (plugin / "tests/a_test.py").write_text("pass\n")
    commit(tmp_path)
    assert versions.unbumped_changes("base") == []


@pytest.mark.parametrize(
    "text",
    [
        None,  # no changelog line at all
        "# Changelog\n\n## 0.1.0\n\n- Old.\n",  # the old version still on top
        "# Changelog\n\n## 0.1.1\n\n## 0.1.0\n\n- Old.\n",  # an empty section
        "# Changelog\n\n## Unreleased\n\n- New.\n\n## 0.1.1\n\n- New.\n",  # not the top section
    ],
)
def test_a_bump_without_its_changelog_section_fails(tmp_path, monkeypatch, text):
    plugin = repository(tmp_path, monkeypatch)
    (plugin / "src/a.py").write_text("a = 2\n")
    bump(plugin, notes=False)
    if text is not None:
        (plugin / "CHANGELOG.md").write_text(text)
    commit(tmp_path)
    assert versions.missing_changelogs("base") == ["heinzel-a"]
    assert versions.main(["check", "base"]) == 1


def test_a_bump_with_its_changelog_section_passes(tmp_path, monkeypatch):
    plugin = repository(tmp_path, monkeypatch)
    (plugin / "src/a.py").write_text("a = 2\n")
    bump(plugin)
    commit(tmp_path)
    assert versions.missing_changelogs("base") == []


def test_a_new_plugin_needs_its_first_changelog_section(tmp_path, monkeypatch):
    repository(tmp_path, monkeypatch)
    other = tmp_path / "plugins/heinzel-b"
    (other / "src").mkdir(parents=True)
    (other / "pyproject.toml").write_text(PROJECT.format(version="0.1.0", extra="").replace("heinzel-a", "heinzel-b"))
    (other / "src/b.py").write_text("b = 1\n")
    commit(tmp_path)
    assert versions.missing_changelogs("base") == ["heinzel-b"]
    (other / "CHANGELOG.md").write_text(changelog("0.1.0"))
    commit(tmp_path)
    assert versions.missing_changelogs("base") == []


def test_unbumped_plugins_need_no_new_section(tmp_path, monkeypatch):
    plugin = repository(tmp_path, monkeypatch)
    (plugin / "docs/a.md").write_text("two\n")
    commit(tmp_path)
    assert versions.missing_changelogs("base") == []


def test_changelog_sections_keep_their_text_and_order():
    text = "# Changelog\n\n## Unreleased\n\n## 0.2.0\n\n- Two.\n  More.\n\n## 0.1.0\n\n- One.\n"
    assert versions.changelog_sections(text) == [("Unreleased", ""), ("0.2.0", "- Two.\n  More."), ("0.1.0", "- One.")]
    assert versions.changelog_section(text, "0.1.0") == "- One."
    assert versions.changelog_section(text, "0.3.0") == ""
