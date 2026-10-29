import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from heinzel import Kernel, Settings
from heinzel.heads import web
from heinzel.kernel import discover

import heinzel_theme

pytestmark = pytest.mark.e2e


@pytest.fixture
def installed(tmp_path):
    env = {key: value for key, value in os.environ.items() if not key.startswith("HZ_")}
    env.update(UV_TOOL_DIR=str(tmp_path / "tools"), UV_TOOL_BIN_DIR=str(tmp_path / "bin"), HZ_PLUGINS_ENABLED="true")
    for key in ("CONFIG_HOME", "DATA_DIR", "CACHE_DIR", "STATE_DIR", "LOG_DIR"):
        env[f"HZ_{key}"] = str(tmp_path / key.lower())
    env["HZ_SYSTEM_CREDENTIAL__BACKEND"] = "environment"
    env["HZ_SYSTEM_DAEMON__UNIT_DIR"] = str(tmp_path / "units")
    env.pop("VIRTUAL_ENV", None)
    uv = shutil.which("uv")
    assert uv
    subprocess.run(
        [uv, "tool", "install", os.environ["PLUGIN_TEST_CORE"], "--with", os.environ["PLUGIN_TEST_WHEEL"]],
        check=True,
        env=env,
        capture_output=True,
        timeout=240,
    )

    def run(*args):
        result = subprocess.run(
            [str(tmp_path / "bin/hz"), *args, "--json"],
            check=False,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)

    return run, tmp_path


def test_installed_catalog_is_complete_and_silent_by_default(installed):
    hz, _ = installed
    themes = hz("system", "theme", "list")
    assert themes["selected"] == "default"
    assert [(item["name"], item["plugin"]) for item in themes["themes"]] == [
        ("default", None),
        ("heinzelmaennchen", "heinzel-theme"),
    ]
    sounds = hz("system", "sound", "list")
    assert (sounds["selected"], sounds["effective"]) == ("off", "off")
    assert {item["name"] for item in sounds["soundscapes"]} == {"off", "claude-fm", "focus", "hyper-focus"}
    assert all(item["plugin"] == "heinzel-theme" for item in sounds["soundscapes"] if item["name"] != "off")
    assert [item["distribution"] for item in hz("system", "plugin", "list")] == ["heinzel-theme"]


def test_theme_pairing_disable_and_removal_use_only_generic_operations(installed):
    hz, _ = installed
    assert hz("system", "theme", "use", "heinzelmaennchen")["selected"] == "heinzelmaennchen"
    hz("system", "config", "set", "system.sound.follow_theme", "true")
    assert hz("system", "sound", "list")["effective"] == "focus"
    hz("system", "plugin", "disable", "heinzel-theme")
    assert hz("system", "theme", "list")["selected"] == "default"
    assert [item["name"] for item in hz("system", "sound", "list")["soundscapes"]] == ["off"]
    hz("system", "plugin", "enable", "heinzel-theme")
    assert hz("system", "sound", "use", "hyper-focus")["effective"] == "hyper-focus"
    hz("system", "plugin", "remove", "heinzel-theme")
    assert hz("system", "theme", "list")["selected"] == "default"
    assert hz("system", "sound", "list")["effective"] == "off"
    assert hz("system", "plugin", "list") == []


def test_packaged_theme_assets_are_served_by_the_generic_web_head():
    assert Path(heinzel_theme.__file__).resolve().is_relative_to(Path(sys.prefix))
    records, errors = discover(plugins=True)
    kernel = Kernel(Settings(), records, errors)
    client = TestClient(web.build(kernel, port=8000, token="theme-test"), base_url="http://127.0.0.1:8000")
    listed = client.get("/api/system/theme/list", headers={"Authorization": "Bearer theme-test"}).json()
    theme = next(item for item in listed["themes"] if item["name"] == "heinzelmaennchen")
    for key in ("light", "dark", "mark"):
        response = client.get(theme["logo"][key])
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/svg+xml")
        assert b"<svg" in response.content
