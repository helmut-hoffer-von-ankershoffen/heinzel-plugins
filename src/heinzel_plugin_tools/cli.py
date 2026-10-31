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
import shlex
import shutil
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

TOOLING_SCRIPT = Path(__file__).resolve()
ROOT = Path(os.environ.get("PLUGIN_SOURCE_ROOT") or Path.cwd()).resolve()


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
        path.startswith(("scripts/", ".github/", "tests/", "src/heinzel_plugin_tools/"))
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
            *requirements(project, "dev"),
            *requirements(project, "tooling"),
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


def released_core(project: Project) -> str:
    """Find a compatible stable registry wheel so authors need no manual artifact download."""
    with urllib.request.urlopen("https://pypi.org/pypi/heinzel/json", timeout=30) as response:  # noqa: S310
        payload = json.loads(response.read(16 * 1024 * 1024))
    candidates = {
        Version(version): files
        for version, files in payload["releases"].items()
        if not Version(version).is_prerelease and supports_core(project, version)
    }
    for version in sorted(candidates, reverse=True):
        for artifact in candidates[version]:
            if artifact["filename"].endswith("-py3-none-any.whl") and not artifact.get("yanked", False):
                return artifact["url"]
    raise ValueError("No compatible released core is available. Pass CORE=<candidate-core-wheel>.")


def lock(project: Project, core: str | None = None) -> None:
    """Resolve one portable dependency lock against a compatible candidate, keeping its wheel path out of the lock."""
    core = core or released_core(project)
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


def core_install_spec(core: str | None, version: str) -> str:
    """Keep a selected local wheel an absolute operand, even when its filename starts with an option."""
    if not core:
        return f"heinzel=={version}"
    if core.startswith("https://"):
        return core
    return str(Path(core).resolve())


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
            "--no-build",
            str(project.directory / "requirements.lock"),
        ]
    )
    selected = core_install_spec(core, record["core"]["version"])
    run(["uv", "pip", "install", "--python", str(interpreter), "--no-deps", "--no-build", selected])
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


def ruff_configuration(project: Project) -> list[str]:
    """Use the owning policy or portable defaults that recognize this project's public package roots."""
    if "ruff" in project.metadata.get("tool", {}):
        return []
    own = sorted(
        {
            value.split(":")[0].split(".")[0]
            for value in project.metadata["project"]["entry-points"]["heinzel.modules"].values()
        }
    )
    return [
        "--config",
        str(TOOLING_SCRIPT.with_name("defaults") / "ruff.toml"),
        "--config",
        f"lint.isort.known-first-party={json.dumps(own)}",
    ]


def fix(project: Project, core: str | None) -> None:
    """Format and fix only the owning plugin, refreshing its lock when dependency inputs changed."""
    path = project.directory / "plugin-lock.json"
    if not path.is_file() or json.loads(path.read_text())["inputs"] != dependency_inputs(project):
        lock(project, core)
    prepare_environment(project, core)
    for command in (
        ["ruff", "format", "src", "tests"],
        ["ruff", "check", "--fix", "src", "tests"],
        ["ruff", "format", "src", "tests"],
    ):
        run(python_command(project, core, [*command, *ruff_configuration(project)]), cwd=project.directory)


def check(project: Project, core: str | None, *, tests_only: bool = False, fast: bool = False) -> None:
    """Run only the owning package's checks against an installed core/SDK artifact."""
    prepare_environment(project, core)
    run(
        python_command(project, core, ["python", str(TOOLING_SCRIPT), "boundary", project.name]),
        cwd=project.directory,
    )
    steps = (
        []
        if tests_only
        else [
            ["ruff", "check", "--no-fix", "src", "tests"],
            ["ruff", "format", "--check", "src", "tests"],
            ["mypy", "--strict", "src"],
            ["pyright", "--pythonpath", str(project.directory / ".venv/bin/python"), "src"],
        ]
    )
    if fast:
        steps = steps[:2]
    if not tests_only:
        for command in steps[:2]:
            command += ruff_configuration(project)
    # A small plugin may contain only offline integration tests; filtering to unit would exit 5.
    # Fast skips strict types and coverage, while still checking every owning offline behavior.
    marker = "not e2e and not perf"
    test = ["pytest", "-c", "pyproject.toml", "tests", "-m", marker, "-q"]
    steps.append(test if tests_only or fast else ["coverage", "run", "-m", *test])
    if not tests_only and not fast:
        steps.append(["coverage", "report"])
    for command in steps:
        run(python_command(project, core, command), cwd=project.directory)
    if not tests_only and not fast:
        run(
            ["typos", str(project.directory)],
            cwd=project.directory,
        )
    frontend = project.directory / "web/package.json"
    if frontend.is_file():
        scripts = json.loads(frontend.read_text()).get("scripts", {})
        for step in (
            ["test"] if fast else ["typecheck", "test"] if tests_only else ["lint", "typecheck", "test", "build"]
        ):
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
    environment.pop("VIRTUAL_ENV", None)
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


