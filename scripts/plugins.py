# /// script
# requires-python = ">=3.12"
# dependencies = ["packaging==26.3"]
# ///
"""One independent plugin at a time: discover, plan, check, build and compose app profiles."""

import argparse
import ast
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.request
import zipfile
from dataclasses import dataclass
from importlib import metadata as distributions
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Project:
    """Everything about a plugin comes from its own directory."""

    directory: Path
    name: str
    version: str
    metadata: dict

    @property
    def options(self) -> dict:
        return self.metadata.get("tool", {}).get("heinzel", {}).get("plugin", {})


def projects(root: Path = ROOT) -> list[Project]:
    """Read metadata only; never import a project to discover it."""
    paths = sorted((root / "plugins").glob("*/pyproject.toml"))
    if (root / "pyproject.toml").is_file():
        paths.append(root / "pyproject.toml")
    found = []
    for path in paths:
        metadata = tomllib.loads(path.read_text())
        project = metadata.get("project", {})
        if not project.get("entry-points", {}).get("heinzel.modules"):
            continue
        name, version = project["name"], project["version"]
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 100:
            raise ValueError(f"{path}: use a canonical distribution name")
        if not isinstance(version, str) or str(Version(version)) != version:
            raise ValueError(f"{path}: use a canonical version")
        found.append(Project(path.parent, name, version, metadata))
    names = [project.name for project in found]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate plugin distribution names")
    return found


def plan(
    changed: list[str],
    inventory: list[Project],
    root: Path = ROOT,
    *,
    contracts: list[str] = (),
    core: str | None = None,
) -> dict:
    """Select changed providers and their public-contract consumers; never select core work."""
    shared = any(
        path.startswith(("scripts/", ".github/", "tests/"))
        or path in {"pyproject.toml", "uv.lock", ".license-allowlist"}
        for path in changed
    )
    selected = {
        project.name
        for project in inventory
        if shared
        or any(
            project.directory == root or path.startswith(project.directory.relative_to(root).as_posix() + "/")
            for path in changed
        )
    }
    selected |= {
        project.name for project in inventory if set(contracts).intersection(project.options.get("requires", []))
    }
    while True:
        provided = {
            contract
            for project in inventory
            if project.name in selected
            for contract in project.options.get("provides", [])
        }
        consumers = {
            project.name for project in inventory if provided.intersection(project.options.get("requires", []))
        }
        if consumers <= selected:
            break
        selected |= consumers
    version = core_metadata(core)["version"] if core else None
    return {
        "core": False,
        "core_build": False,
        "core_tests": False,
        "include": [
            {"name": project.name, "path": project.directory.relative_to(root).as_posix()}
            for project in inventory
            if project.name in selected and (version is None or supports_core(project, version))
        ],
    }


def run(command: list[str], *, cwd: Path = ROOT, env: dict | None = None, timeout: int | None = 600) -> None:
    """Print bounded, useful progress and stop at the failing owning command."""
    started = time.monotonic()
    print("→ " + " ".join(command), flush=True)
    result = subprocess.run(command, cwd=cwd, env=env, check=False, timeout=timeout)
    print(f"{'✓' if result.returncode == 0 else '✗'} {command[0]}: {time.monotonic() - started:.2f}s", flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)


def requirements(project: Project, group: str) -> list[str]:
    found = []
    groups = project.metadata.get("dependency-groups", {})
    for requirement in groups.get(group, []):
        if isinstance(requirement, str):
            found.append(requirement)
        elif "include-group" in requirement:
            found += requirements(project, requirement["include-group"])
    return found


def core_metadata(source: str) -> dict:
    """Read dependency metadata from the selected built artifact; never import or build core."""
    if source.startswith("https://"):
        with urllib.request.urlopen(source, timeout=60) as response:  # noqa: S310 - explicit HTTPS candidate artifact
            content = response.read(128 * 1024 * 1024 + 1)
    else:
        content = Path(source).read_bytes()
    if len(content) > 128 * 1024 * 1024:
        raise ValueError("Core artifact exceeds its size limit")
    from email.parser import Parser

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        metadata = Parser().parsestr(archive.read(name).decode())
    if canonicalize_name(metadata["Name"]) != "heinzel":
        raise ValueError("Select a built Heinzel core wheel")
    return {
        "version": metadata["Version"],
        "dependencies": sorted(str(Requirement(value)) for value in metadata.get_all("Requires-Dist", [])),
    }


