"""The same disposable Linux browser and source snapshot for authors and CI."""

import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from heinzel_plugin_tools.privacy import CaptureError, _confidentiality_module, regular_bytes, safe_path

IMAGE = (
    "mcr.microsoft.com/playwright/python:v1.64.1-noble@sha256:"
    "330d401ae23c905896a0c26c66c36fc971b621519e7b11b435a8328d7bf6e031"
)
PLATFORM = "linux/amd64"
DOCKERFILE = f"""FROM {IMAGE}
RUN apt-get update -qq && apt-get install -y -qq git && python -m pip install --no-cache-dir uv==0.13.7
"""


def configured_terms() -> str:
    """Require the real external scanner policy; never put its contents in command arguments or logs."""
    checker = _confidentiality_module()
    terms = checker.load_terms() if checker else []
    if not terms:
        raise CaptureError("Canonical capture requires configured confidential terms, including on an author's machine")
    return "\n".join(terms) + "\n"


def command(argv: list[str], *, cwd: Path, capture: bool = False, timeout: int = 900):
    try:
        return subprocess.run(argv, cwd=cwd, text=True, capture_output=capture, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CaptureError(
            "Canonical Linux capture needs a running Docker engine and the pinned public image"
        ) from error


def copy_draft(source: Path, root: Path, plan: dict) -> None:
    """Import only bounded, validated scene artifacts, never arbitrary container paths."""
    from heinzel_plugin_tools import capture

    draft = source / capture.DRAFT
    manifest = json.loads(regular_bytes(safe_path(draft, capture.DRAFT_MANIFEST), 1024 * 1024))
    capture.draft_artifacts(source, plan, manifest)
    names = [f"{scene['name']}.{ext}" for scene in plan["scenes"] for ext in ("png", "txt")]
    names += [capture.DRAFT_MANIFEST, "index.html"]
    payload = {name: regular_bytes(safe_path(draft, name), 20 * 1024 * 1024) for name in names}
    target = safe_path(root, capture.DRAFT)
    target.mkdir(parents=True, exist_ok=True)
    destinations = {name: safe_path(target, name) for name in payload}
    for name, data in payload.items():
        destination = destinations[name]
        with tempfile.NamedTemporaryFile(dir=target, delete=False) as handle:
            handle.write(data)
            staged = Path(handle.name)
        try:
            safe_path(target, name)
            os.replace(staged, destination)
        finally:
            staged.unlink(missing_ok=True)


def run(args) -> dict:
    """Capture a copy without host tools, applications, credentials, sockets or Python environments."""
    from heinzel_plugin_tools import capture

    if args.headed:
        raise CaptureError("Canonical Linux capture is headless; review its generated contact sheet")
    root = args.project.resolve()
    plan = capture.read_plan(root)
    terms = configured_terms()
    original_inputs = capture.input_digest(root, plan)
    if args.verify:
        capture.check_capture(root)
    with tempfile.TemporaryDirectory(prefix="hz-gallery-linux-") as scratch:
        work = Path(scratch)
        project = work / "project"
        shutil.copytree(
            root,
            project,
            symlinks=True,
            ignore=shutil.ignore_patterns(
                ".git", ".venv", "node_modules", "__pycache__", ".preview", ".acceptance", ".pytest_cache", "dist"
            ),
        )
        runtime = work / "runtime"
        package = Path(__file__).resolve().parent
        shutil.copytree(package, runtime / "src/heinzel_plugin_tools", ignore=shutil.ignore_patterns("__pycache__"))
        (runtime / "scripts").mkdir()
        shutil.copyfile(Path(_confidentiality_module().__file__), runtime / "scripts/check_confidentiality.py")
        (work / "terms").write_text(terms)
        build = work / "image"
        build.mkdir()
        (build / "Dockerfile").write_text(DOCKERFILE)
        identity = work / "image-id"
        print("Preparing the pinned Linux capture image…", file=sys.stderr, flush=True)
        built = command(
            ["docker", "build", "--platform", PLATFORM, "--quiet", "--iidfile", str(identity), str(build)],
            cwd=work,
            capture=True,
        )
        if built.returncode or not identity.is_file():
            raise CaptureError("The pinned canonical Linux capture image could not be built")
        image = identity.read_text().strip()
        if not image.startswith("sha256:") or len(image) != 71:
            raise CaptureError("Docker returned no immutable capture image identity")
        core = args.core
        if core and Path(core).expanduser().is_file():
            selected = Path(core).expanduser()
            (work / "core").mkdir()
            shutil.copyfile(selected, work / "core" / selected.name)
            core = "/capture/core/" + selected.name
        child = [
            "uv",
            "run",
            "--no-project",
            "--script",
            "/capture/runtime/src/heinzel_plugin_tools/capture.py",
            "--project",
            "/capture/project",
            "--container-worker",
            "--json",
            "--verify" if args.verify else "--draft",
        ]
        if core:
            child += ["--core", core]
        if args.strict_images:
            child += ["--strict-images"]
        print("Capturing inside the isolated Linux worker…", file=sys.stderr, flush=True)
        container = "hz-gallery-" + uuid.uuid4().hex
        try:
            result = command(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--name",
                    container,
                    "--platform",
                    PLATFORM,
                    "--ipc=private",
                    "--shm-size=1g",
                    "--mount",
                    f"type=bind,source={work},target=/capture",
                    "--workdir",
                    "/capture/project",
                    "--env",
                    "LANG=C.UTF-8",
                    "--env",
                    "LC_ALL=C.UTF-8",
                    "--env",
                    "TZ=UTC",
                    "--env",
                    "GITHUB_ACTIONS=true",
                    "--env",
                    "CONFIDENTIALITY_REQUIRED=true",
                    "--env",
                    "CONFIDENTIAL_TERMS_FILE=/capture/terms",
                    image,
                    *child,
                ],
                cwd=work,
                capture=True,
            )
        finally:
            with contextlib.suppress(CaptureError):
                command(["docker", "rm", "--force", container], cwd=work, capture=True, timeout=30)
        try:
            report = json.loads(result.stdout)
        except (ValueError, TypeError) as error:
            raise CaptureError("Canonical Linux capture returned no result; no gallery was changed") from error
        if capture.input_digest(root, capture.read_plan(root)) != original_inputs:
            raise CaptureError("Screenshot inputs changed during canonical capture; capture again")
        if capture.input_digest(project, plan) != original_inputs:
            raise CaptureError("The isolated source snapshot differs from the owning screenshot inputs")
        if (project / capture.DRAFT / capture.DRAFT_MANIFEST).is_file():
            copy_draft(project, root, plan)
        if result.returncode or report.get("ok") is not True:
            raise CaptureError(
                capture.safe_failure_message(CaptureError(str(report.get("error", "Canonical Linux capture failed"))))
            )
        if not args.verify and not args.draft:
            report = capture.publish_draft(root)
        report["preview"] = str(root / capture.DRAFT / "index.html")
        if "draft" in report:
            report["draft"] = str(root / capture.DRAFT)
        report["capture_platform"] = PLATFORM
        report["browser_image"] = IMAGE
        return report
