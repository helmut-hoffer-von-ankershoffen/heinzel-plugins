# /// script
# requires-python = ">=3.12"
# dependencies = ["packaging>=25"]
# ///
"""Compose a standard app from a verified released core and locally enrolled plugin metadata."""

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from email.parser import Parser
from pathlib import Path
from urllib.parse import quote, urlsplit

from packaging.utils import parse_wheel_filename
from packaging.version import Version

from heinzel_plugin_tools.cli import ROOT, acceptance, profile, projects, run, validate_lock, write_accepted_profile
from heinzel_plugin_tools.installation import check_profile_format, isolated_environment, verify_managed_profile
from heinzel_plugin_tools.publishing import api, fetch_bytes, find_release, restore, tag_revision

CORE_REPOSITORY = "helmut-hoffer-von-ankershoffen/heinzel"
PLUGINS_REPOSITORY = f"{CORE_REPOSITORY}-plugins"


def release_absent(repository: str, tag: str) -> bool:
    """Only classify a known accessible repository with neither release object nor ref."""
    if find_release(repository, tag) is not None:
        return False
    if api(f"repos/{repository}/git/ref/tags/{quote(tag, safe='')}", missing=True) is not None:
        raise ValueError(f"Enrolled plugin tag {tag} exists without a complete release")
    return True


def dependency_context() -> dict | None:
    """Limit evidence to first-attempt runs of the protected composition workflow."""
    plugins_sha = os.environ.get("GITHUB_SHA", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if (
        os.environ.get("GH_REPO") != PLUGINS_REPOSITORY
        or os.environ.get("GITHUB_REPOSITORY") != PLUGINS_REPOSITORY
        or os.environ.get("GITHUB_REF") != "refs/heads/main"
        or os.environ.get("GITHUB_WORKFLOW_REF")
        != f"{PLUGINS_REPOSITORY}/.github/workflows/compose.yml@refs/heads/main"
        or os.environ.get("GITHUB_EVENT_NAME") not in {"schedule", "workflow_dispatch"}
        or os.environ.get("GITHUB_RUN_ATTEMPT") != "1"
        or not re.fullmatch(r"[a-f0-9]{40}", plugins_sha)
        or not re.fullmatch(r"[1-9][0-9]*", run_id)
    ):
        return None
    return {"plugins_sha": plugins_sha, "run_id": int(run_id), "run_attempt": 1}


def parse_dependency_pins(raw: str) -> dict[str, dict]:
    """Read the bounded canonical map whose exact bytes are named by the recovery run."""
    if not raw:
        return {}
    if len(raw.encode()) > 16 * 1024:
        raise ValueError("Dependency pins exceed the recovery input limit")
    pins = json.loads(raw)
    if (
        not isinstance(pins, dict)
        or not 1 <= len(pins) <= 32
        or json.dumps(pins, sort_keys=True, separators=(",", ":")) != raw
    ):
        raise ValueError("Recovery needs a nonempty canonical dependency pin map")
    for tag, pin in pins.items():
        identity = re.fullmatch(r"(heinzel-[a-z0-9]+(?:-[a-z0-9]+)*)/v([0-9]+\.[0-9]+\.[0-9]+)", tag)
        if (
            not identity
            or not isinstance(pin, dict)
            or set(pin) != {"revision", "assets"}
            or not isinstance(pin["revision"], str)
            or not re.fullmatch(r"[a-f0-9]{40}", pin["revision"])
            or not isinstance(pin["assets"], dict)
            or len(pin["assets"]) != 2
        ):
            raise ValueError("Invalid dependency pin identity")
        name, version = identity.groups()
        prefix = f"{name.replace('-', '_')}-{version}"
        assets = pin["assets"]
        if (
            prefix + ".tar.gz" not in assets
            or sum(
                bool(re.fullmatch(re.escape(prefix) + r"-[A-Za-z0-9_.]+-[A-Za-z0-9_.]+-[A-Za-z0-9_.]+\.whl", filename))
                for filename in assets
            )
            != 1
            or any(
                not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest) for digest in assets.values()
            )
        ):
            raise ValueError("Dependency pins must include the exact wheel and sdist digests")
    return pins


def verify_dependency_pin(tag: str, release: dict, pin: dict) -> None:
    verified = release["artifact_hashes"]
    restored_hashes = {Path(path).name: digest for path, digest in verified.items()}
    if (
        release.get("revision") != pin["revision"]
        or set(verified) != set(release["artifacts"])
        or len(restored_hashes) != len(verified)
        or restored_hashes != pin["assets"]
    ):
        raise ValueError(f"Restored dependency {tag} differs from its reviewed revision or artifact pins")


