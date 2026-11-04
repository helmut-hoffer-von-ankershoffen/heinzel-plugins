"""An actual built toolkit script runs from uv's package cache without adopting the consumer project."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("filename", ["capture.py", "cli.py"])
def test_built_capture_script_runs_from_uv_cache_with_pinned_script_dependencies(tmp_path, filename):
    uv = shutil.which("uv")
    assert uv is not None
    version = subprocess.check_output([uv, "--version"], text=True, timeout=10)  # noqa: S603 - locked tooling uv, fixed arguments
    assert version.startswith("uv 0.13.7 ")  # Installed by the root's locked tooling group.
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {"VIRTUAL_ENV", "PYTHONPATH", "UV_PROJECT_ENVIRONMENT"}
    }
    cache = tmp_path / "cache"
    environment["UV_CACHE_DIR"] = str(cache)
    dist = tmp_path / "dist"
    subprocess.run(  # noqa: S603 - locked tooling uv and private fixture paths
        [uv, "build", "--wheel", "--out-dir", str(dist)],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    [wheel] = dist.glob("heinzel_plugin_tools-*.whl")
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    (consumer / "pyproject.toml").write_text(
        '[project]\nname="unrelated-consumer"\nversion="1.0.0"\n'
        'dependencies=["capture-consumer-must-not-resolve==0.0.0"]\n'
    )
    discovered = subprocess.run(  # noqa: S603 - locked tooling uv and locally built wheel
        [
            uv,
            "run",
            "--quiet",
            "--no-project",
            "--python",
            sys.executable,
            "--with",
            str(wheel),
            "python",
            "-c",
            "import json,pathlib,heinzel_plugin_tools; "
            "print(json.dumps(str(pathlib.Path(heinzel_plugin_tools.__file__).parent/'capture.py')))",
        ],
        cwd=consumer,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    script = Path(json.loads(discovered.stdout)).with_name(filename)
    assert script.resolve().is_relative_to(cache.resolve())
    script_bytes = script.read_bytes()
    assert script_bytes == (ROOT / "src/heinzel_plugin_tools" / filename).read_bytes()
    forwarded = ["--project", str(consumer)] if filename == "capture.py" else ["setup", "harbor"]
    args = ["--script", str(script), *forwarded, "--core", "candidate.whl", "--help"]
    # Even --no-project alone is insufficient: uv rejects a script inside its configured cache.
    before = subprocess.run(  # noqa: S603 - actual packaged script with fixed help-only arguments
        [uv, "run", "--quiet", "--no-project", *args],
        cwd=consumer,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert before.returncode != 0
    assert "inside the cache directory" in before.stderr
    after = subprocess.run(  # noqa: S603 - same packaged script, isolated dependency environment
        [uv, "run", "--quiet", "--no-project", "--no-cache", *args],
        cwd=consumer,
        env=environment,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert after.returncode == 0, after.stderr
    assert "--core" in after.stdout
    assert ("--review-receipt" if filename == "capture.py" else "--core") in after.stdout
    assert "inside the cache directory" not in after.stderr
    assert script.read_bytes() == script_bytes
    assert not (consumer / ".venv").exists()
    assert not (consumer / "uv.lock").exists()