def acceptance(project: Project, core: str | None, *, wheel: Path | None = None) -> None:
    """Install core and this plugin's wheel, then run only its mounted browser contract tests."""
    record = validate_lock(project, core)
    if wheel is None:
        build(project)
    selected = core_install_spec(core, record["core"]["version"])
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
            "--no-build",
            str(project.directory / "requirements.lock"),
        ]
    )
    wheels = (
        [wheel.resolve()]
        if wheel
        else list((project.directory / "dist").glob(f"{project.name.replace('-', '_')}-{project.version}-*.whl"))
    )
    if len(wheels) != 1:
        raise ValueError("Build exactly one owning wheel before acceptance")
    expected = f"{project.name.replace('-', '_')}-{project.version}-"
    if not wheels[0].is_file() or not wheels[0].name.startswith(expected) or not wheels[0].name.endswith(".whl"):
        raise ValueError("Acceptance requires the selected plugin's exact built wheel")
    from heinzel_plugin_tools.publishing import artifact_identity

    if artifact_identity(wheels[0]) != (project.name, project.version):
        raise ValueError("Acceptance wheel metadata differs from the selected plugin")
    digest = hashlib.sha256(wheels[0].read_bytes()).hexdigest()
    run(["uv", "pip", "install", "--python", str(interpreter), "--no-deps", "--no-build", selected, str(wheels[0])])
    run(["uv", "pip", "check", "--python", str(interpreter)])
    suites = [
        f"tests/{name}" for name in ("acceptance", "browser", "e2e") if (project.directory / "tests" / name).is_dir()
    ]
    if not suites:
        raise ValueError("Declare installed-wheel tests under tests/acceptance or tests/browser")
    environment = dict(os.environ) | {
        "PLUGIN_TEST_CORE": selected,
        "HZ_SPEC": selected,
        "PLUGIN_TEST_WHEEL": str(wheels[0]),
    }
    run([str(interpreter), "-m", "pytest", *suites, "-q"], cwd=project.directory, env=environment)
    if hashlib.sha256(wheels[0].read_bytes()).hexdigest() != digest:
        raise ValueError("The tested wheel changed during acceptance; rebuild and test that exact artifact again")


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


def profile(
    inventory: list[Project],
    core: Path,
    destination: Path,
    base_url: str | None,
    *,
    selected_wheels: dict[str, Path] | None = None,
) -> dict:
    """Draft locally enrolled metadata; CLI and publication require installed acceptance before exposing it."""
    wheels = [core]
    for project in inventory:
        if "standard" not in project.options.get("profiles", []):
            continue
        if selected_wheels is not None:
            matches = [selected_wheels[project.name]] if project.name in selected_wheels else []
        else:
            matches = list(
                (project.directory / "dist").glob(f"{project.name.replace('-', '_')}-{project.version}-*.whl")
            )
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
    result = {"format": 2, "core_version": core_version, "sdk": 1, "artifacts": artifacts}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + "\n")
    return result


def write_accepted_profile(
    accepted: dict,
    candidate: Path,
    destination: Path,
    base_url: str | None,
    *,
    artifact_directory: Path | None = None,
) -> dict:
    """Expose the exact accepted selection; never select or digest a replacement after acceptance."""
    if json.loads(candidate.read_text()) != accepted:
        raise ValueError("The profile changed during installed acceptance")
    artifacts = []
    for artifact in accepted["artifacts"]:
        source = Path(artifact["url"])
        if hashlib.sha256(source.read_bytes()).hexdigest() != artifact["sha256"]:
            raise ValueError("An accepted artifact changed before profile publication")
        if artifact_directory is not None:
            copied = artifact_directory / artifact["filename"]
            if hashlib.sha256(copied.read_bytes()).hexdigest() != artifact["sha256"]:
                raise ValueError("A copied artifact differs from its accepted bytes")
        artifacts.append(
            artifact | {"url": f"{base_url.rstrip('/')}/{artifact['filename']}" if base_url else artifact["url"]}
        )
    result = accepted | {"artifacts": artifacts}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + "\n")
    return result