def core_python(core: Path) -> list[str]:
    """`--python` with the core wheel's Requires-Python, so the acceptance environment has a Python the core supports.

    Empty when the wheel declares none: uv's default interpreter then serves, as before.
    """
    with zipfile.ZipFile(core) as wheel:
        name = next(n for n in wheel.namelist() if n.endswith(".dist-info/METADATA"))
        requires = Parser().parsestr(wheel.read(name).decode()).get("Requires-Python")
    return ["--python", requires.strip()] if requires and requires.strip() else []


def compose(
    core: Path,
    destination: Path,
    base_url: str | None,
    *,
    core_sha256: str | None = None,
    dependency_pins: dict[str, dict] | None = None,
) -> None:
    """Install the verified independent releases, then prove the profile in a fresh environment."""
    inventory = projects()
    standard = {
        f"{project.name}/v{project.version}": project
        for project in inventory
        if "standard" in project.options.get("profiles", [])
    }
    pins = dependency_pins or {}
    if pins.keys() - standard.keys():
        raise ValueError("Dependency pins name a release outside the enrolled standard profile")
    repository = os.environ.get("GH_REPO")
    if not repository:
        raise ValueError("Set GH_REPO to the reviewed composition repository's owner/name")
    verified = {core: core_sha256 or hashlib.sha256(core.read_bytes()).hexdigest()}

    def unchanged():
        for artifact, digest in verified.items():
            if hashlib.sha256(artifact.read_bytes()).hexdigest() != digest:
                raise ValueError("A verified release artifact changed before composition")

    unchanged()
    environment = destination / "acceptance"
    isolated = isolated_environment(destination / "acceptance-state")
    run(["uv", "venv", "--clear", *core_python(core), str(environment)], env=isolated)
    interpreter = environment / "bin/python"
    unchanged()
    run(["uv", "pip", "install", "--python", str(interpreter), str(core)], env=isolated)
    # Check the accepted SDK's actual profile parser before restoring or testing independent providers.
    # Format 2 promises managed startup continuity; the plugin ABI remains sdk=1.
    probe = destination / "protocol.json"
    profile([], core, probe, None)
    check_profile_format(interpreter, probe, env=isolated, runner=run)
    probe.unlink()
    selected = {}
    for tag, project in standard.items():
        validate_lock(project, str(core))
        release = restore(repository, tag, project.name, destination / ".verified" / project.name)
        if tag in pins:
            verify_dependency_pin(tag, release, pins[tag])
        wheel = next(Path(path) for path in release["artifacts"] if path.endswith(".whl"))
        verified[wheel] = release["artifact_hashes"][str(wheel)]
        unchanged()
        selected[project.name] = wheel
        if any((project.directory / "tests" / name).is_dir() for name in ("acceptance", "browser", "e2e")):
            acceptance(project, str(core), wheel=wheel)
        unchanged()
    unchanged()
    result = profile(inventory, core, destination / "local.json", None, selected_wheels=selected)
    for artifact in result["artifacts"]:
        target = destination / artifact["filename"]
        if Path(artifact["url"]).resolve() != target.resolve():
            shutil.copyfile(artifact["url"], target)
    run(
        [
            str(interpreter),
            "-I",
            "-m",
            "heinzel.heads.install",
            "--profile",
            str(destination / "local.json"),
            "--python",
            str(interpreter),
        ],
        env=isolated,
    )
    # Discovery is provider-neutral. Default plugin health must not start sharing, playback or authorization.
    run(
        [
            str(interpreter),
            "-I",
            "-c",
            "from heinzel.kernel import discover; r,e=discover(); assert not e,e; "
            f"expected={set(p.name for p in inventory if 'standard' in p.options.get('profiles', []))!r}; "
            "actual={m.origin.distribution for m in r if not m.origin.builtin}; "
            "assert actual==expected,(actual,expected); "
            "from heinzel import Config,CurrentUser,Kernel,Settings; from heinzel.kernel import OperationLet; "
            "c=Config.empty(); k=Kernel(c.settings(Settings,'hz'),r,config=c); "
            "op=next(let for owner,let in k.lets(OperationLet) if owner.qualname=='system.ui' and let.name=='views'); "
            "\nwith k.resolve(CurrentUser).local('cli'):\n views=k.invoke(op)\n"
            "assert all(not v.problem and v.bundle for v in views); print(sorted(actual))",
        ],
        env=isolated,
    )
    verify_managed_profile(interpreter, destination / "local.json")
    unchanged()
    write_accepted_profile(
        result,
        destination / "local.json",
        destination / "standard.json",
        base_url,
        artifact_directory=destination,
    )
    (destination / "local.json").unlink()
    shutil.rmtree(environment)
    shutil.rmtree(destination / "acceptance-state", ignore_errors=True)
    shutil.rmtree(destination / ".verified")