def dependency_inputs(project: Project) -> list[str]:
    return sorted(
        [
            *project.metadata["project"].get("dependencies", []),
            *requirements(project, "test"),
            *project.metadata["build-system"]["requires"],
        ]
    )


def supports_core(project: Project, version: str) -> bool:
    """Compatibility is declared by the owning package, never inferred from its repository or name."""
    matches = [
        Requirement(value)
        for value in project.metadata["project"].get("dependencies", [])
        if canonicalize_name(Requirement(value).name) == "heinzel"
    ]
    return bool(matches) and all(Version(version) in item.specifier for item in matches)


def lock(project: Project, core: str) -> None:
    """Resolve one portable dependency lock against a compatible candidate, keeping its wheel path out of the lock."""
    metadata = core_metadata(core)
    inputs = dependency_inputs(project)
    if not supports_core(project, metadata["version"]):
        raise ValueError(f"{project.name} does not allow core {metadata['version']}")
    with tempfile.TemporaryDirectory(prefix="hz-plugin-lock-") as temporary:
        directory = Path(temporary)
        source = directory / "requirements.in"
        source.write_text("\n".join(inputs) + "\n")
        override = directory / "core.in"
        location = Path(core).resolve().as_uri() if Path(core).is_file() else core
        override.write_text(f"heinzel @ {location}\n")
        run(
            [
                "uv",
                "pip",
                "compile",
                str(source),
                "--overrides",
                str(override),
                "--universal",
                "--python-version",
                "3.12",
                "--generate-hashes",
                "--no-emit-package",
                "heinzel",
                "--no-header",
                "--no-annotate",
                "--output-file",
                str(project.directory / "requirements.lock"),
            ]
        )
    record = {"format": 1, "sdk": 1, "inputs": inputs, "core": metadata}
    (project.directory / "plugin-lock.json").write_text(json.dumps(record, indent=2) + "\n")


def validate_lock(project: Project, core: str | None) -> dict:
    path = project.directory / "plugin-lock.json"
    hint = f"make lock NAME={project.name} CORE=<compatible-core-wheel>"
    if not path.is_file() or not (project.directory / "requirements.lock").is_file():
        raise ValueError(f"{project.name} needs its own dependency lock. Run: {hint}")
    record = json.loads(path.read_text())
    if record["inputs"] != dependency_inputs(project):
        raise ValueError(f"{project.name} dependencies changed. Run: {hint}")
    metadata = core_metadata(core) if core else record["core"]
    if not supports_core(project, metadata["version"]):
        raise ValueError(f"{project.name} does not allow core {metadata['version']}")
    if metadata["dependencies"] != record["core"]["dependencies"]:
        raise ValueError(f"Core dependencies changed; relock only this consumer. Run: {hint}")
    return record


def validate_installed_core(project: Project) -> None:
    record = validate_lock(project, None)
    dependencies = sorted(str(Requirement(value)) for value in distributions.requires("heinzel") or [])
    if dependencies != record["core"]["dependencies"]:
        raise ValueError(
            f"Installed core dependencies changed; make lock NAME={project.name} CORE=<compatible-core-wheel>"
        )


def prepare_environment(project: Project, core: str | None) -> Path:
    """Authenticate the owning lock before installing core and this plugin without resolving new dependencies."""
    record = validate_lock(project, core)
    environment = project.directory / ".venv"
    interpreter = environment / "bin/python"
    if not interpreter.is_file():
        run(["uv", "venv", "--python", "3.12", str(environment)])
    run(
        [
            "uv",
            "pip",
            "sync",
            "--python",
            str(interpreter),
            "--require-hashes",
            str(project.directory / "requirements.lock"),
        ]
    )
    selected = core or f"heinzel=={record['core']['version']}"
    run(["uv", "pip", "install", "--python", str(interpreter), "--no-deps", selected])
    run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(interpreter),
            "--no-deps",
            "--no-build-isolation",
            "--editable",
            str(project.directory),
        ]
    )
    run(["uv", "pip", "check", "--python", str(interpreter)])
    return interpreter


