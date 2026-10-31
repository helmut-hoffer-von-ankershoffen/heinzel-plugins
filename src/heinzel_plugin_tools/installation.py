"""Focused installed-artifact acceptance for the standard app lifecycle, independent of core's test suite."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path


def isolated_environment(root: Path) -> dict:
    """Keep package resolution, application state and Python imports away from the caller's installation."""
    # This controls inherited configuration, not filesystem or network access.
    result = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "SYSTEMROOT", "SSL_CERT_FILE", "SSL_CERT_DIR", "UV_DEFAULT_INDEX"}
        or key.startswith("UV_INDEX")
    }
    for key, relative in {
        "HOME": "home",
        "XDG_CONFIG_HOME": "xdg/config",
        "XDG_DATA_HOME": "xdg/data",
        "XDG_CACHE_HOME": "xdg/cache",
        "XDG_STATE_HOME": "xdg/state",
        "XDG_RUNTIME_DIR": "xdg/runtime",
        "TMPDIR": "tmp",
        "UV_CACHE_DIR": "uv-cache",
    }.items():
        directory = root / relative
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        result[key] = str(directory)
    result.update(TMP=result["TMPDIR"], TEMP=result["TMPDIR"], LANG="C.UTF-8")
    result.update(
        UV_NO_CONFIG="1",
        UV_TOOL_DIR=str(root / "tools"),
        UV_TOOL_BIN_DIR=str(root / "bin"),
        PATH=str(root / "bin") + os.pathsep + os.environ.get("PATH", ""),
        HZ_UPDATE_CHECK="false",
        HZ_SYSTEM_CREDENTIAL__BACKEND="environment",
        BROWSER="true",
        HZ_SYSTEM_DAEMON__UNIT_DIR=str(root / "units"),
        HZ_SYSTEM_AGENT__SKILL_DIRS=json.dumps([str(root / "skills")]),
    )
    for name in ("CONFIG_HOME", "DATA_DIR", "CACHE_DIR", "STATE_DIR", "LOG_DIR"):
        result[f"HZ_{name}"] = str(root / name.lower())
    return result


def _run(command: list[str], *, cwd: Path, env: dict) -> str:
    result = subprocess.run(command, cwd=cwd, env=env, stdout=subprocess.PIPE, text=True, timeout=900, check=False)
    if result.returncode:
        if result.stdout:
            sys.stderr.write(result.stdout)
        raise SystemExit(result.returncode)
    return result.stdout


def check_profile_format(interpreter: Path, profile: Path, *, env: dict, runner=None) -> None:
    """Ask the actual installed SDK to accept this profile's lifecycle contract, without installing providers."""
    (runner or _run)(
        [str(interpreter), "-I", str(interpreter.parent / "hz-install"), "--dry-run", "--profile", str(profile)],
        cwd=profile.parent,
        env=env,
    )


def _probe_project(directory: Path, version: str) -> None:
    package = directory / "src/heinzel_lifecycle_probe"
    package.mkdir(parents=True, exist_ok=True)
    (directory / "pyproject.toml").write_text(
        '[project]\nname="heinzel-lifecycle-probe"\n'
        f'version="{version}"\nrequires-python=">=3.12"\ndependencies=["heinzel"]\n'
        '[project.entry-points."heinzel.modules"]\nlifecycleprobe="heinzel_lifecycle_probe"\n'
        '[build-system]\nrequires=["hatchling"]\nbuild-backend="hatchling.build"\n'
    )
    (package / "__init__.py").write_text(
        'from heinzel import Module\nmodule=Module("lifecycleprobe", "An installed lifecycle acceptance fixture.")\n'
        '@module.operation\ndef ping() -> str:\n    """Read the installed fixture version."""\n'
        f'    return "{version}"\n'
    )


def _require(condition, message):
    if not condition:
        raise ValueError(message)


@contextmanager
def _workspace(prefix):
    root = Path(tempfile.mkdtemp(prefix=prefix)).resolve()
    try:
        yield root
    except BaseException:
        sys.stderr.write(f"Acceptance state retained for inspection: {root}\n")
        raise
    else:
        shutil.rmtree(root)


