"""Select a published SDK whose independently verified standard composition is still missing."""

import hashlib
import json
import os
import re
from http import HTTPStatus
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import urlopen

from packaging.utils import parse_wheel_filename
from packaging.version import Version

from heinzel_plugin_tools.publishing import api, find_release

CORE_REPOSITORY = "helmut-hoffer-von-ankershoffen/heinzel"
EDGE_POINTER = f"https://github.com/{CORE_REPOSITORY}/releases/download/edge-channel/edge.json"
MAX_METADATA = 2 * 1024 * 1024


def download(url, limit=MAX_METADATA):
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"pypi.org", "github.com"}
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise ValueError("Release metadata must come from the official HTTPS endpoints")
    with urlopen(url, timeout=30) as response:  # noqa: S310 - official HTTPS endpoints checked above
        if not response.url.startswith("https://"):
            raise ValueError("Release metadata redirected away from HTTPS")
        content = response.read(limit + 1)
    if len(content) > limit:
        raise ValueError("Public SDK metadata exceeds the release-selection limit")
    return content


def package(version=""):
    suffix = f"{version}/" if version else ""
    return json.loads(download(f"https://pypi.org/pypi/heinzel/{suffix}json"))


def complete_app(repository, version, release, metadata):
    """Verify the profile and every declared asset before classifying a published app as a no-op."""
    assets = {item["name"]: item for item in release.get("assets", [])}
    if len(assets) != len(release.get("assets", [])) or "standard.json" not in assets:
        raise ValueError("Published app assets are incomplete; operator review is required")
    manifest = assets["standard.json"]
    if not 0 < manifest.get("size", 0) <= 1024 * 1024:
        raise ValueError("Published app profile has an invalid size; operator review is required")
    base = f"https://github.com/{repository}/releases/download/app-v{version}"
    content = download(f"{base}/standard.json", 1024 * 1024)
    if manifest.get("digest") != "sha256:" + hashlib.sha256(content).hexdigest():
        raise ValueError("Published app profile digest differs; operator review is required")
    profile = json.loads(content)
    if (
        set(profile) != {"format", "sdk", "core_version", "artifacts"}
        or type(profile["format"]) is not int
        or profile["format"] not in {1, 2}
        or profile["sdk"] != 1
        or profile["core_version"] != version
        or not isinstance(profile["artifacts"], list)
        or not 1 <= len(profile["artifacts"]) <= 64
    ):
        raise ValueError("Published app profile is invalid; operator review is required")
    names = set()
    for artifact in profile["artifacts"]:
        if set(artifact) != {"name", "version", "filename", "sha256", "url"}:
            raise ValueError("Published app artifact is invalid; operator review is required")
        if (
            not all(isinstance(value, str) for value in artifact.values())
            or len(artifact["version"]) > 80
            or len(artifact["filename"]) > 240
            or not re.fullmatch(r"[A-Za-z0-9_.+-]+\.whl", artifact["filename"])
            or len(artifact["url"]) > 4096
        ):
            raise ValueError("Published app artifact exceeds the installer contract; operator review is required")
        name, wheel_version, _, _ = parse_wheel_filename(artifact["filename"])
        if (
            name != artifact["name"]
            or str(wheel_version) != artifact["version"]
            or name in names
            or not re.fullmatch(r"heinzel(?:-[a-z0-9]+(?:-[a-z0-9]+)*)?", name)
            or not re.fullmatch(r"[a-f0-9]{64}", artifact["sha256"])
            or artifact["url"] != f"{base}/{artifact['filename']}"
        ):
            raise ValueError("Published app artifact identity is invalid; operator review is required")
        names.add(name)
        asset = assets.get(artifact["filename"])
        if not asset or asset.get("digest") != "sha256:" + artifact["sha256"]:
            raise ValueError("Published app is missing a matching provider asset; operator review is required")
        if name == "heinzel":
            public = next((item for item in metadata["urls"] if item["filename"] == artifact["filename"]), None)
            if (
                artifact["version"] != version
                or not public
                or public.get("yanked")
                or public["digests"]["sha256"] != artifact["sha256"]
            ):
                raise ValueError("Published app does not match its public SDK; operator review is required")
    if "heinzel" not in names:
        raise ValueError("Published app contains no SDK; operator review is required")


