# /// script
# requires-python = ">=3.12"
# dependencies = ["packaging>=25"]
# ///
"""Compose a standard app from a verified released core and locally enrolled plugin metadata."""

import argparse
import os
import shutil
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from packaging.utils import parse_wheel_filename
from packaging.version import Version

from heinzel_plugin_tools.cli import ROOT, acceptance, profile, projects, run, validate_lock
from heinzel_plugin_tools.publishing import restore, tag_revision


def compose(core: Path, destination: Path, base_url: str | None) -> None:
    """Install the verified independent releases, then prove the profile in a fresh environment."""
    inventory = projects()
    repository = os.environ.get("GH_REPO")
    if not repository:
        raise ValueError("Set GH_REPO to the reviewed composition repository's owner/name")
    selected = {}
    for project in inventory:
        if "standard" in project.options.get("profiles", []):
            validate_lock(project, str(core))
            release = restore(
                repository,
                f"{project.name}/v{project.version}",
                project.name,
                destination / ".verified" / project.name,
            )
            wheel = next(Path(path) for path in release["artifacts"] if path.endswith(".whl"))
            selected[project.name] = wheel
            if any((project.directory / "tests" / name).is_dir() for name in ("acceptance", "browser", "e2e")):
                acceptance(project, str(core), wheel=wheel)
    result = profile(inventory, core, destination / "local.json", None, selected_wheels=selected)
    for artifact in result["artifacts"]:
        target = destination / artifact["filename"]
        if Path(artifact["url"]).resolve() != target.resolve():
            shutil.copyfile(artifact["url"], target)
    environment = destination / "acceptance"
    run(["uv", "venv", "--clear", str(environment)])
    interpreter = environment / "bin/python"
    run(["uv", "pip", "install", "--python", str(interpreter), str(core)])
    isolated = {key: value for key, value in os.environ.items() if not key.startswith("HZ_")}
    for name in ("CONFIG_HOME", "DATA_DIR", "CACHE_DIR", "STATE_DIR", "LOG_DIR"):
        isolated[f"HZ_{name}"] = str(destination / "acceptance-state" / name.lower())
    isolated["HZ_PLUGINS_ENABLED"] = "true"
    run(
        [
            str(interpreter),
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
    profile(inventory, core, destination / "standard.json", base_url, selected_wheels=selected)
    (destination / "local.json").unlink()
    shutil.rmtree(environment)
    shutil.rmtree(destination / "acceptance-state", ignore_errors=True)
    shutil.rmtree(destination / ".verified")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-url", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    version = str(Version(args.version))
    if args.version != version:
        parser.error("Use the canonical core version, for example 0.9.0")
    url = urlsplit(args.core_url)
    if url.scheme != "https" or url.hostname != "github.com" or url.username or url.password or url.fragment:
        parser.error("Use the immutable HTTPS wheel URL from the official core release")
    if not url.path.startswith("/helmut-hoffer-von-ankershoffen/heinzel/releases/download/"):
        parser.error("The core artifact must come from its official release")
    name, wheel_version, _, _ = parse_wheel_filename(Path(url.path).name)
    if name != "heinzel" or str(wheel_version) != version:
        parser.error("The core wheel must match the requested version")
    destination = ROOT / "dist/standard"
    destination.mkdir(parents=True, exist_ok=True)
    core = destination / Path(url.path).name
    with urllib.request.urlopen(args.core_url, timeout=60) as response:  # noqa: S310 - exact HTTPS official release checked
        if urlsplit(response.url).scheme != "https":
            parser.error("The core download redirected away from HTTPS")
        content = response.read(128 * 1024 * 1024 + 1)
    if len(content) > 128 * 1024 * 1024:
        parser.error("Core wheel exceeds its size limit")
    core.write_bytes(content)
    repository = "helmut-hoffer-von-ankershoffen/heinzel"
    revision = tag_revision(repository, f"v{version}")
    run(
        [
            "gh",
            "attestation",
            "verify",
            str(core),
            "--repo",
            repository,
            "--source-digest",
            revision,
            "--deny-self-hosted-runners",
        ]
    )
    compose(
        core,
        destination,
        f"https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/releases/download/app-v{version}",
    )


if __name__ == "__main__":
    main()
