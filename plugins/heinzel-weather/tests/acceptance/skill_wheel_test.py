"""Build and install a wheel into a disposable target, then discover its real checked skill."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

pytestmark = pytest.mark.e2e
ROOT = Path(__file__).resolve().parents[2]
READ_INSTALLED = """
import json
import sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root))
import heinzel_weather
from heinzel import Skills
from heinzel.kernel import boot
assert Path(heinzel_weather.__file__).is_relative_to(root)
skills = boot().resolve(Skills)
entry = next(entry for entry in skills.index() if entry.name == 'weather-trend')
loaded = skills.load('weather-trend', allowed=['weather-trend'])
assert loaded.fingerprint == entry.fingerprint
assert 'weather.observe' in loaded.body
print(json.dumps({'source': entry.source, 'module': entry.module, 'fingerprint': loaded.fingerprint}))
"""


def test_built_installed_wheel_discovers_the_actual_skill(tmp_path):
    uv = shutil.which("uv")
    assert uv
    if selected := os.environ.get("PLUGIN_TEST_WHEEL"):
        wheel = Path(selected)
    else:
        output = tmp_path / "built"
        built = subprocess.run(
            [uv, "build", "--project", str(ROOT), "--wheel", "--out-dir", str(output)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        assert built.returncode == 0, built.stderr
        (wheel,) = output.glob("*.whl")
    with ZipFile(wheel) as archive:
        assert "heinzel_weather/skills/weather-trend/SKILL.md" in archive.namelist()
    target = tmp_path / "installed"
    installed = subprocess.run(
        [uv, "pip", "install", "--offline", "--no-deps", "--target", str(target), str(wheel)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert installed.returncode == 0, installed.stderr
    read = subprocess.run(
        [sys.executable, "-I", "-c", READ_INSTALLED, str(target)],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert read.returncode == 0, read.stderr
    found = json.loads(read.stdout)
    assert (found["source"], found["module"]) == ("plugin", "weather")
    assert len(found["fingerprint"]) == 64
