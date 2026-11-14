"""On a Python without a PyYAML wheel the hash-pinned sync uses Core's reviewed build and copies no pin."""

import sys
import zipfile
from pathlib import Path

import pytest

from heinzel_plugin_tools import cli

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
# A stand-in for the file the Core wheel ships: the same commands, an invented package and no real build.
BOOTSTRAP = """
import sys
if sys.argv[1] == "needed":
    raise SystemExit({needed})
if sys.argv[1] == "pins":
    print('{{"name": "tidal-yaml", "version": "1.0", "source_sha256": "aa"}}')
"""
LOCK = (
    "pydantic==2.12.0 --hash=sha256:00\n"
    "Tidal_YAML==1.0 \\\n    --hash=sha256:aa \\\n    --hash=sha256:bb\n"
    "typer==0.16.0 \\\n    --hash=sha256:00\n"
)
REST = "pydantic==2.12.0 --hash=sha256:00\ntyper==0.16.0 \\\n    --hash=sha256:00\n"


def core_wheel(path, *, needed: int | None = 0):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("heinzel-0.9.45.dist-info/METADATA", "Name: heinzel\nVersion: 0.9.45\n")
        if needed is not None:
            archive.writestr(cli.CORE_PYYAML_BOOTSTRAP, BOOTSTRAP.format(needed=needed))
    return str(path)


@pytest.fixture
def lock(tmp_path):
    path = tmp_path / "requirements.lock"
    path.write_text(LOCK)
    return path


@pytest.fixture
def commands(monkeypatch):
    """Record each command and the lock it synced; the bootstrap's build leaves the wheels named in `built`."""
    recorded = []
    recorded_built = ["tidal_yaml-1.0-py3-none-any.whl"]

    def run(command, **_options):
        entry = {"command": command}
        if command[:3] == ["uv", "pip", "sync"]:
            entry["synced"] = Path(command[-1]).read_text()
        if "build" in command:
            wheels = Path(command[command.index("--wheel-dir") + 1])
            wheels.mkdir(parents=True)
            for name in recorded_built:
                (wheels / name).write_bytes(b"wheel")
        recorded.append(entry)

    monkeypatch.setattr(cli, "run", run)
    return recorded, recorded_built


def test_one_package_leaves_a_hash_pinned_lock_and_every_other_entry_stays_byte_for_byte():
    assert cli.without_requirement(LOCK, "tidal-yaml") == REST
    assert cli.without_requirement(LOCK, "absent") == LOCK
    assert cli.without_requirement("# tidal-yaml is built\n" + LOCK, "tidal-yaml") == "# tidal-yaml is built\n" + REST
    # a name that only starts the same is another package
    assert cli.without_requirement("tidal-yaml-types==1 --hash=sha256:00\n", "tidal-yaml") != ""


def test_a_python_without_a_wheel_gets_cores_build_and_everything_else_under_hashes(tmp_path, lock, commands):
    recorded, _ = commands
    interpreter = Path(sys.executable)
    cli.sync_locked(interpreter, lock, core_wheel(tmp_path / "heinzel-0.9.45-py3-none-any.whl"))
    build, sync, install = (entry["command"] for entry in recorded)
    # Core's file, run isolated on the environment's own interpreter, checks the lock before it builds
    assert build[:3] == [str(interpreter), "-I", "-S"] and Path(build[3]).name == "bootstrap_pyyaml.py"
    assert build[4:] == ["build", "--requirements", str(lock), "--wheel-dir", build[8], "--python", str(interpreter)]
    assert sync[:7] == ["uv", "pip", "sync", "--python", str(interpreter), "--require-hashes", "--no-build"]
    assert recorded[1]["synced"] == REST
    assert install[:7] == ["uv", "pip", "install", "--python", str(interpreter), "--no-deps", "--no-build"]
    assert Path(install[7]).name == "tidal_yaml-1.0-py3-none-any.whl" and len(install) == 8
    assert lock.read_text() == LOCK  # the plugin's own lock is never rewritten


@pytest.mark.parametrize(
    ("needed", "text"),
    [
        (None, LOCK),  # a Core that ships no bootstrap
        (1, LOCK),  # this Python has an upstream wheel
        (0, REST),  # the lock does not install the package at all
    ],
)
def test_otherwise_the_whole_lock_syncs_under_hashes_and_nothing_is_built(tmp_path, lock, commands, needed, text):
    recorded, _ = commands
    lock.write_text(text)
    cli.sync_locked(Path(sys.executable), lock, core_wheel(tmp_path / "heinzel-0.9.45-py3-none-any.whl", needed=needed))
    assert [entry["command"] for entry in recorded] == [
        ["uv", "pip", "sync", "--python", sys.executable, "--require-hashes", "--no-build", str(lock)]
    ]


@pytest.mark.parametrize("built", [[], ["a-1-py3-none-any.whl", "b-1-py3-none-any.whl"]])
def test_a_build_that_leaves_no_single_wheel_installs_nothing(tmp_path, lock, commands, built):
    recorded, wheels = commands
    wheels[:] = built
    with pytest.raises(ValueError, match="exactly one wheel"):
        cli.sync_locked(Path(sys.executable), lock, core_wheel(tmp_path / "heinzel-0.9.45-py3-none-any.whl"))
    assert not any(entry["command"][:2] == ["uv", "pip"] for entry in recorded)


def test_the_toolkit_keeps_no_copy_of_a_core_pin():
    """The source, its hash, the version and the backend pins are Core's: here only the path inside its wheel."""
    import tomllib

    package = next(
        item for item in tomllib.loads((ROOT / "uv.lock").read_text())["package"] if item["name"] == "pyyaml"
    )
    forbidden = [package["sdist"]["hash"].removeprefix("sha256:"), package["sdist"]["url"], "setuptools=="]
    for path in sorted((ROOT / "src/heinzel_plugin_tools").rglob("*.py")):
        source = path.read_text()
        assert not any(value in source for value in forbidden), path.name
    sync = (ROOT / "src/heinzel_plugin_tools/cli.py").read_text()
    assert sync.count('"--require-hashes"') == 1  # one sync path, always under hashes
