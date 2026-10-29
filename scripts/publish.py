# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Publish an immutable artifact set, binding its tag to the built commit and safely resuming partial publication."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import quote


def api(path: str, *, data: dict | None = None, missing: bool = False, method: str = "POST") -> dict | None:
    command = ["gh", "api", path]
    if data is not None:
        command += ["--method", method, "--input", "-"]
    result = subprocess.run(
        command, input=json.dumps(data) if data else None, capture_output=True, text=True, check=False, timeout=60
    )
    if result.returncode:
        if missing and "(HTTP 404)" in result.stderr:
            return None
        raise ValueError(f"GitHub request failed for {path}: {result.stderr.strip()}")
    return json.loads(result.stdout)


def exact_tag(repository: str, tag: str, revision: str) -> None:
    path = f"repos/{repository}/git/ref/tags/{quote(tag, safe='')}"
    reference = api(path, missing=True)
    if reference is None:
        api(f"repos/{repository}/git/refs", data={"ref": f"refs/tags/{tag}", "sha": revision})
        reference = api(path)
    target = reference["object"]
    for _ in range(8):
        if target["type"] != "tag":
            break
        target = api(f"repos/{repository}/git/tags/{target['sha']}")["object"]
    if target["type"] != "commit" or target["sha"] != revision:
        raise ValueError(f"{tag} does not point at the built commit; nothing was published")


def existing_assets(release: dict | None, artifacts: list[Path]) -> list[Path]:
    existing = {asset["name"]: asset for asset in (release or {}).get("assets", [])}
    if set(existing) - {path.name for path in artifacts}:
        raise ValueError("Existing release has unexpected artifacts; refusing to alter it")
    missing = []
    for artifact in artifacts:
        old = existing.get(artifact.name)
        digest = "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest()
        if old is None:
            missing.append(artifact)
        elif old.get("digest") != digest:
            raise ValueError(f"Existing artifact differs or has no verifiable digest: {artifact.name}")
    return missing


def publish(repository: str, tag: str, revision: str, artifacts: list[Path], *, pypi: bool = False) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Use an owner/repository identity")
    if not re.fullmatch(r"[a-z0-9][a-z0-9./+-]*", tag) or not re.fullmatch(r"[a-f0-9]{40}|[a-f0-9]{64}", revision):
        raise ValueError("Use a canonical tag and exact built commit")
    if not artifacts or len(artifacts) > 128 or any(not path.is_file() or path.is_symlink() for path in artifacts):
        raise ValueError("Select the exact built artifact files")
    exact_tag(repository, tag, revision)
    path = f"repos/{repository}/releases/tags/{quote(tag, safe='')}"
    release = api(path, missing=True)
    pending = existing_assets(release, artifacts)
    if release is not None and not release.get("draft", False) and pending:
        raise ValueError("A published release is incomplete; refusing to change immutable published artifacts")
    if pypi:
        subprocess.run(
            ["uv", "publish", "--check-url", "https://pypi.org/simple", *(str(path) for path in artifacts)],
            check=True,
            timeout=600,
        )
    if release is None:
        release = api(
            f"repos/{repository}/releases",
            data={
                "tag_name": tag,
                "target_commitish": revision,
                "name": tag,
                "body": "Independently checked artifacts with build provenance.",
                "draft": True,
            },
        )
    if pending:
        subprocess.run(
            ["gh", "release", "upload", tag, *(str(path) for path in pending), "--repo", repository],
            check=True,
            timeout=600,
        )
    if existing_assets(api(path), artifacts):
        raise ValueError("Publication is incomplete; retry the same built artifacts")
    exact_tag(repository, tag, revision)
    if release and release.get("draft", False):
        api(f"repos/{repository}/releases/{release['id']}", data={"draft": False}, method="PATCH")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--pypi", action="store_true")
    args = parser.parse_args()
    files = sorted(path for path in args.directory.iterdir() if path.name != "release.json" and path.is_file())
    publish(os.environ["GH_REPO"], args.tag, args.revision, files, pypi=args.pypi)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"Publication stopped: {error}") from None
