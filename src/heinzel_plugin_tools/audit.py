"""Audit one installed plugin's runtime closure without auditing developer tools or acquiring sibling environments."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__:
    from heinzel_plugin_tools import vendor
else:
    import vendor

# Execute dependency inspection with the owning interpreter, never the tooling environment's distributions.
INSPECT = """
import json, sys
from importlib import metadata
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

def requirements(name, extras):
    for text in metadata.distribution(name).requires or []:
        requirement = Requirement(text)
        environment = default_environment()
        if requirement.marker is None or any(
            requirement.marker.evaluate(environment | {"extra": extra}) for extra in extras | {""}
        ):
            yield requirement

def closure(start):
    pending = [(start, frozenset())]
    seen, versions = set(), {}
    while pending:
        name, extras = pending.pop()
        name = canonicalize_name(name)
        if (name, extras) in seen:
            continue
        seen.add((name, extras))
        versions[name] = metadata.distribution(name).version
        pending += [(item.name, frozenset(item.extras)) for item in requirements(name, extras)]
    return versions

owner = closure(sys.argv[1])
direct = sorted({canonicalize_name(item.name) for item in requirements(sys.argv[1], frozenset())})
core = sorted(closure("heinzel")) if "heinzel" in owner else []
print(json.dumps({"versions": owner, "direct": direct, "core": core}))
"""

# Which security relock case applies to a vulnerable package (plugins ADR 0003).
CASES = {
    "core": "comes through Core: Core's release fixes it; relock only, no plugin bump",
    "declared": "declared dependency: raise its floor in project.dependencies, patch bump and changelog",
    "transitive": "comes only through this plugin's dependencies: add a direct floor (pkg>=fixed), patch bump",
}


def security_case(package: str, closure: dict) -> str:
    """Core forces a fix it releases; otherwise the plugin's own metadata must, through a floor."""
    if package in closure["core"]:
        return "core"
    return "declared" if package in closure["direct"] else "transitive"


def report_cases(report: Path, closure: dict) -> None:
    """Name the security case of every vulnerable package pip-audit found."""
    if not report.is_file():
        return
    for dependency in json.loads(report.read_text()).get("dependencies", []):
        if dependency.get("vulns"):
            case = security_case(dependency["name"], closure)
            fixes = sorted({fix for vuln in dependency["vulns"] for fix in vuln.get("fix_versions", [])})
            identifiers = ", ".join(vuln["id"] for vuln in dependency["vulns"])
            print(
                f"{dependency['name']} {dependency['version']} ({identifiers}; fixed in {', '.join(fixes) or 'none'})"
                f": {CASES[case]}",
                flush=True,
            )


def main() -> None:
    interpreter, name = sys.argv[1:]
    vendored = vendor.project(Path.cwd())
    result = subprocess.run([interpreter, "-c", INSPECT, name], check=True, text=True, capture_output=True, timeout=60)
    closure = json.loads(result.stdout)
    versions = closure["versions"]
    allowlist = Path(".license-allowlist")
    if not allowlist.is_file():
        allowlist = Path(__file__).with_name("defaults") / "license-allowlist"
    allowed_expressions = [
        line.strip() for line in allowlist.read_text().splitlines() if line.strip() and not line.startswith("#")
    ]
    allowed = ";".join(allowed_expressions)
    if vendored.files and vendored.license_expression not in allowed_expressions:
        raise ValueError("Vendored upstream license is outside the owning allowlist")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "piplicenses",
            "--python",
            interpreter,
            "--from=mixed",
            "--partial-match",
            f"--allow-only={allowed}",
            "--packages",
            *sorted(versions),
        ],
        check=True,
        timeout=60,
    )
    with tempfile.TemporaryDirectory(prefix="hz-plugin-audit-") as temporary:
        requirements = Path(temporary) / "runtime.txt"
        # Own source and candidate core are checked by their respective pipelines. Their transitive runtime
        # packages are checked here; unpublished local distribution versions cannot be looked up on PyPI.
        runtime = {
            f"{package}=={version}" for package, version in sorted(versions.items()) if package not in {name, "heinzel"}
        }
        if vendored.files:
            # Keep the exact upstream version visible even when the external
            # distribution is absent, or a different version is installed.
            runtime.add(f"{vendored.distribution}=={vendored.version}")
            print(
                json.dumps(
                    {
                        "vendored": vendored.distribution,
                        "version": vendored.version,
                        "license": vendored.license_expression,
                        "files": list(vendored.files),
                    }
                )
            )
        requirements.write_text("\n".join(sorted(runtime)) + "\n")
        report = Path(temporary) / "audit.json"
        command = [sys.executable, "-m", "pip_audit", "--strict", "--disable-pip", "--no-deps", "-r", str(requirements)]
        command += ["--format", "json", "--output", str(report)]
        audited = subprocess.run(command, check=False, timeout=300)
        report_cases(report, closure)
        if audited.returncode:
            raise subprocess.CalledProcessError(audited.returncode, command)


if __name__ == "__main__":
    main()