def repository_private() -> bool:
    """Prefer the workflow's repository identity and keep an unknown local project private."""
    if value := os.environ.get("PLUGIN_PRIVATE"):
        if value not in {"true", "false"}:
            raise ValueError("PLUGIN_PRIVATE must be true or false")
        return value == "true"
    try:
        value = json.loads(
            subprocess.check_output(
                ["gh", "repo", "view", "--json", "isPrivate", "--jq", ".isPrivate"],
                cwd=ROOT,
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        return True
    return value if isinstance(value, bool) else True


def audit(project: Project, core: str | None) -> None:
    """Audit only the installed runtime closure of the owning plugin."""
    interpreter = prepare_environment(project, core)
    custom = project.options.get("audit_command")
    if custom:
        if not isinstance(custom, list) or not all(isinstance(value, str) and value for value in custom):
            raise ValueError("audit_command must be an owning command argument list")
        run(python_command(project, core, custom), cwd=project.directory)
    if repository_private():
        print(
            "Private release: locks and installed compatibility checked locally; public advisory queries disabled.",
            flush=True,
        )
        return
    run(
        [
            "uv",
            "run",
            "--no-project",
            "--with",
            "pip-audit==2.10.1",
            "--with",
            "pip-licenses==5.5.5",
            "python",
            str(TOOLING_SCRIPT.with_name("audit.py")),
            str(interpreter),
            project.name,
        ]
    )


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


def setup(project: Project, core: str | None) -> None:
    """Create the owning lock and environment, and initialize only a standalone repository."""
    if project.options.get("layout") == "standalone" and not (project.directory / ".git").exists():
        if any((parent / ".git").exists() for parent in project.directory.parents):
            raise ValueError(
                "Use --layout collection inside an existing repository; no embedded Git repository was created."
            )
        run(["git", "init", "--quiet", "-b", "main"], cwd=project.directory)
    if not (project.directory / "plugin-lock.json").is_file():
        fix(project, core)
    else:
        prepare_environment(project, core)
    print("Ready. Run make check-fast, make preview or make build.", flush=True)


def scaffold(name: str, core: str | None, template: str | None, ref: str | None, preset: str) -> None:
    """Generate one collection project and its lock without changing any parent file."""
    short = name.removeprefix("heinzel-")
    if not re.fullmatch(r"[a-z][a-z0-9-]*", short):
        raise ValueError("Use a lowercase plugin name, for example NAME=harbor.")
    destination = ROOT / "plugins" / f"heinzel-{short}"
    if destination.exists():
        raise ValueError(f"{destination} already exists; choose a new plugin name.")
    command = [
        "uv",
        "tool",
        "run",
        "--from",
        core or "heinzel>=0.9.1,<0.10",
        "hz",
        "system",
        "plugin",
        "new",
        str(destination),
        "--defaults",
        "--layout",
        "collection",
        "--preset",
        preset,
        "--data",
        f"plugin_name={short}",
    ]
    if template:
        command += ["--template", template]
    if ref:
        command += ["--ref", ref]
    with tempfile.TemporaryDirectory(prefix="hz-plugin-scaffold-") as temporary:
        environment = {key: value for key, value in os.environ.items() if not key.startswith("HZ_")}
        environment.pop("VIRTUAL_ENV", None)
        environment["HZ_PLUGINS_ENABLED"] = "false"
        for key in ("CONFIG_HOME", "DATA_DIR", "CACHE_DIR", "STATE_DIR", "LOG_DIR"):
            environment[f"HZ_{key}"] = str(Path(temporary) / key.lower())
        run(command, env=environment)
    [project] = projects(destination)
    lock(project, core)
    fix(project, core)
    print(f"Created {project.name}. Next:\n  cd {shlex.quote(str(destination))} && make check-fast", flush=True)


def require_clean_source() -> None:
    """Refuse source changes that would make provenance name a different payload."""
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True, timeout=30)
    if status.strip():
        raise ValueError("Release verification requires clean committed sources; commit the owning change first")


def verify_release(project: Project, core: str | None, destination: Path) -> dict:
    """Check one release and stage the exact wheel that passed installed acceptance."""
    require_clean_source()
    check(project, core)
    build(project)
    record = release_info(project)
    wheels = [Path(path) for path in record["artifacts"] if path.endswith(".whl")]
    if len(wheels) != 1 or len(record["artifacts"]) != 2:
        raise ValueError("A release needs exactly one owning wheel and source distribution")
    from heinzel_plugin_tools.publishing import artifact_identity

    hashes = {}
    for filename in record["artifacts"]:
        path = Path(filename)
        if artifact_identity(path) != (project.name, project.version):
            raise ValueError("Built artifact metadata differs from the selected plugin")
        hashes[path] = hashlib.sha256(path.read_bytes()).digest()
    audit(project, core)
    if any((project.directory / "tests" / name).is_dir() for name in ("acceptance", "browser", "e2e")):
        acceptance(project, core, wheel=wheels[0])
    if any(hashlib.sha256(path.read_bytes()).digest() != digest for path, digest in hashes.items()):
        raise ValueError("A built artifact changed during release verification")
    require_clean_source()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=30).strip()
    if os.environ.get("GITHUB_SHA", revision) != revision:
        raise ValueError("The checked-out source does not match the workflow revision")
    destination.mkdir(parents=True, exist_ok=False)
    staged = []
    for path in record["artifacts"]:
        source = Path(path)
        target = destination / source.name
        shutil.copyfile(source, target)
        if hashlib.sha256(target.read_bytes()).digest() != hashes[source]:
            raise ValueError("The staged artifact differs from the checked release")
        staged.append(str(target))
    record |= {"revision": revision, "artifacts": staged}
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a") as stream:
            for key in ("tag", "name", "revision"):
                stream.write(f"{key}={record[key]}\n")
    return record