def select(repository, *, version="", core_wheel=""):
    """Return a fully published candidate, or None when its composition already exists."""
    if bool(version) != bool(core_wheel):
        raise ValueError("An explicit composition needs both its SDK version and official wheel")
    metadata = package(version)
    version = version or metadata["info"]["version"]
    parsed = Version(version)
    if (
        str(parsed) != version
        or parsed.is_prerelease
        or parsed.is_devrelease
        or parsed.local
        or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version)
    ):
        raise ValueError("Only canonical stable SDK releases can become the standard app")
    if metadata["info"]["version"] != version:
        raise ValueError("Explicit SDK metadata does not match the requested release")
    filename = f"heinzel-{version}-py3-none-any.whl"
    expected = f"https://github.com/{CORE_REPOSITORY}/releases/download/v{version}/{filename}"
    if core_wheel and core_wheel != expected:
        raise ValueError("The composition must use the official immutable SDK wheel")
    existing = find_release(repository, f"app-v{version}")
    if existing:
        if existing.get("draft") or existing.get("prerelease"):
            raise ValueError(
                "An unpublished or prerelease app already owns this identity; resume it with operator review"
            )
        complete_app(repository, version, existing, metadata)
        return None
    if api(f"repos/{repository}/git/ref/tags/app-v{version}", missing=True):
        raise ValueError("An existing app tag has no release; operator review is required before recomposing")
    released = api(f"repos/{CORE_REPOSITORY}/releases/tags/v{version}", missing=True)
    if not released or released.get("draft") or released.get("prerelease"):
        return None
    wheel = next((asset for asset in released.get("assets", []) if asset["name"] == filename), None)
    public = next((item for item in metadata["urls"] if item["filename"] == filename and not item["yanked"]), None)
    if wheel is None or public is None:
        return None
    if wheel.get("digest") != f"sha256:{public['digests']['sha256']}":
        raise ValueError("The official GitHub SDK wheel does not match its PyPI publication")
    return {"version": version, "core_wheel": expected}


def select_edge(repository):
    """The newest edge SDK from its channel pointer, unless its composition exists (ADR 0114 in the core)."""
    pointer = json.loads(download(EDGE_POINTER, 4096))
    version = pointer["version"]
    parsed = Version(version)
    expected = (
        f"https://github.com/{CORE_REPOSITORY}/releases/download/edge-v{version}/heinzel-{version}-py3-none-any.whl"
    )
    if str(parsed) != version or not parsed.is_devrelease or pointer["wheel"] != expected:
        raise ValueError("The edge pointer does not name an edge release")
    if find_release(repository, f"app-v{version}"):
        return None
    return {"version": version, "core_wheel": expected}


def selected(repository, version, core_wheel):
    """An explicit release, else a missing stable composition, else a missing edge one."""
    if version and Version(version).is_devrelease:
        return select_edge(repository)
    chosen = select(repository, version=version, core_wheel=core_wheel)
    if chosen or version:
        return chosen
    try:
        return select_edge(repository)
    except HTTPError as error:
        if error.code == HTTPStatus.NOT_FOUND:  # no edge channel yet
            return None
        raise


def main():
    chosen = selected(os.environ["GH_REPO"], os.environ.get("VERSION", ""), os.environ.get("CORE_URL", ""))
    if chosen:
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
            for key, value in chosen.items():
                output.write(f"{key}={value}\n")
        print(f"Compose the standard app for published SDK {chosen['version']}")
    else:
        print("No missing published standard app composition")


if __name__ == "__main__":
    main()