def python_command(project: Project, _core: str | None, command: list[str]) -> list[str]:
    """Use only this project's authenticated isolated environment, never core test sources or sibling environments."""
    return [str(project.directory / ".venv/bin" / command[0]), *command[1:]]


def boundaries(project: Project) -> None:
    """Reject concrete plugin dependencies; implementation-free contract packages remain ordinary dependencies."""
    own = project.name.replace("-", "_")
    providers = {canonicalize_name(item.name) for item in projects() if item.name != project.name}
    roots = set()
    neutral = set()
    for distribution in distributions.distributions():
        points = [point for point in distribution.entry_points if point.group == "heinzel.modules"]
        name = canonicalize_name(distribution.metadata["Name"])
        if points and name != project.name:
            providers.add(name)
            roots.update(point.value.split(":")[0].split(".")[0] for point in points)
        elif not points:
            neutral.add(name)
    for requirement in project.metadata["project"].get("dependencies", []):
        name = canonicalize_name(Requirement(requirement).name)
        if name in providers or (name.startswith("heinzel-") and name not in neutral):
            raise ValueError(f"{project.name}: require a public contract, not a sibling plugin distribution")
    neutral_roots = {
        root
        for root, names in distributions.packages_distributions().items()
        if names and all(name in neutral for name in names)
    }
    for source in (project.directory / "src").rglob("*.py"):
        tree = ast.parse(source.read_text(), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                imported = [f"{node.module}.{alias.name}" for alias in node.names]
            else:
                continue
            for name in imported:
                root = name.split(".")[0]
                private = name.startswith(("heinzel.modules", "heinzel.heads", "heinzel.kernel._"))
                sibling = root != own and (root in roots or (root.startswith("heinzel_") and root not in neutral_roots))
                if private or sibling:
                    raise ValueError(f"{source}:{node.lineno}: consume a public contract instead of {name}")


def check(project: Project, core: str | None, *, tests_only: bool = False) -> None:
    """Run only the owning package's checks against an installed core/SDK artifact."""
    prepare_environment(project, core)
    run(
        python_command(project, core, ["python", str(ROOT / "scripts/plugins.py"), "boundary", project.name]),
        cwd=project.directory,
    )
    steps = (
        []
        if tests_only
        else [
            ["ruff", "check", "src", "tests"],
            ["ruff", "format", "--check", "src", "tests"],
            ["mypy", "--strict", "src"],
            ["pyright", "--pythonpath", str(project.directory / ".venv/bin/python"), "src"],
        ]
    )
    test = ["pytest", "-c", "pyproject.toml", "tests", "-m", "not e2e and not perf", "-q"]
    steps.append(test if tests_only else ["coverage", "run", "-m", *test])
    if not tests_only:
        steps.append(["coverage", "report"])
    for command in steps:
        run(python_command(project, core, command), cwd=project.directory)
    frontend = project.directory / "web/package.json"
    if frontend.is_file():
        scripts = json.loads(frontend.read_text()).get("scripts", {})
        for step in ["typecheck", "test"] if tests_only else ["lint", "typecheck", "test", "build"]:
            if step in scripts:
                run(
                    ["uv", "run", "--no-project", "--script", str(project.directory / "web/build.py"), "run", step],
                    cwd=project.directory,
                )


def preview(project: Project, core: str | None) -> None:
    """Launch only this plugin with isolated application state and a compatible installed core."""
    interpreter = prepare_environment(project, core)
    frontend = project.directory / "web/package.json"
    if frontend.is_file() and "build" in json.loads(frontend.read_text()).get("scripts", {}):
        run(["uv", "run", "--no-project", "--script", str(project.directory / "web/build.py"), "run", "build"])
    environment = {key: value for key, value in os.environ.items() if not key.startswith("HZ_")}
    for name in ("CONFIG_HOME", "DATA_DIR", "CACHE_DIR", "STATE_DIR", "LOG_DIR"):
        environment[f"HZ_{name}"] = str(project.directory / ".preview" / name.lower())
    environment["HZ_PLUGINS_ENABLED"] = "true"
    print("Preview uses isolated state. Restart after rebuilding view assets; Ctrl-C stops it.", flush=True)
    run(
        [str(interpreter), "-m", "heinzel", "ui", "--no-browser", "--port", "0"],
        cwd=project.directory,
        env=environment,
        timeout=None,
    )


def acceptance(project: Project, core: str | None) -> None:
    """Install core and this plugin's wheel, then run only its mounted browser contract tests."""
    record = validate_lock(project, core)
    build(project)
    selected = core or f"heinzel=={record['core']['version']}"
    environment = project.directory / ".acceptance"
    interpreter = environment / "bin/python"
    if not interpreter.is_file():
        run(["uv", "venv", "--python", "3.12", str(environment)])
    run(
        [
            "uv",
            "pip",
            "sync",
            "--python",
            str(interpreter),
            "--require-hashes",
            str(project.directory / "requirements.lock"),
        ]
    )
    wheels = list((project.directory / "dist").glob(f"{project.name.replace('-', '_')}-{project.version}-*.whl"))
    if len(wheels) != 1:
        raise ValueError("Build exactly one owning wheel before acceptance")
    run(["uv", "pip", "install", "--python", str(interpreter), "--no-deps", selected, str(wheels[0])])
    run(["uv", "pip", "check", "--python", str(interpreter)])
    suites = [f"tests/{name}" for name in ("acceptance", "browser") if (project.directory / "tests" / name).is_dir()]
    if not suites:
        raise ValueError("Declare installed-wheel tests under tests/acceptance or tests/browser")
    environment = dict(os.environ) | {"PLUGIN_TEST_CORE": selected, "PLUGIN_TEST_WHEEL": str(wheels[0])}
    run([str(interpreter), "-m", "pytest", *suites, "-q"], cwd=project.directory, env=environment)


def build(project: Project) -> None:
    """Build exactly one project's self-contained artifacts."""
    validate_lock(project, None)
    run(
        [
            "uv",
            "build",
            "--project",
            str(project.directory),
            "--build-constraints",
            str(project.directory / "requirements.lock"),
            "--out-dir",
            str(project.directory / "dist"),
        ]
    )


def profile(inventory: list[Project], core: Path, destination: Path, base_url: str | None) -> dict:
    """Only the selected composition repository can enroll defaults; topic discovery never feeds this function."""
    wheels = [core]
    for project in inventory:
        if "standard" not in project.options.get("profiles", []):
            continue
        matches = list((project.directory / "dist").glob(f"{project.name.replace('-', '_')}-{project.version}-*.whl"))
        if len(matches) != 1:
            raise ValueError(f"Build {project.name} {project.version} first")
        wheels.append(matches[0])
    artifacts = []
    core_version = None
    for wheel in wheels:
        with zipfile.ZipFile(wheel) as archive:
            from email.parser import Parser

            metadata = Parser().parsestr(
                archive.read(next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))).decode()
            )
            name, version = metadata["Name"], metadata["Version"]
        if name == "heinzel":
            core_version = version
        else:
            if core_version is None:
                raise ValueError("Read the core artifact before plugins")
            dependencies = [Requirement(value) for value in metadata.get_all("Requires-Dist", [])]
            core_dependencies = [item for item in dependencies if item.name == "heinzel"]
            if not core_dependencies or any(Version(core_version) not in item.specifier for item in core_dependencies):
                raise ValueError(f"{name} does not support core {core_version}")
        artifacts.append(
            {
                "name": name,
                "version": version,
                "filename": wheel.name,
                "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
                "url": f"{base_url.rstrip('/')}/{wheel.name}" if base_url else str(wheel.resolve()),
            }
        )
    if core_version is None:
        raise ValueError("The composition needs its core wheel")
    result = {"format": 1, "core_version": core_version, "sdk": 1, "artifacts": artifacts}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + "\n")
    return result