def publication_registry(private: bool, requested: str | None) -> str:
    """Keep private source releases on GitHub and select the public registry explicitly."""
    if requested not in {None, "github", "pypi"}:
        raise ValueError("Choose REGISTRY=github or REGISTRY=pypi")
    if private and requested == "pypi":
        raise ValueError("PyPI is public. Private plugins publish to their private GitHub repository")
    return requested or ("github" if private else "pypi")


def dispatch_publication(project: Project, tag: str | None, registry: str | None = None) -> None:
    """Dispatch the protected main workflow; an existing tag selects verified upload-only publication."""
    if tag:
        prefix = f"{project.name}/v"
        if not tag.startswith(prefix) or str(Version(tag.removeprefix(prefix))) != tag.removeprefix(prefix):
            raise ValueError("Use this plugin's canonical existing tag, for example NAME/v0.1.0")
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True, timeout=30).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True, timeout=30).strip()
    if branch != "main" or dirty:
        raise ValueError("Commit and merge the plugin, then run publish from clean, current main")
    run(["git", "fetch", "--quiet", "origin", "main"])
    local = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=30).strip()
    remote = subprocess.check_output(["git", "rev-parse", "origin/main"], cwd=ROOT, text=True, timeout=30).strip()
    if local != remote:
        raise ValueError("Update main with git pull --ff-only before publishing")
    private = repository_private()
    registry = publication_registry(private, registry)
    if private and tag:
        raise ValueError("Private GitHub releases are already published; TAG resumes public PyPI publication only")
    command = [
        "gh",
        "workflow",
        "run",
        "release.yml",
        "--ref",
        "main",
        "--field",
        f"plugin={project.name}",
        "--field",
        "publish=true",
    ]
    if tag:
        command += ["--field", f"resume_tag={tag}"]
    command += ["--field", f"registry={registry}"]
    run(command)
    print("Dispatched the protected release workflow. Follow its verified result in GitHub Actions.", flush=True)


