"""Caller approval for the advanced prepared-host capture path."""

import hashlib
import json
import os
import re
import stat
from pathlib import Path

from heinzel_plugin_tools.privacy import CaptureError, regular_bytes, safe_path

RUNTIME_FILE_LIMIT = 64 * 1024 * 1024
RUNTIME_TOTAL_LIMIT = 512 * 1024 * 1024
RUNTIME_ENTRY_LIMIT = 30000


def fingerprint(path: Path, data: bytes) -> dict:
    return {"sha256": hashlib.sha256(data).hexdigest(), "mode": stat.S_IMODE(path.stat().st_mode)}


def check_site_entry(site: Path, path: Path, data: bytes) -> None:
    """Refuse import paths and startup hooks that static local inspection cannot bind."""
    relative = path.relative_to(site)
    if len(relative.parts) == 1 and path.suffix == ".pth":
        for line in data.decode("utf-8").splitlines():
            value = line.rstrip()
            if not value or value.startswith("#"):
                continue
            if value != ".":
                raise CaptureError("Prepared host approval refuses executable .pth imports or additional import roots")
    if path.name == "direct_url.json" and path.parent.name.endswith(".dist-info"):
        if json.loads(data).get("dir_info", {}).get("editable"):
            raise CaptureError("Prepared host approval needs installed wheels; editable imports cannot be bound")


def site_fingerprints(prefix: Path, site: Path) -> dict:
    files = {}
    total = 0
    for index, item in enumerate(site.rglob("*"), start=1):
        if index > RUNTIME_ENTRY_LIMIT:
            raise CaptureError("Prepared runtime exceeds the approval inventory limit")
        relative = item.relative_to(prefix)
        site_relative = item.relative_to(site)
        path = safe_path(prefix, relative)
        top = site_relative.parts[0]
        if top.partition(".")[0] in {"sitecustomize", "usercustomize"} or top.endswith((".egg-link", ".start")):
            raise CaptureError("Prepared host approval refuses startup customization and legacy editable links")
        if path.is_dir():
            continue
        data = regular_bytes(path, RUNTIME_FILE_LIMIT)
        total += len(data)
        if len(data) > RUNTIME_FILE_LIMIT or total > RUNTIME_TOTAL_LIMIT:
            raise CaptureError("Prepared runtime exceeds the approval inventory limit")
        check_site_entry(site, path, data)
        files[relative.as_posix()] = fingerprint(path, data)
    return files


def runtime_identity(interpreter: Path) -> dict:
    """Fingerprint the selected Python and its local standard-layout virtual environment without running either."""
    invoked = interpreter.absolute()
    resolved = invoked.resolve()
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise CaptureError("The prepared interpreter must be an existing Python executable")
    prefix = invoked.parent.parent.resolve()
    sites = list(prefix.glob("lib/python*/site-packages"))
    if invoked.parent.name != "bin" or len(sites) != 1 or not (sites[0] / "heinzel").is_dir():
        raise CaptureError("Prepared host approval requires one installed Core in a standard virtual environment")
    site = safe_path(prefix, sites[0].relative_to(prefix))
    distributions = list(site.glob("heinzel-*.dist-info"))
    if len(distributions) != 1:
        raise CaptureError("Prepared host approval requires one installed Core distribution")

    config = safe_path(prefix, "pyvenv.cfg")
    config_data = regular_bytes(config, 64 * 1024)
    system_sites = [
        value.strip().lower()
        for key, separator, value in (line.partition("=") for line in config_data.decode("utf-8").splitlines())
        if separator and key.strip().lower() == "include-system-site-packages"
    ]
    if system_sites != ["false"]:
        raise CaptureError("Prepared host approval requires include-system-site-packages = false")
    files = site_fingerprints(prefix, site)
    files["pyvenv.cfg"] = fingerprint(config, config_data)
    entrypoint = safe_path(prefix, "bin/hz")
    files["bin/hz"] = fingerprint(entrypoint, regular_bytes(entrypoint, 1024 * 1024))
    if distributions[0].relative_to(prefix).joinpath("METADATA").as_posix() not in files:
        raise CaptureError("Prepared Core distribution has no metadata")
    return {
        "invoked": str(invoked),
        "resolved": str(resolved),
        "interpreter": fingerprint(resolved, regular_bytes(resolved, RUNTIME_FILE_LIMIT)),
        "prefix": str(prefix),
        "core_distribution": distributions[0].name,
        "files": files,
    }


def approval(root: Path, plan: dict, interpreter: Path) -> dict:
    """Fingerprint the exact plan, checked authoring inputs and selected runtime without launching the project."""
    from heinzel_plugin_tools.capture import OUTPUT
    from heinzel_plugin_tools.capture_linux import snapshot_files
    from heinzel_plugin_tools.capture_worker import FILE_COUNT, fingerprints

    names = [
        name for name in snapshot_files(root, plan, require_definition=False) if not Path(name).is_relative_to(OUTPUT)
    ]
    if len(names) > FILE_COUNT:
        raise CaptureError("Prepared host source exceeds the approval inventory limit")
    identity = {
        "format": 2,
        "project": str(root.resolve()),
        "plan": plan,
        "source": fingerprints(root, names),
        "runtime": runtime_identity(interpreter),
    }
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"ok": True, "prepared_approval_sha256": digest, **identity}


def require_approval(root: Path, plan: dict, interpreter: Path, reviewed: str | None) -> None:
    if not reviewed or not re.fullmatch(r"[0-9a-f]{64}", reviewed):
        raise CaptureError(
            "Prepared host capture requires a reviewed --prepared-approval SHA-256; inspect with --inspect-prepared"
        )
    if approval(root, plan, interpreter)["prepared_approval_sha256"] != reviewed:
        raise CaptureError("Prepared host approval is stale; inspect and review the current prepared inputs")
