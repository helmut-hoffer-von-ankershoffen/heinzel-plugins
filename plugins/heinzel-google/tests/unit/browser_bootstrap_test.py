"""Cold owning browser setup must use the pinned package and preserve cache isolation."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.support import installed_browser_support as support

pytestmark = pytest.mark.unit


def test_cold_bootstrap_installs_both_locked_engines_without_lifecycle_scripts(monkeypatch):
    calls = []
    monkeypatch.setattr(support.shutil, "which", lambda _name: "/fixture/npm")
    monkeypatch.setattr(support.subprocess, "run", lambda command, **kw: calls.append((command, kw)))
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", "/private/fixture-cold-cache")
    support.browser_package.cache_clear()
    try:
        package, cache = support.browser_package()
    finally:
        support.browser_package.cache_clear()
    assert cache == Path("/private/fixture-cold-cache").resolve()
    assert calls[0][0] == ["/fixture/npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"]
    assert calls[1][0] == ["/fixture/npm", "run", "--ignore-scripts", "browser:install"]
    assert all(call[1]["check"] for call in calls)
    assert all(call[1]["env"]["PLAYWRIGHT_BROWSERS_PATH"] == "/private/fixture-cold-cache" for call in calls)
    declaration = json.loads(package.read_text())
    assert declaration["scripts"]["browser:install"] == "playwright-core install chromium webkit"
    assert declaration["scripts"]["browser:install-deps"] == "playwright-core install-deps chromium webkit"
    lock = json.loads(package.with_name("package-lock.json").read_text())
    assert (
        lock["packages"]["node_modules/playwright-core"]["version"] == declaration["devDependencies"]["playwright-core"]
    )


def test_installed_child_uses_explicit_cold_cache(tmp_path, monkeypatch):
    cache = tmp_path / "empty-browser-cache"
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(cache))
    monkeypatch.setattr(support, "browser_package", lambda: (tmp_path / "package.json", cache))
    calls = []

    def run(command, **keywords):
        calls.append((command, keywords))
        return subprocess.CompletedProcess(command, 0, stderr=b"")

    monkeypatch.setattr(support.subprocess, "run", run)
    support.run_installed_browser(Path(__file__), "fixture", tmp_path, "webkit")
    assert calls[0][1]["env"]["PLAYWRIGHT_BROWSERS_PATH"] == str(cache)
    assert calls[0][1]["env"]["HZ_TEST_BROWSER_CACHE"] == str(cache)


@pytest.mark.parametrize(
    "scenario",
    [
        ("darwin", None, None, False, "home/Library/Caches/ms-playwright"),
        ("linux", None, None, False, "home/.cache/ms-playwright"),
        ("linux", None, "/fixture/xdg", False, "/fixture/xdg/ms-playwright"),
        ("linux", None, "xdg", False, "cwd/xdg/ms-playwright"),
        ("linux", None, "xdg", True, "initial/xdg/ms-playwright"),
        ("linux", "relative-cache", None, False, "cwd/relative-cache"),
        ("linux", "relative-cache", None, True, "initial/relative-cache"),
        ("darwin", "0", None, False, "browser/node_modules/playwright-core/.local-browsers"),
    ],
)
def test_installer_and_isolated_child_share_resolved_cache(tmp_path, monkeypatch, scenario):
    platform, selected, xdg, initial, expected = scenario
    for name in ("PLAYWRIGHT_BROWSERS_PATH", "INIT_CWD"):
        for key in (name, f"npm_config_{name.lower()}", f"npm_package_config_{name.lower()}"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    directory = tmp_path / "browser"
    directory.mkdir()
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(support.sys, "platform", platform)
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    if selected is not None:
        monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", selected)
    if xdg is not None:
        monkeypatch.setenv("XDG_CACHE_HOME", xdg)
    if initial:
        monkeypatch.setenv("INIT_CWD", str(tmp_path / "initial"))
    # Redirect the owning package lookup, while preserving its normal tests/support layout.
    monkeypatch.setattr(support, "__file__", str(tmp_path / "support/installed_browser_support.py"))
    monkeypatch.setattr(support.shutil, "which", lambda _name: "/fixture/npm")
    calls = []

    def run(command, **keywords):
        calls.append((command, keywords))
        return subprocess.CompletedProcess(command, 0, stderr=b"")

    monkeypatch.setattr(support.subprocess, "run", run)
    support.browser_package.cache_clear()
    try:
        support.run_installed_browser(Path(__file__), "fixture", tmp_path, "webkit")
    finally:
        support.browser_package.cache_clear()
    resolved = str((tmp_path / expected).resolve())
    assert len(calls) == 3
    assert all(call[1]["env"]["PLAYWRIGHT_BROWSERS_PATH"] == resolved for call in calls)
    assert calls[-1][1]["env"]["HZ_TEST_BROWSER_CACHE"] == resolved
    assert calls[-1][1]["env"]["HOME"] == str(tmp_path / "isolated-home")
    assert "XDG_CACHE_HOME" not in calls[-1][1]["env"]
    assert "INIT_CWD" not in calls[-1][1]["env"]
    assert os.environ.get("PLAYWRIGHT_BROWSERS_PATH") == selected
