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
import tarfile
import zipfile
from email.parser import Parser
from pathlib import Path
from urllib.parse import quote

from packaging.utils import canonicalize_name
from packaging.version import Version


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


def find_release(repository: str, tag: str) -> dict | None:
    """Resolve drafts as well as published releases; GitHub's REST tag endpoint hides drafts."""
    owner, name = repository.split("/", 1)
    answer = api(
        "graphql",
        data={
            "query": (
                "query($owner:String!,$name:String!,$tag:String!){"
                "repository(owner:$owner,name:$name){release(tagName:$tag){databaseId}}}"
            ),
            "variables": {"owner": owner, "name": name, "tag": tag},
        },
    )
    if not answer or answer.get("errors"):
        raise ValueError("GitHub could not resolve the release identity")
    data = answer.get("data")
    repo = data.get("repository") if isinstance(data, dict) else None
    if not isinstance(repo, dict) or "release" not in repo:
        raise ValueError("GitHub did not return an accessible release repository")
    identity = repo["release"]
    if identity is None:
        return None
    identifier = identity.get("databaseId") if isinstance(identity, dict) else None
    if type(identifier) is not int or identifier <= 0:
        raise ValueError("GitHub did not return a release identity")
    release = api(f"repos/{repository}/releases/{identifier}")
    if not release or release.get("id") != identifier or release.get("tag_name") != tag:
        raise ValueError("GitHub returned a different release identity")
    return release


def _app_version(tag: str) -> Version:
    raw = tag.removeprefix("app-v")
    selected = Version(raw)
    if not tag.startswith("app-v") or str(selected) != raw or selected.is_prerelease or selected.is_devrelease:
        raise ValueError("Only a canonical stable standard app can become latest")
    return selected


def _latest_setting(repository: str, tag: str, setting: str | None) -> str | None:
    if setting != "true" or not tag.startswith("app-v"):
        return setting
    selected = _app_version(tag)
    # The standard-app workflow serializes its sole promotion writer; this check prevents older retries.
    current = api(f"repos/{repository}/releases/latest", missing=True)
    if current is not None:
        current_tag = current.get("tag_name")
        if not isinstance(current_tag, str):
            raise ValueError("The current latest release identity is invalid")
        if _app_version(current_tag) > selected:
            return "false"
    return "true"


def publish(
    repository: str,
    tag: str,
    revision: str,
    artifacts: list[Path],
    *,
    pypi: bool = False,
    make_latest: str | None = None,
) -> None:
    if make_latest not in {None, "true", "false"}:
        raise ValueError("Choose an explicit true or false latest-release policy")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Use an owner/repository identity")
    if not re.fullmatch(r"[a-z0-9][a-z0-9./+-]*", tag) or not re.fullmatch(r"[a-f0-9]{40}|[a-f0-9]{64}", revision):
        raise ValueError("Use a canonical tag and exact built commit")
    if not artifacts or len(artifacts) > 128 or any(not path.is_file() or path.is_symlink() for path in artifacts):
        raise ValueError("Select the exact built artifact files")
    exact_tag(repository, tag, revision)
    release = find_release(repository, tag)
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
                "body": "Independently checked artifacts from the exact tagged source commit.",
                "draft": True,
            },
        )
    if pending:
        subprocess.run(
            ["gh", "release", "upload", tag, *(str(path) for path in pending), "--repo", repository],
            check=True,
            timeout=600,
        )
    if not release or existing_assets(api(f"repos/{repository}/releases/{release['id']}"), artifacts):
        raise ValueError("Publication is incomplete; retry the same built artifacts")
    exact_tag(repository, tag, revision)
    if release and (release.get("draft", False) or make_latest is not None):
        publication: dict[str, object] = {"draft": False}
        if make_latest is not None:
            publication["make_latest"] = _latest_setting(repository, tag, make_latest)
        api(f"repos/{repository}/releases/{release['id']}", data=publication, method="PATCH")


def tag_revision(repository: str, tag: str) -> str:
    """Read an existing immutable tag without creating or moving it."""
    reference = api(f"repos/{repository}/git/ref/tags/{quote(tag, safe='')}")
    target = reference["object"]
    for _ in range(8):
        if target["type"] != "tag":
            break
        target = api(f"repos/{repository}/git/tags/{target['sha']}")["object"]
    if target["type"] != "commit" or not re.fullmatch(r"[a-f0-9]{40}|[a-f0-9]{64}", target["sha"]):
        raise ValueError("The release tag must identify an existing source commit")
    return target["sha"]


