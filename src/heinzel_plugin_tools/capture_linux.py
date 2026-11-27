"""The same disposable Linux browser and source snapshot for authors and CI."""

import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from heinzel_plugin_tools.privacy import CaptureError, _confidentiality_module, regular_bytes, safe_path

IMAGE = (
    "mcr.microsoft.com/playwright/python:v1.64.1-noble@sha256:"
    "330d401ae23c905896a0c26c66c36fc971b621519e7b11b435a8328d7bf6e031"
)
PLATFORM = "linux/amd64"
BOOTSTRAP_WHEEL = "uv-0.13.7-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
BOOTSTRAP_SHA256 = "2c9bdc4a872b60a93c5f26c0791089ea11585a4f9d3b3c017d78eb8487505e25"
BOOTSTRAP_URL = (
    "https://files.pythonhosted.org/packages/b9/93/0e053a2ca4523ee9825ccbedeb7121470d0a188933f11688b6d90d7f5c08/"
    + BOOTSTRAP_WHEEL
)
BOOTSTRAP_LIMIT = 20 * 1024 * 1024


def bootstrap_wheel() -> bytes:
    """Cache only a hash-locked public wheel; the worker never sees or writes this host cache."""
    cache = Path.home() / ".cache/heinzel-plugin-tools/bootstrap"
    path = cache / BOOTSTRAP_WHEEL
    if path.exists() or path.is_symlink():
        data = regular_bytes(path, BOOTSTRAP_LIMIT)
    else:
        try:
            with urllib.request.urlopen(BOOTSTRAP_URL, timeout=60) as response:  # noqa: S310 - fixed public HTTPS URL
                data = response.read(BOOTSTRAP_LIMIT + 1)
        except (OSError, urllib.error.URLError) as error:
            raise CaptureError(
                "Cannot fetch the hash-locked public capture bootstrap wheel; retry when transport recovers"
            ) from error
    if len(data) > BOOTSTRAP_LIMIT or hashlib.sha256(data).hexdigest() != BOOTSTRAP_SHA256:
        raise CaptureError(
            "Public capture bootstrap wheel hash differs; remove the invalid cached wheel before retrying"
        )
    if not path.exists():
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=cache, delete=False) as handle:
            handle.write(data)
            temporary = Path(handle.name)
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return data


def configured_terms() -> str:
    """Require the real external scanner policy; never put its contents in command arguments or logs."""
    checker = _confidentiality_module()
    terms = checker.load_terms() if checker else []
    if not terms:
        raise CaptureError("Canonical capture requires configured confidential terms, including on an author's machine")
    return "\n".join(terms) + "\n"


def command(argv: list[str], *, cwd: Path, capture: bool = False, capture_stderr: bool = False, timeout: int = 900):
    try:
        return subprocess.run(
            argv,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture_stderr else None,
            timeout=timeout,
            check=False,
        )
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
    names = [f"{scene['name']}.{ext}" for scene in plan["scenes"] for ext in ("png", "txt", "scan.txt")]
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


