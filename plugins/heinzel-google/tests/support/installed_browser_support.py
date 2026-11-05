"""Run browser fixtures in a fresh process with installed source capture before plugin imports."""

import os
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import nodejs_wheel
import pytest

pytestmark = pytest.mark.e2e


def _playwright_env(name: str) -> str | None:
    for key in (name, f"npm_config_{name.lower()}", f"npm_package_config_{name.lower()}"):
        if key in os.environ:
            return os.environ[key]
    return None


def _browser_cache(directory: Path) -> Path:
    """Resolve the owning locked Playwright cache once, before npm changes cwd or the child changes HOME."""
    selected = _playwright_env("PLAYWRIGHT_BROWSERS_PATH")
    if selected == "0":
        cache = directory / "node_modules/playwright-core/.local-browsers"
    elif selected:
        cache = Path(selected)
    elif sys.platform == "darwin":
        cache = Path.home() / "Library/Caches/ms-playwright"
    elif sys.platform == "win32":
        cache = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local") / "ms-playwright"
    else:
        cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "ms-playwright"
    if not cache.is_absolute():
        cache = Path(_playwright_env("INIT_CWD") or Path.cwd()) / cache
    return cache.resolve()


@lru_cache(maxsize=1)
def browser_package() -> tuple[Path, Path]:
    """Install only this plugin's pinned browser test dependencies, with package scripts disabled."""
    directory = Path(__file__).resolve().parents[1] / "browser"
    cache = _browser_cache(directory)
    npm = shutil.which("npm")
    if npm is None:
        msg = "npm is required for the Google plugin's browser tests"
        raise RuntimeError(msg)
    node_bin = Path(nodejs_wheel.__file__).parent / "bin"
    environment = dict(
        os.environ,
        PATH=f"{node_bin}{os.pathsep}{os.environ.get('PATH', '')}",
        PLAYWRIGHT_BROWSERS_PATH=str(cache),
    )
    subprocess.run(
        [npm, "ci", "--ignore-scripts", "--no-audit", "--no-fund"],
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    subprocess.run(
        [npm, "run", "--ignore-scripts", "browser:install"],
        cwd=directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    return directory / "package.json", cache


def run_installed_browser(path: Path, function: str, root: Path, engine: str) -> None:
    package, cache = browser_package()
    script = r"""
import os, runpy, sys
from pathlib import Path
from heinzel.kernel import boot
boot()
sys.path.insert(0, os.environ['HZ_TEST_PLUGIN_TESTS'])
from pytest import MonkeyPatch
fixture = runpy.run_path(os.environ['HZ_TEST_SCRIPT'])
with MonkeyPatch.context() as patches:
    fixture[os.environ['HZ_TEST_FUNCTION']](
        boot, Path(os.environ['HZ_TEST_ROOT']), patches, os.environ['HZ_TEST_ENGINE']
    )
"""
    home = root / "isolated-home"
    home.mkdir()
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "HZ_CONFIG_HOME": str(root / "config"),
        "HZ_STATE_DIR": str(root / "state"),
        "HZ_DATA_DIR": str(root / "data"),
        "HZ_CACHE_DIR": str(root / "cache"),
        "HZ_LOG_DIR": str(root / "logs"),
        "HZ_TEST_ROOT": str(root),
        "HZ_TEST_SCRIPT": str(path),
        "HZ_TEST_FUNCTION": function,
        "HZ_TEST_ENGINE": engine,
        "HZ_TEST_PLUGIN_TESTS": str(path.parents[2]),
        "HZ_TEST_BROWSER_CACHE": str(cache),
        "PLAYWRIGHT_BROWSERS_PATH": str(cache),
        "HZ_TEST_BROWSER_PACKAGE": str(package),
    }
    result = subprocess.run(
        [sys.executable, "-I", "-c", script], env=env, capture_output=True, timeout=170, check=False
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
