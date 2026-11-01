"""Exercise the installed wheel through the public CLI, outside the source directory."""

import json
import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.e2e


def test_installed_manifest(tmp_path):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("HZ_")}
    environment["HZ_PLUGINS_ENABLED"] = "true"
    environment.pop("PYTHONPATH", None)
    for key in ("CONFIG_HOME", "DATA_DIR", "CACHE_DIR", "STATE_DIR", "LOG_DIR"):
        environment[f"HZ_{key}"] = str(tmp_path / key.lower())
    result = subprocess.run(
        [sys.executable, "-m", "heinzel", "slack", "manifest", "--json"],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    manifest = json.loads(json.loads(result.stdout))
    assert manifest["settings"]["socket_mode_enabled"] is True
    assert manifest["oauth_config"]["scopes"]["bot"] == ["chat:write", "im:write", "users:read"]
