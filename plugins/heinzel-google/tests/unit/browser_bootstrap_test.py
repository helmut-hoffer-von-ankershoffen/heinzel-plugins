"""Cold owning browser setup must use the pinned package and preserve cache isolation."""

import json
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
        package = support.browser_package()
    finally:
        support.browser_package.cache_clear()
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
    monkeypatch.setattr(support, "browser_package", lambda: tmp_path / "package.json")
    calls = []

    def run(command, **keywords):
        calls.append((command, keywords))
        return subprocess.CompletedProcess(command, 0, stderr=b"")

    monkeypatch.setattr(support.subprocess, "run", run)
    support.run_installed_browser(Path(__file__), "fixture", tmp_path, "webkit")
    assert calls[0][1]["env"]["PLAYWRIGHT_BROWSERS_PATH"] == str(cache)
    assert calls[0][1]["env"]["HZ_TEST_BROWSER_CACHE"] == str(cache)
