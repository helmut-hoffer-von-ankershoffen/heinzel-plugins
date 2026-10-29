"""Audit one installed plugin's runtime closure without auditing developer tools or acquiring sibling environments."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

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
    result = subprocess.run([interpreter, "-c", INSPECT, name], check=True, text=True, capture_output=True, timeout=60)
    versions = json.loads(result.stdout)
    allowed = ";".join(
        line.strip()
        for line in Path(".license-allowlist").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    )
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
        requirements.write_text(
            "\n".join(
                f"{package}=={version}"
                for package, version in sorted(versions.items())
                if package not in {name, "heinzel"}
            )
            + "\n"
        )
        subprocess.run(
            [sys.executable, "-m", "pip_audit", "--strict", "--disable-pip", "--no-deps", "-r", str(requirements)],
            check=True,
            timeout=300,
        )


if __name__ == "__main__":
    main()