def source_inventory(root: Path) -> bytes:
    """Use repository provenance, or an empty private index for standalone authors."""
    root = root.resolve()
    inventory = ["ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "."]
    try:
        # lexists also catches broken gitfiles/links: damaged repositories must
        # never become standalone sources merely because Git cannot read them.
        repository = any(
            os.path.lexists(parent / ".git")
            or (os.path.lexists(parent / "HEAD") and os.path.lexists(parent / "objects"))
            for parent in (root, *root.parents)
        )
        explicit_repository = any(
            key in os.environ for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE")
        )
        if repository or explicit_repository:
            listed = subprocess.run(["git", "-C", str(root), *inventory], capture_output=True, check=False, timeout=60)
        else:
            # Never initialize the author directory, load templates/hooks, or
            # consult user configuration for this scoped .gitignore inventory.
            environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
            environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
            with tempfile.TemporaryDirectory(prefix="hz-gallery-inventory-") as temporary:
                initialized = subprocess.run(
                    [
                        "git",
                        "-c",
                        f"core.hooksPath={os.devnull}",
                        "init",
                        "--bare",
                        "--quiet",
                        "--template=",
                        temporary,
                    ],
                    env=environment,
                    capture_output=True,
                    check=False,
                    timeout=60,
                )
                if initialized.returncode:
                    raise CaptureError("Cannot initialize the isolated authoring inventory")
                listed = subprocess.run(
                    ["git", f"--git-dir={temporary}", f"--work-tree={root}", *inventory],
                    env=environment,
                    capture_output=True,
                    check=False,
                    timeout=60,
                )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CaptureError("Canonical snapshot requires Git source provenance") from error
    if listed.returncode:
        raise CaptureError("Canonical snapshot requires Git source provenance")
    return listed.stdout


def snapshot_files(root: Path, plan: dict) -> list[str]:
    """Select the same validated authoring allowlist in repositories and standalone sources."""
    from heinzel_plugin_tools import capture

    names = sorted({name for name in source_inventory(root).decode().split("\0") if name})
    package_files = {
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "requirements.lock",
        "plugin-lock.json",
        "hatch_build.py",
        "Makefile",
    }
    required = {"pyproject.toml", capture.PLAN.as_posix()}
    if plan.get("bootstrap"):
        required.add(plan["bootstrap"])
    gallery_files = {capture.MANIFEST.as_posix(), (capture.OUTPUT / "index.html").as_posix()}
    gallery_files.update(
        (capture.OUTPUT / f"{scene['name']}.{extension}").as_posix()
        for scene in plan["scenes"]
        for extension in ("png", "txt")
    )
    selected = []
    for name in names:
        path = Path(name)
        if path.as_posix() != name or path.is_absolute() or ".." in path.parts:
            raise CaptureError("Canonical snapshot contains an invalid source path")
        if set(path.parts) & (capture.IGNORED | {".git", ".env", ".netrc", ".npmrc", ".pypirc"}):
            continue
        if any(part.startswith(".env.") for part in path.parts):
            continue
        if name in package_files | required | gallery_files or path.parts[0] in {
            "src",
            "web",
            "assets",
            "static",
            "templates",
            "resources",
            "vendor-provenance",
        }:
            source = safe_path(root, name)
            # A tracked deletion is not an input; dangling links are still refused above.
            if source.exists():
                regular_bytes(source, 20 * 1024 * 1024)
                selected.append(name)
    if not required.issubset(selected):
        raise CaptureError("Canonical snapshot is missing required source provenance")
    return selected


def copy_snapshot(root: Path, project: Path, names: list[str]) -> None:
    """Copy only selected regular files, never directory trees or linked components."""
    project.mkdir()
    for name in names:
        data = regular_bytes(safe_path(root, name), 20 * 1024 * 1024)
        destination = safe_path(project, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        destination.chmod(0o644 | (safe_path(root, name).stat().st_mode & 0o111))


def run(args) -> dict:
    """Capture a copy without host tools, applications, credentials, sockets or Python environments."""
    from heinzel_plugin_tools import capture

    if args.headed:
        raise CaptureError("Canonical Linux capture is headless; review its generated contact sheet")
    root = args.project.resolve()
    plan = capture.read_plan(root)
    render_check = getattr(args, "render_check", False)
    if not render_check:
        configured_terms()  # Only the trusted host applies private policy; rendering receives none.
    source_files = snapshot_files(root, plan)
    original_inputs = capture.input_digest(root, plan, source_files=source_files)
    if args.verify and not render_check:
        capture.check_capture(root)
    with tempfile.TemporaryDirectory(prefix="hz-gallery-linux-") as scratch:
        work = Path(scratch)
        project = work / "project"
        copy_snapshot(root, project, source_files)
        (work / "source-files.json").write_text(json.dumps(source_files))
        (work / BOOTSTRAP_WHEEL).write_bytes(bootstrap_wheel())
        for directory in ("home", "cache", "python", "bootstrap"):
            (work / directory).mkdir()
        runtime = work / "runtime"
        package = Path(__file__).resolve().parent
        shutil.copytree(package, runtime / "src/heinzel_plugin_tools", ignore=shutil.ignore_patterns("__pycache__"))
        (runtime / "scripts").mkdir()
        shutil.copyfile(Path(_confidentiality_module().__file__), runtime / "scripts/check_confidentiality.py")
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
            "--source-inventory",
            "/capture/source-files.json",
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
                    "--user",
                    f"{os.getuid()}:{os.getgid()}",
                    "--hostname",
                    "demo-host",
                    "--ipc=private",
                    "--shm-size=1g",
                    "--mount",
                    f"type=bind,source={work},target=/capture",
                    "--workdir",
                    "/capture/project",
                    "--env",
                    "LANG=C.UTF-8",
                    "--env",
                    "HOME=/capture/home",
                    "--env",
                    "UV_CACHE_DIR=/capture/cache",
                    "--env",
                    "UV_PYTHON_INSTALL_DIR=/capture/python",
                    "--env",
                    "LC_ALL=C.UTF-8",
                    "--env",
                    "TZ=UTC",
                    "--env",
                    "GITHUB_ACTIONS=true",
                    "--env",
                    "CONFIDENTIALITY_REQUIRED=false",
                    "--env",
                    "CONFIDENTIAL_TERMS_FILE=/dev/null",
                    "--entrypoint",
                    "python",
                    IMAGE,
                    "-c",
                    "import os,subprocess,sys; "
                    "os.environ['PATH']='/capture/bootstrap/bin:'+os.environ['PATH']; "
                    "subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', "
                    "'--no-index', '--no-deps', '--target', '/capture/bootstrap', "
                    f"'/capture/{BOOTSTRAP_WHEEL}'], check=True); "
                    "os.execvp(sys.argv[1], sys.argv[1:])",
                    *child,
                ],
                cwd=work,
                capture=True,
                capture_stderr=render_check,
            )
        finally:
            with contextlib.suppress(CaptureError):
                command(["docker", "rm", "--force", container], cwd=work, capture=True, timeout=30)
        try:
            report = json.loads(result.stdout)
        except (ValueError, TypeError) as error:
            raise CaptureError("Canonical Linux capture returned no result; no gallery was changed") from error
        if project.is_symlink() or not project.is_dir() or project.resolve() != work.resolve() / "project":
            raise CaptureError("The isolated snapshot directory was replaced; no gallery was changed")
        current_plan = capture.read_plan(root)
        if capture.input_digest(root, current_plan, source_files=snapshot_files(root, current_plan)) != original_inputs:
            raise CaptureError("Screenshot inputs changed during canonical capture; capture again")
        # Never execute host Git against worker-writable metadata.
        if capture.input_digest(project, plan, source_files=source_files) != original_inputs:
            raise CaptureError("The isolated source snapshot differs from the owning screenshot inputs")
        if render_check:
            if result.returncode or report.get("ok") is not True or report.get("verified") is not True:
                raise CaptureError("Zero-secret rendering comparison failed; no private-policy approval or publication")
            # No unscanned transcript, caption, image or stderr is published by the zero-secret CI mode.
            return {
                "ok": True,
                "render_verified": True,
                "private_scan": False,
                "fresh": False,
                "scope": "render-only",
                "scene_count": len(plan["scenes"]),
                "capture_platform": PLATFORM,
                "browser_image": IMAGE,
            }
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
        report["private_scan"] = True
        report["capture_platform"] = PLATFORM
        report["browser_image"] = IMAGE
        return report