def verify_managed_profile(interpreter: Path, profile: Path) -> None:
    """Prove seeding, offline launch, plugin mutations and local updates using only the selected artifact bytes."""
    data = json.loads(profile.read_text())
    sources = [Path(item["url"]).resolve() for item in data["artifacts"]]
    original = {source: hashlib.sha256(source.read_bytes()).hexdigest() for source in sources}
    expected = {item["name"] for item in data["artifacts"] if item["name"] != "heinzel"}
    core = next(source for source, item in zip(sources, data["artifacts"], strict=True) if item["name"] == "heinzel")
    with _workspace("hz-managed-profile-") as root:
        env = isolated_environment(root)
        constraints = root / "constraints.txt"
        constraints.write_text(
            "".join(
                f"{item['name']} @ {source.as_uri()}\n" for source, item in zip(sources, data["artifacts"], strict=True)
            )
        )
        env["UV_CONSTRAINT"] = str(constraints)
        _run(
            [str(interpreter), "-I", str(interpreter.parent / "hz-install"), "--profile", str(profile)],
            cwd=root,
            env=env,
        )
        hz = root / "bin/hz"
        prefix = root / "tools/heinzel"

        def command(*arguments):
            return json.loads(_run([str(hz), *arguments, "--json"], cwd=root, env=env))

        def launch(names, stage):
            _run(
                [
                    str(interpreter),
                    "-I",
                    "-c",
                    "from pathlib import Path; import sys; from heinzel import Progress; "
                    "from heinzel.kernel import Installation; "
                    "valid=Installation(Progress(),prefix=Path(sys.argv[1])).startup_state_matches(); "
                    "raise SystemExit(None if valid else "
                    "'Managed startup checkpoint does not match after '+sys.argv[2])",
                    str(prefix),
                    stage,
                ],
                cwd=root,
                env=env,
            )
            # A missing checkpoint must not be hidden by quietly installing a fresh composition.
            offline = env | {"UV_OFFLINE": "1", "HZ_APP_PROFILE": str(root / "must-not-reinstall.json")}
            inventory = json.loads(
                _run(
                    [
                        str(interpreter),
                        "-I",
                        str(interpreter.parent / "heinzel"),
                        "system",
                        "plugin",
                        "list",
                        "--json",
                    ],
                    cwd=root,
                    env=offline,
                )
            )
            _require({item["distribution"] for item in inventory} == names, "Offline launch lost plugin membership")
            _require(all(item["enabled"] and not item["error"] for item in inventory), "Offline discovery failed")

        launch(expected, "standard installation")
        fixture = root / "probe"
        _probe_project(fixture, "0.1.0")
        _require(command("system", "plugin", "develop", str(fixture))["done"], "Probe installation did not complete")
        launch(expected | {"heinzel-lifecycle-probe"}, "plugin installation")
        _require(command("lifecycleprobe", "ping") == "0.1.0", "The installed probe is not the original version")
        _probe_project(fixture, "0.2.0")
        updated = command("system", "update", "--source", str(core))
        _require(updated["after"] == data["core_version"], "The SDK changed during a fixture-only update")
        _require(command("lifecycleprobe", "ping") == "0.2.0", "The local provider did not update")
        launch(expected | {"heinzel-lifecycle-probe"}, "local update")
        _require(command("system", "plugin", "remove", "heinzel-lifecycle-probe")["done"], "Probe removal failed")
        launch(expected, "plugin removal")
        _require(command("system", "plugin", "develop", str(fixture))["done"], "Probe reinstallation failed")
        launch(expected | {"heinzel-lifecycle-probe"}, "plugin reinstallation")
        _require(not list((root / "units").glob("*")), "Acceptance must leave a previously off daemon off")
    if any(hashlib.sha256(source.read_bytes()).hexdigest() != digest for source, digest in original.items()):
        raise ValueError("The selected release bytes changed during managed acceptance")


def verify_profile(core: Path, profile: Path) -> None:
    """Check a public profile command through the same installed SDK and managed lifecycle used by publication."""
    with tempfile.TemporaryDirectory(prefix="hz-profile-sdk-") as temporary:
        root = Path(temporary).resolve()
        env = isolated_environment(root)
        sdk = root / "sdk"
        _run(["uv", "venv", str(sdk)], cwd=root, env=env)
        interpreter = sdk / "bin/python"
        _run(["uv", "pip", "install", "--python", str(interpreter), str(core.resolve())], cwd=root, env=env)
        check_profile_format(interpreter, profile, env=env)
        verify_managed_profile(interpreter, profile)