def artifact_identity(path: Path) -> tuple[str, str]:
    """Read declared identity without importing the wheel or extracting an archive."""
    if path.name.endswith(".whl"):
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
            if len(names) != 1:
                raise ValueError("A release wheel must have exactly one metadata identity")
            with archive.open(names[0]) as stream:
                content = stream.read(1024 * 1024 + 1)
    elif path.name.endswith(".tar.gz"):
        with tarfile.open(path) as archive:
            members = [m for m in archive.getmembers() if len(Path(m.name).parts) == 2 and m.name.endswith("/PKG-INFO")]
            if len(members) != 1 or not members[0].isfile() or members[0].size > 1024 * 1024:
                raise ValueError("A release sdist must have one bounded root metadata identity")
            stream = archive.extractfile(members[0])
            if stream is None:
                raise ValueError("The release sdist metadata is absent")
            content = stream.read()
    else:
        raise ValueError("Use a wheel and source distribution")
    if len(content) > 1024 * 1024:
        raise ValueError("Release metadata exceeds its size limit")
    metadata = Parser().parsestr(content.decode())
    name, version = metadata["Name"], metadata["Version"]
    if not name or not version:
        raise ValueError("Release metadata must declare its name and version")
    return canonicalize_name(name), str(Version(version))


def restore(repository: str, tag: str, name: str, destination: Path) -> dict:
    """Restore and verify exact published plugin artifacts for composition or later registry upload."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Use an owner/repository identity")
    tag_name = tag.split("/v", 1)[0]
    if name == tag_name.removeprefix("heinzel-"):
        name = tag_name
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or not tag.startswith(f"{name}/v"):
        raise ValueError("Use this plugin's existing independent release tag")
    version = tag.removeprefix(f"{name}/v")
    if str(Version(version)) != version:
        raise ValueError("Use a canonical release version")
    revision = tag_revision(repository, tag)
    release = api(f"repos/{repository}/releases/tags/{quote(tag, safe='')}")
    assets = release.get("assets", [])
    if release.get("draft", False) or len(assets) != 2:
        raise ValueError("Use a complete published wheel/sdist release")
    expected = name.replace("-", "_") + "-" + version
    names = {asset["name"] for asset in assets}
    if not any(filename.startswith(expected + "-") and filename.endswith(".whl") for filename in names):
        raise ValueError("The release wheel does not match the selected plugin version")
    if expected + ".tar.gz" not in names:
        raise ValueError("The release source distribution does not match the selected plugin version")
    destination.mkdir(parents=True, exist_ok=False)
    files = []
    artifact_hashes = {}
    for asset in assets:
        filename = asset["name"]
        if Path(filename).name != filename or asset["size"] > 128 * 1024 * 1024:
            raise ValueError("Release artifacts must have bounded canonical filenames")
        subprocess.run(
            ["gh", "release", "download", tag, "--repo", repository, "--pattern", filename, "--dir", str(destination)],
            check=True,
            timeout=120,
        )
        artifact = destination / filename
        if artifact.stat().st_size != asset["size"]:
            raise ValueError("The release download size differs from its declared artifact")
        digest = "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest()
        if asset.get("digest") != digest or artifact_identity(artifact) != (name, version):
            raise ValueError("The downloaded release identity or digest differs; nothing will be uploaded")
        subprocess.run(
            [
                "gh",
                "attestation",
                "verify",
                str(artifact),
                "--repo",
                repository,
                "--source-ref",
                "refs/heads/main",
                "--source-digest",
                revision,
                "--signer-workflow",
                f"{repository}/.github/workflows/release.yml",
                "--deny-self-hosted-runners",
            ],
            check=True,
            timeout=120,
        )
        if "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest() != digest:
            raise ValueError("The verified release artifact changed during attestation")
        files.append(str(artifact))
        artifact_hashes[str(artifact)] = digest.removeprefix("sha256:")
    return {
        "tag": tag,
        "name": name,
        "version": version,
        "revision": revision,
        "artifacts": files,
        "artifact_hashes": artifact_hashes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--revision")
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--pypi", action="store_true")
    parser.add_argument("--make-latest", choices=("true", "false"))
    parser.add_argument("--restore", action="store_true")
    parser.add_argument("--name")
    args = parser.parse_args()
    if args.restore:
        if not args.name:
            parser.error("Restore requires the owning distribution name")
        record = restore(os.environ["GH_REPO"], args.tag, args.name, args.directory)
        print(json.dumps(record))
        if output := os.environ.get("GITHUB_OUTPUT"):
            with Path(output).open("a") as stream:
                for key in ("tag", "name", "revision"):
                    stream.write(f"{key}={record[key]}\n")
        return
    if not args.revision:
        parser.error("Publication requires the exact built revision")
    files = sorted(path for path in args.directory.iterdir() if path.name != "release.json" and path.is_file())
    publish(os.environ["GH_REPO"], args.tag, args.revision, files, pypi=args.pypi, make_latest=args.make_latest)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(f"Publication stopped: {error}") from None
