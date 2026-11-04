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
pending = [(sys.argv[1], frozenset())]
seen, versions = set(), {}
while pending:
    name, extras = pending.pop()
    name = canonicalize_name(name)
    if (name, extras) in seen:
        continue
    seen.add((name, extras))
    distribution = metadata.distribution(name)
    versions[name] = distribution.version
    for text in distribution.requires or []:
        requirement = Requirement(text)
        environment = default_environment()
        active = requirement.marker is None or any(
            requirement.marker.evaluate(environment | {"extra": extra}) for extra in extras | {""}
        )
        if active:
            pending.append((requirement.name, frozenset(requirement.extras)))
print(json.dumps(versions))
"""


def main() -> None:
    interpreter, name = sys.argv[1:]
    vendored = vendor.project(Path.cwd())
    result = subprocess.run([interpreter, "-c", INSPECT, name], check=True, text=True, capture_output=True, timeout=60)
    versions = json.loads(result.stdout)
    allowlist = Path(".license-allowlist")
    if not allowlist.is_file():
        allowlist = Path(__file__).with_name("defaults") / "license-allowlist"
    allowed = ";".join(
        line.strip() for line in allowlist.read_text().splitlines() if line.strip() and not line.startswith("#")
    )
    if vendored.files and not any(
        license_name and license_name in vendored.license_expression for license_name in allowed.split(";")
    ):
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
        subprocess.run(
            [sys.executable, "-m", "pip_audit", "--strict", "--disable-pip", "--no-deps", "-r", str(requirements)],
            check=True,
            timeout=300,
        )


if __name__ == "__main__":
    main()