def audit(project: Project, core: str | None) -> None:
    """Audit only the installed runtime closure of the owning plugin."""
    interpreter = prepare_environment(project, core)
    run(["uv", "run", "--frozen", "--group", "audit", "python", "scripts/audit.py", str(interpreter), project.name])


def release_info(project: Project) -> dict:
    """Derive one independent release identity and its exact artifacts from owning metadata."""
    if str(Version(project.version)) != project.version:
        raise ValueError("Use a canonical plugin version")
    basename = f"{project.name.replace('-', '_')}-{project.version}"
    artifacts = sorted((project.directory / "dist").glob(f"{basename}-*.whl"))
    sdist = project.directory / "dist" / f"{basename}.tar.gz"
    if sdist.is_file():
        artifacts.append(sdist)
    return {
        "name": project.name,
        "version": project.version,
        "tag": f"{project.name}/v{project.version}",
        "path": str(project.directory.relative_to(ROOT)),
        "artifacts": [str(path) for path in artifacts],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "list",
            "plan",
            "test",
            "check",
            "build",
            "profile",
            "release",
            "boundary",
            "lock",
            "acceptance",
            "preview",
            "release-info",
            "audit",
        ],
    )
    parser.add_argument("name", nargs="?", default=os.environ.get("PLUGIN_NAME") or None)
    parser.add_argument(
        "--core",
        default=os.environ.get("PLUGIN_CORE") or None,
        help="Candidate core wheel or immutable artifact URL; otherwise use the declared released core",
    )
    parser.add_argument("--base", default=os.environ.get("PLUGIN_BASE") or None)
    parser.add_argument(
        "--contract",
        action="append",
        default=[os.environ["PLUGIN_CONTRACT"]] if os.environ.get("PLUGIN_CONTRACT") else [],
        help="Check consumers of a changed public contract",
    )
    parser.add_argument("--changed", action="append", default=[])
    parser.add_argument("--output", type=Path, default=ROOT / "dist/standard.json")
    parser.add_argument("--base-url")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    inventory = projects()
    if args.command == "list":
        print(
            json.dumps(
                [
                    {"name": item.name, "version": item.version, "path": str(item.directory.relative_to(ROOT))}
                    for item in inventory
                ]
            )
        )
        return 0
    if args.command == "plan":
        changed = args.changed
        if args.base:
            changed += subprocess.check_output(
                ["git", "diff", "--name-only", f"{args.base}...HEAD"], cwd=ROOT, text=True, timeout=30
            ).splitlines()
        print(json.dumps(plan(changed, inventory, contracts=args.contract, core=args.core)))
        return 0
    if args.command == "profile":
        if not args.core or not Path(args.core).is_file():
            parser.error("profile needs --core with a built wheel")
        print(json.dumps(profile(inventory, Path(args.core), args.output, args.base_url), indent=2))
        return 0
    selected = [
        item
        for item in inventory
        if item.name == args.name
        or item.name.removeprefix("heinzel-") == args.name
        or (args.name is None and item.directory == Path.cwd())
    ]
    if len(selected) != 1:
        parser.error("Choose one plugin (for example: check resource), or run from its directory")
    project = selected[0]
    if args.command == "release-info":
        print(json.dumps(release_info(project)))
    elif args.command == "lock":
        if not args.core:
            parser.error("lock needs --core with a compatible built artifact")
        lock(project, args.core)
    elif args.command == "audit":
        audit(project, args.core)
    elif args.command == "preview":
        preview(project, args.core)
    elif args.command == "acceptance":
        acceptance(project, args.core)
    elif args.command == "boundary":
        boundaries(project)
        validate_installed_core(project)
    elif args.command in {"test", "check"}:
        check(project, args.core, tests_only=args.command == "test")
    else:
        if args.command == "release":
            check(project, args.core)
        build(project)
        if args.command == "release":
            print(f"Release: {project.name}/v{project.version}; artifacts: {project.directory / 'dist'}")
            if args.publish:
                # Exact owning artifacts only; never uv publish dist/* from a monorepo root.
                paths = sorted(
                    (project.directory / "dist").glob(f"{project.name.replace('-', '_')}-{project.version}-*.whl")
                )
                sdist = project.directory / "dist" / f"{project.name.replace('-', '_')}-{project.version}.tar.gz"
                if sdist.exists():
                    paths.append(sdist)
                run(["uv", "publish", *(str(path) for path in paths)])
    return 0


if __name__ == "__main__":
    try:
        result = main()
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        sys.stderr.write(
            f"Plugin command failed: {error}\n"
            "Use a compatible core wheel; make lock NAME=<plugin> CORE=<wheel> refreshes dependencies.\n"
        )
        result = 1
    sys.exit(result)
