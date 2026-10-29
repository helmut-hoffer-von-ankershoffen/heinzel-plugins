"""Install Heinzelmännchen with `uv tool install`, add this plugin from the checkout, use it. Needs network.

Run with `make acceptance NAME=example CORE=<compatible-built-core-wheel>`; both installed artifacts are explicit.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.timeout(300)]

REPO = Path(__file__).resolve().parents[2]
CORE_SPEC = os.environ.get(
    "PLUGIN_TEST_CORE", "heinzel==" + json.loads((REPO / "plugin-lock.json").read_text())["core"]["version"]
)
OWN_WHEEL = Path(os.environ.get("PLUGIN_TEST_WHEEL", "."))


@pytest.fixture(scope="module")
def hz(tmp_path_factory):
    root = tmp_path_factory.mktemp("uv-tools")
    env = {key: value for key, value in os.environ.items() if not key.startswith("HZ_")}
    env |= {"UV_TOOL_DIR": str(root / "tools"), "UV_TOOL_BIN_DIR": str(root / "bin"), "HZ_PLUGINS_ENABLED": "true"}
    for key in ("CONFIG_HOME", "DATA_DIR", "CACHE_DIR", "STATE_DIR", "LOG_DIR"):
        env[f"HZ_{key}"] = str(root / key.lower())
    env["HZ_SYSTEM_CREDENTIAL__BACKEND"] = "environment"
    env["HZ_SYSTEM_DAEMON__UNIT_DIR"] = str(root / "units")
    env.pop("VIRTUAL_ENV", None)
    uv = shutil.which("uv")
    assert uv, "uv is not on PATH: https://docs.astral.sh/uv/"
    subprocess.run([uv, "tool", "install", CORE_SPEC, "--with", str(OWN_WHEEL)], check=True, env=env, timeout=240)

    def run(*args: str) -> str:
        result = subprocess.run(
            [str(root / "bin" / "hz"), *args], capture_output=True, text=True, check=False, env=env, timeout=240
        )
        assert result.returncode == 0, f"hz {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}"
        return result.stdout

    return run


def test_info(hz):
    about = json.loads(hz("example", "info", "--json"))
    assert about["plugin"] == "heinzel-example"


def test_hello(hz):
    assert json.loads(hz("example", "hello", "--name", "Ada", "--json")) == {"text": "Hello, Ada!"}


def test_listed_as_plugin(hz):
    plugins = json.loads(hz("system", "plugin", "list", "--json"))
    assert [p["distribution"] for p in plugins] == ["heinzel-example"]