def hook_changes() -> list[str]:
    """Read staged or pushed plugin paths, including deletions omitted by hook filename filtering."""
    before, after = os.environ.get("PRE_COMMIT_FROM_REF"), os.environ.get("PRE_COMMIT_TO_REF")
    if before and not after:
        raise ValueError("The pre-push hook must provide PRE_COMMIT_TO_REF")
    if after and not before:
        command = ["git", "ls-tree", "-rz", "--name-only", after, "--", "plugins/"]
    else:
        scope = [before, after] if before and after else ["--cached"]
        command = ["git", "diff", "--name-only", "--no-renames", "-z", *scope, "--", "plugins/"]
    changed = subprocess.check_output(
        command,
        cwd=ROOT,
        text=True,
        timeout=30,
    )
    return [path for path in changed.split("\0") if path]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "list",
            "new",
            "setup",
            "fix",
            "plan",
            "test",
            "check",
            "check-fast",
            "check-changed",
            "preflight",
            "build",
            "profile",
            "release",
            "verify-release",
            "publish",
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
    parser.add_argument("--changed", action="extend", nargs="+", default=[])
    parser.add_argument("--git-hook", action="store_true", help="Include staged or pushed plugin deletions")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--wheel", type=Path, help="Test this exact prebuilt owning wheel without rebuilding it")
    parser.add_argument(
        "--tag",
        default=os.environ.get("PLUGIN_TAG") or None,
        help="Existing verified release to upload without rebuilding",
    )
    parser.add_argument("--template", default=os.environ.get("PLUGIN_TEMPLATE") or None)
    parser.add_argument("--ref", default=os.environ.get("PLUGIN_TEMPLATE_REF") or None)
    parser.add_argument(
        "--preset", choices=["minimal", "contributions"], default=os.environ.get("PLUGIN_PRESET") or "minimal"
    )
    parser.add_argument("--registry", choices=["github", "pypi"], default=os.environ.get("PLUGIN_REGISTRY") or None)
    parser.add_argument("--base-url")
    parser.add_argument("--publish", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.base and args.base.startswith("-"):
        parser.error("--base must be a revision, not a Git option")
    if args.publish:
        parser.error("Local release previews artifacts only. Publish through the protected release workflow.")
    inventory = projects()
    if args.command == "check-changed":
        changed = hook_changes() if args.git_hook else args.changed
        selected = {entry["name"] for entry in plan(changed, inventory, ROOT)["include"]}
        for project in inventory:
            if project.name in selected:
                check(project, args.core, fast=True)
        return 0
    if args.command == "new":
        if not args.name:
            parser.error("Choose a plugin name, for example: new harbor")
        scaffold(args.name, args.core, args.template, args.ref, args.preset)
        return 0
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
                ["git", "diff", "--name-only", "--end-of-options", f"{args.base}...HEAD", "--"],
                cwd=ROOT,
                text=True,
                timeout=30,
            ).splitlines()
        print(json.dumps(plan(changed, inventory, ROOT, contracts=args.contract, core=args.core)))
        return 0
    if args.command == "profile":
        from heinzel_plugin_tools.installation import verify_profile

        if not args.core or not Path(args.core).is_file():
            parser.error("profile needs --core with a built wheel")
        with tempfile.TemporaryDirectory(prefix="hz-profile-draft-") as temporary:
            candidate = Path(temporary) / "standard.json"
            accepted = profile(inventory, Path(args.core), candidate, None)
            verify_profile(Path(args.core), candidate)
            result = write_accepted_profile(
                accepted, candidate, args.output or ROOT / "dist/standard.json", args.base_url
            )
        print(json.dumps(result, indent=2))
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
        lock(project, args.core)
    elif args.command == "setup":
        setup(project, args.core)
    elif args.command == "fix":
        fix(project, args.core)
    elif args.command == "publish":
        dispatch_publication(project, args.tag, args.registry)
    elif args.command == "verify-release":
        print(json.dumps(verify_release(project, args.core, args.output or ROOT / "release-dist")))
    elif args.command == "audit":
        audit(project, args.core)
    elif args.command == "preview":
        preview(project, args.core)
    elif args.command == "acceptance":
        acceptance(project, args.core, wheel=args.wheel)
    elif args.command == "boundary":
        boundaries(project)
        validate_installed_core(project)
    elif args.command in {"test", "check", "check-fast", "preflight"}:
        check(project, args.core, tests_only=args.command == "test", fast=args.command == "check-fast")
        if args.command == "preflight":
            build(project)
            audit(project, args.core)
            if any((project.directory / "tests" / name).is_dir() for name in ("acceptance", "browser", "e2e")):
                wheel = next(
                    (project.directory / "dist").glob(f"{project.name.replace('-', '_')}-{project.version}-*.whl")
                )
                acceptance(project, args.core, wheel=wheel)
    else:
        if args.command == "release":
            check(project, args.core)
        build(project)
        if args.command == "release":
            print(f"Release: {project.name}/v{project.version}; artifacts: {project.directory / 'dist'}")
    return 0


def entrypoint() -> int:
    """Report an actionable command failure without an implementation traceback."""
    try:
        return main()
    except KeyboardInterrupt:
        print("Stopped.", file=sys.stderr)
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        sys.stderr.write(f"Plugin command failed: {error}\n")
        return 1


if __name__ == "__main__":
    sys.exit(entrypoint())