def core_tag(version: str) -> str:
    return f"{'edge-v' if Version(version).is_devrelease else 'v'}{version}"


def verified_core(url: str, version: str, core: Path) -> tuple[str, str]:
    """Download and attest the official wheel without importing its code."""
    _, content = fetch_bytes(url, hosts={"github.com"}, timeout=60, limit=128 * 1024 * 1024)
    if len(content) > 128 * 1024 * 1024:
        raise ValueError("Core wheel exceeds its size limit")
    core.write_bytes(content)
    revision = tag_revision(CORE_REPOSITORY, core_tag(version))
    digest = hashlib.sha256(content).hexdigest()
    expected_revision = os.environ.get("EXPECTED_CORE_SHA", "")
    expected_digest = os.environ.get("EXPECTED_CORE_WHEEL_SHA256", "")
    if (expected_revision and revision != expected_revision) or (expected_digest and digest != expected_digest):
        raise ValueError("The official Core source or downloaded wheel differs from the recovery request")
    run(
        [
            "gh",
            "attestation",
            "verify",
            str(core),
            "--repo",
            CORE_REPOSITORY,
            "--source-digest",
            revision,
            "--deny-self-hosted-runners",
        ]
    )
    return revision, digest


def check_dependencies(url: str, version: str, filename: str) -> None:
    """Emit a receipt for missing publication after passive checks of exact release inputs."""
    context = dependency_context()
    if context is None or Version(version).is_prerelease:
        return
    selected = [
        (project, f"{project.name}/v{project.version}")
        for project in projects()
        if "standard" in project.options.get("profiles", [])
    ]
    missing = {tag for _, tag in selected if release_absent(PLUGINS_REPOSITORY, tag)}
    if not missing:
        return
    with tempfile.TemporaryDirectory() as temporary:
        destination = Path(temporary)
        core = destination / filename
        revision, digest = verified_core(url, version, core)
        for project, tag in selected:
            validate_lock(project, str(core))
            if tag not in missing:
                restore(PLUGINS_REPOSITORY, tag, project.name, destination / project.name)
        if not all(release_absent(PLUGINS_REPOSITORY, tag) for tag in sorted(missing)):
            return  # A publication appeared during verification. Let normal composition try it.
    receipt = {
        "schema": 1,
        "kind": "enrolled-plugin-publication-missing",
        **context,
        "core_version": version,
        "core_sha": revision,
        "core_wheel_sha256": digest,
        "missing": sorted(
            (
                {"name": project.name, "version": str(project.version), "tag": tag}
                for project, tag in selected
                if tag in missing
            ),
            key=lambda row: row["name"],
        ),
    }
    output = Path(os.environ["RUNNER_TEMP"]) / "standard-app-dependency.json"
    output.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as result:
        result.write("dependency_missing=true\n")
    raise SystemExit("Missing enrolled plugin publication: " + ", ".join(sorted(missing)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-url", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--dependency-check", action="store_true")
    args = parser.parse_args()
    version = str(Version(args.version))
    if args.version != version:
        parser.error("Use the canonical core version, for example 0.9.0")
    url = urlsplit(args.core_url)
    filename = Path(url.path).name
    expected_path = f"/{CORE_REPOSITORY}/releases/download/{core_tag(version)}/{filename}"
    if url.scheme != "https" or url.netloc != "github.com" or url.path != expected_path or url.query or url.fragment:
        parser.error("Use the immutable HTTPS wheel URL from the official core release")
    name, wheel_version, _, _ = parse_wheel_filename(filename)
    if name != "heinzel" or str(wheel_version) != version:
        parser.error("The core wheel must match the requested version")
    pins = parse_dependency_pins(os.environ.get("DEPENDENCY_PINS", ""))
    if args.dependency_check:
        check_dependencies(args.core_url, version, filename)
        return
    destination = ROOT / "dist/standard"
    destination.mkdir(parents=True, exist_ok=True)
    core = destination / filename
    _, digest = verified_core(args.core_url, version, core)
    compose(
        core,
        destination,
        f"https://github.com/{PLUGINS_REPOSITORY}/releases/download/app-v{version}",
        core_sha256=digest,
        dependency_pins=pins,
    )


if __name__ == "__main__":
    main()
