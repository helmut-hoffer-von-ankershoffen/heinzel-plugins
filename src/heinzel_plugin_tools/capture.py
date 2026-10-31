# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright==1.64.1", "rich==15.0.0", "tomlkit==0.15.2"]
# ///
"""Capture an owning plugin in an isolated demonstration profile; never run during catalog discovery."""

import argparse
import hashlib
import html
import io
import json
import os
import queue
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import unicodedata
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from heinzel_plugin_tools.privacy import (
    DRAFT,
    CaptureError,
    atomic_text,
    bundle_digest,
    canonical_text,
    prepare_review,
    run_agent,
    safe_path,
    validate_bundle,
    validate_review,
)

PLAN = Path("docs/screenshots.toml")
OUTPUT = Path("docs/assets/screenshots")
MANIFEST = OUTPUT / "capture.json"
MAX_IMAGE = 500 * 1024
MAX_SCENES = 8
IGNORED = {"node_modules", "__pycache__", ".venv", "dist", ".git", ".acceptance", ".preview"}


def project_data(root: Path) -> dict:
    """Read the owning metadata without importing its code."""
    return tomllib.loads(safe_path(root, "pyproject.toml").read_text())


def theme_names(root: Path) -> list[str]:
    """Find the owning source's inert theme declarations."""
    result = []
    for path in sorted((root / "src").glob("*/themes/*.toml")):
        if path.is_symlink():
            continue
        value = tomllib.loads(path.read_text()).get("name")
        if isinstance(value, str) and value:
            result.append(value)
    return result


def default_plan(root: Path) -> dict:
    """Give even a new CLI-only plugin a truthful installed UI and CLI gallery."""
    metadata = project_data(root)
    name = metadata["project"]["name"]
    module = next(iter(metadata["project"]["entry-points"]["heinzel.modules"]))
    themes = theme_names(root)
    scenes = [
        {
            "name": "ui",
            "surface": "ui",
            "route": "/?settings=plugins",
            "plugin_card": True,
            "caption": f"{name} installed in the app; isolated demonstration profile",
        },
        {
            "name": "cli",
            "surface": "cli",
            "command": ["system", "theme", "list"] if themes else [module, "--help"],
            "caption": "hz "
            + " ".join(["system", "theme", "list"] if themes else [module, "--help"])
            + " — isolated demonstration profile",
        },
    ]
    if not themes:
        scenes.insert(
            1,
            {
                "name": "terminal",
                "surface": "ui",
                "route": "/",
                "caption": f"{name} in the app terminal; isolated demonstration profile",
                "steps": [{"action": "terminal", "command": [module, "--help"]}],
            },
        )
    if themes:
        scenes[0].update(theme=themes[0], appearance="light", route="/", plugin_card=False)
        scenes.append(
            {**scenes[0], "name": "ui-dark", "appearance": "dark", "caption": f"{name} in the app, dark appearance"}
        )
    return {"format": 1, "scenes": scenes}


def toml_value(value: object) -> str:
    """Encode only the bounded data shapes used by editable screenshot plans."""
    if isinstance(value, dict):
        return "{" + ", ".join(f"{json.dumps(key)} = {toml_value(item)}" for key, item in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(item) for item in value) + "]"
    return json.dumps(value, ensure_ascii=False)


def write_default_plan(root: Path, *, preset: str | None = None) -> None:
    """Write a concise editable plan once; preserve the author's existing scene choices."""
    path = safe_path(root, PLAN)
    if path.exists():
        return
    lines = [
        "# Real UI and CLI captures. Run make screenshots; open the generated index.html to review.",
        "# UI steps use accessible roles/labels: click, fill, press, wait. Commands are hz arguments, never shell.",
        "format = 1",
        "",
    ]
    scenes = default_plan(root)["scenes"]
    if preset:
        module = next(iter(project_data(root)["project"]["entry-points"]["heinzel.modules"]))
        command = [module, "hello"] if preset == "minimal" else [module, "sample"]
        for scene in scenes:
            if scene["surface"] == "cli":
                scene.update(command=command, caption="hz " + " ".join(command) + " — fictional starter example")
            for step in scene.get("steps", []):
                if step["action"] == "terminal":
                    step["command"] = command
        scenes.sort(key=lambda scene: (scene.get("name") != "terminal", scene["surface"] == "cli"))
    for scene in scenes:
        lines.append("[[scenes]]")
        lines.extend(f"{key} = {toml_value(value)}" for key, value in scene.items())
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


def read_plan(root: Path) -> dict:
    """Validate bounded scenes and accessible user actions before running anything."""
    path = safe_path(root, PLAN)
    data = tomllib.loads(path.read_text()) if path.exists() else default_plan(root)
    return validate_plan(root, data)


def validate_plan(root: Path, data: dict) -> dict:
    """Accept only bounded, editable presentation actions, never executable browser source."""
    if not isinstance(data, dict) or set(data) - {"format", "bootstrap", "browser_time", "scenes"}:
        raise CaptureError("Screenshot plan contains unsupported fields")
    scenes = data.get("scenes")
    if (
        type(data.get("format")) is not int
        or data["format"] != 1
        or not isinstance(scenes, list)
        or not 3 <= len(scenes) <= MAX_SCENES
    ):
        raise CaptureError(
            "docs/screenshots.toml needs format = 1 and three to eight scenes, including at least two UI and one CLI"
        )
    validate_browser_time(data.get("browser_time"))
    names = set()
    for scene in scenes:
        if not isinstance(scene, dict):
            raise CaptureError("Each screenshot scene must be a TOML table")
        if set(scene) - {
            "name",
            "surface",
            "caption",
            "command",
            "route",
            "appearance",
            "theme",
            "steps",
            "focus",
            "plugin_card",
            "timeout_ms",
            "viewport",
            "reduced_motion",
            "browser_time",
        }:
            raise CaptureError("Screenshot scene contains unsupported fields")
        name = scene.get("name", "")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,59}", name) or name in names:
            raise CaptureError("Screenshot scene names must be unique lowercase words joined by dashes")
        names.add(name)
        validate_browser_time(scene.get("browser_time"))
        if scene.get("reduced_motion", "reduce") not in ("reduce", "no-preference"):
            raise CaptureError(f"Scene {name}: reduced_motion must be reduce or no-preference")
        focus = scene.get("focus")
        if focus is not None:
            if not isinstance(focus, dict):
                raise CaptureError(f"Scene {name}: focus must be a bounded accessible locator")
            validate_locator({key: value for key, value in focus.items() if key != "padding"}, name)
            if type(focus.get("padding", 40)) is not int or not 16 <= focus.get("padding", 40) <= 160:
                raise CaptureError(f"Scene {name}: focus padding must be between 16 and 160")
        if "theme" in scene and (
            not isinstance(scene["theme"], str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,79}", scene["theme"])
        ):
            raise CaptureError(f"Scene {name}: theme must be a bounded theme identifier")
        timeout = scene.get("timeout_ms", 15000)
        if type(timeout) is not int or not 1000 <= timeout <= 30000:
            raise CaptureError(f"Scene {name}: timeout_ms must be between 1000 and 30000")
        viewport = scene.get("viewport", {"width": 1280, "height": 900})
        if (
            not isinstance(viewport, dict)
            or set(viewport) != {"width", "height"}
            or not all(type(v) is int and 320 <= v <= 1920 for v in viewport.values())
        ):
            raise CaptureError(f"Scene {name}: viewport needs width and height between 320 and 1920")
        caption = scene.get("caption", "")
        if (
            not isinstance(caption, str)
            or not caption.strip()
            or len(caption) > 180
            or any(unicodedata.category(c) in {"Cc", "Cf"} and c not in "\n\t" for c in caption)
        ):
            raise CaptureError(f"Scene {name}: supply a short caption, at most 180 characters")
        if scene.get("surface") == "cli":
            command = scene.get("command")
            if not valid_command(command):
                raise CaptureError(f'Scene {name}: command is a list of hz arguments, for example ["clock"]')
        elif scene.get("surface") == "ui":
            route = scene.get("route", "/")
            if not isinstance(route, str):
                raise CaptureError(f"Scene {name}: route must be text")
            parsed = urlsplit(route)
            if not route.startswith("/") or route.startswith("//") or parsed.scheme or parsed.netloc or parsed.fragment:
                raise CaptureError(
                    f"Scene {name}: route must stay inside the local app, for example /?settings=plugins"
                )
            if scene.get("appearance", "light") not in ("light", "dark"):
                raise CaptureError(f"Scene {name}: appearance must be light or dark")
            steps = scene.get("steps", [])
            if not isinstance(steps, list) or len(steps) > 24:
                raise CaptureError(f"Scene {name}: use at most 24 accessible UI steps")
            for step in steps:
                if not isinstance(step, dict):
                    raise CaptureError(f"Scene {name}: each step must be a TOML table")
                if step.get("action") not in ("click", "hover", "fill", "press", "wait", "terminal", "wait-webgl"):
                    raise CaptureError(f"Scene {name}: steps support click, fill, press and wait")
                if set(step) - {
                    "action",
                    "role",
                    "name",
                    "name_regex",
                    "within_role",
                    "optional",
                    "label",
                    "value",
                    "key",
                    "text",
                    "command",
                }:
                    raise CaptureError(f"Scene {name}: action contains unsupported fields")
                if "optional" in step and type(step["optional"]) is not bool:
                    raise CaptureError(f"Scene {name}: optional must be a boolean")
                if "within_role" in step and (
                    not isinstance(step["within_role"], str) or not 1 <= len(step["within_role"]) <= 60
                ):
                    raise CaptureError(f"Scene {name}: within_role must name one accessible landmark")
                if step["action"] in {"click", "hover"}:
                    validate_locator({k: v for k, v in step.items() if k in {"role", "name", "name_regex"}}, name)
                required = {
                    "click": ("role", "name_regex") if "name_regex" in step else ("role", "name"),
                    "hover": ("role", "name_regex") if "name_regex" in step else ("role", "name"),
                    "wait-webgl": (),
                    "fill": ("label", "value"),
                    "press": ("key",),
                    "wait": ("role", "name") if "role" in step else ("text",),
                    "terminal": (),
                }[step["action"]]
                if step["action"] == "terminal" and (not valid_command(step.get("command"))):
                    raise CaptureError(f"Scene {name}: terminal needs an array of hz arguments")
                if not all(isinstance(step.get(key), str) for key in required):
                    raise CaptureError(f"Scene {name}: {step['action']} needs {', '.join(required)}")
        else:
            raise CaptureError(f"Scene {name}: surface must be ui or cli")
    bootstrap = data.get("bootstrap")
    if bootstrap is not None and (
        not isinstance(bootstrap, str)
        or not safe_path(root, bootstrap).is_file()
        or (root / bootstrap).is_symlink()
        or not (root / bootstrap).resolve().is_relative_to(root.resolve())
    ):
        raise CaptureError("bootstrap must name a regular fixture script inside this plugin")
    if sum(scene["surface"] == "ui" for scene in scenes) < 2 or not any(s["surface"] == "cli" for s in scenes):
        raise CaptureError("Every gallery needs at least two relevant UI scenes and a CLI scene")
    return data


def valid_command(command: object) -> bool:
    """Bound command arguments without interpreting shell syntax."""
    return (
        isinstance(command, list)
        and 0 < len(command) <= 40
        and all(
            isinstance(arg, str) and len(arg) <= 2000 and not any(unicodedata.category(c) in {"Cc", "Cf"} for c in arg)
            for arg in command
        )
    )


def validate_locator(locator: dict, scene: str) -> None:
    """Validate only accessible-role locators and bounded regular expressions."""
    if (
        not isinstance(locator, dict)
        or set(locator) not in ({"role", "name"}, {"role", "name_regex"})
        or not all(isinstance(value, str) and 0 < len(value) <= 180 for value in locator.values())
    ):
        raise CaptureError(f"Scene {scene}: focus/click needs a bounded accessible role and name")
    if "name_regex" in locator:
        try:
            re.compile(locator["name_regex"])
        except re.error:
            raise CaptureError(f"Scene {scene}: accessible name regular expression is invalid") from None


def validate_browser_time(value: object) -> None:
    """Accept an explicit timezone-aware demonstration date without freezing animation frames."""
    if value is None:
        return
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError
    except (TypeError, ValueError):
        raise CaptureError("browser_time must be an ISO8601 date with a timezone") from None


def input_digest(root: Path, plan: dict) -> str:
    """Identify visual inputs while excluding generated metadata, captures and environment caches."""
    metadata = project_data(root)
    tool = metadata.get("tool", {})
    owner = tool.get("heinzel", {})
    catalog = owner.get("catalog", {})
    catalog.pop("screenshots", None)
    if not catalog:
        owner.pop("catalog", None)
    if not owner:
        tool.pop("heinzel", None)
    if not tool:
        metadata.pop("tool", None)
    digest = hashlib.sha256(json.dumps([metadata, plan], sort_keys=True).encode())
    paths = [root / "requirements.lock", root / "plugin-lock.json"]
    readme = root / "README.md"
    if readme.exists():
        paths.append(readme)
    if plan.get("bootstrap"):
        paths.append(root / plan["bootstrap"])
    for folder in (
        root / "src",
        root / "web",
        root / "assets",
        root / "static",
        root / "templates",
        root / "resources",
    ):
        for current, directories, filenames in os.walk(folder, followlinks=False):
            if any((Path(current) / name).is_symlink() for name in directories if name not in IGNORED):
                raise CaptureError("Capture inputs must not contain linked directories")
            directories[:] = sorted(name for name in directories if name not in IGNORED)
            paths.extend(Path(current) / name for name in sorted(filenames) if not name.endswith(".pyc"))
    for path in sorted(paths):
        if not path.is_file():
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise CaptureError("Capture inputs must be regular files inside the owning plugin")
        content = path.read_bytes()
        if path == root / "README.md":
            content = (
                re.sub(r"<!-- screenshots:start -->.*?<!-- screenshots:end -->", "", content.decode(), flags=re.S)
                .strip()
                .encode()
            )
        if path == root / "README.md" and not content:
            continue
        digest.update(path.relative_to(root).as_posix().encode() + b"\0" + content)
    return digest.hexdigest()


def check_capture(root: Path) -> dict:
    """Check freshness and complete gallery assets offline, without installing or running a plugin."""
    manifest_path = safe_path(root, MANIFEST)
    if not manifest_path.is_file():
        raise CaptureError(
            "No capture manifest yet. Run make screenshots (or hz-plugin screenshots <name>), then review it"
        )
    plan = read_plan(root)
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("format") != 1 or manifest.get("inputs_sha256") != input_digest(root, plan):
        raise CaptureError(
            "Screenshots are stale. Run make screenshots, review the preview, and commit the updated gallery"
        )
    expected = [
        {"path": (OUTPUT / f"{scene['name']}.png").as_posix(), "surface": scene["surface"], "caption": scene["caption"]}
        for scene in plan["scenes"]
    ]
    actual = project_data(root).get("tool", {}).get("heinzel", {}).get("catalog", {}).get("screenshots")
    if actual != expected:
        raise CaptureError("Catalog screenshots differ from the capture plan. Run make screenshots to update them")
    for shot in expected:
        path = root / shot["path"]
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise CaptureError("Gallery images must stay inside their owning plugin")
        content = path.read_bytes()
        if not content.startswith(b"\x89PNG\r\n\x1a\n") or len(content) > MAX_IMAGE:
            raise CaptureError(f"{shot['path']}: expected a PNG smaller than 500 KiB; re-run make screenshots")
        if hashlib.sha256(content).hexdigest() != manifest.get("images", {}).get(shot["path"]):
            raise CaptureError(
                f"{shot['path']}: capture changed; re-run make screenshots instead of editing generated images"
            )
    from heinzel_plugin_tools.planning import validate_definition

    definition = validate_definition(root, plan)
    bundle = manifest.get("review_bundle", {})
    validate_bundle(bundle, safe_path(root, OUTPUT))
    if bundle.get("definition") != definition:
        raise CaptureError("Gallery source-analysis definition differs from the reviewed captures")
    if (
        bundle.get("plugin") != project_data(root)["project"]["name"]
        or manifest.get("plugin") != bundle["plugin"]
        or manifest.get("core_version") != bundle["core_version"]
        or bundle.get("inputs_sha256") != manifest["inputs_sha256"]
        or bundle.get("screenshots") != expected
        or bundle.get("images") != {Path(shot["path"]).name: manifest["images"][shot["path"]] for shot in expected}
    ):
        raise CaptureError("Gallery has no current exact-bundle privacy review. Run make screenshots")
    validate_review(bundle, manifest.get("privacy_review", {}))
    readme = safe_path(root, "README.md")
    if not readme.is_file():
        raise CaptureError("The generated README gallery is missing. Republish the approved capture draft")
    readme_text = readme.read_text()
    if readme_text != readme_gallery(readme_text, expected):
        raise CaptureError("The generated README gallery differs from the reviewed captions and image order")
    contact_sheet = safe_path(root, OUTPUT / "index.html")
    if not contact_sheet.is_file() or contact_sheet.read_text() != preview_document(
        bundle["plugin"], plan["scenes"], bundle["core_version"]
    ):
        raise CaptureError("The published contact sheet differs from its reviewed captions and SDK provenance")
    return {
        "ok": True,
        "plugin": project_data(root)["project"]["name"],
        "screenshots": expected,
        "preview": str(root / OUTPUT / "index.html"),
        "manifest": str(root / MANIFEST),
        "plan": str(root / PLAN),
        "fresh": True,
        "privacy_reviewed": True,
        "reviewed_by": manifest["privacy_review"]["reviewer"],
    }


def demo_environment(home: Path, interpreter: Path) -> dict[str, str]:
    """Use fictional identity, empty credentials and fresh application/vendor state."""
    env = {key: value for key, value in os.environ.items() if key in {"LANG", "LC_ALL", "TMPDIR", "SYSTEMROOT"}}
    env.update(
        HOME=str(home),
        XDG_CONFIG_HOME=str(home / "config"),
        XDG_CACHE_HOME=str(home / "cache"),
        XDG_DATA_HOME=str(home / "data"),
        XDG_STATE_HOME=str(home / "state"),
        GIT_CONFIG_GLOBAL="/dev/null",
        GIT_CONFIG_NOSYSTEM="1",
        BASH_ENV="/dev/null",
        ENV="/dev/null",
        GH_CONFIG_DIR=str(home / "gh"),
        PATH=str(interpreter.parent) + os.pathsep + "/usr/bin:/bin",
        HZ_PLUGINS_ENABLED="true",
        HZ_UPDATE_CHECK="false",
        HZ_SYSTEM_CREDENTIAL__BACKEND="environment",
        HZ_SYSTEM_DAEMON__UNIT_DIR=str(home / "daemon-units"),
        HZ_HEINZEL__USER_DIR=str(home / "workflows"),
        HZ_ORG__HANDLE="mira",
        HZ_ORG__NAME="Mira Example",
        HZ_ORG__EMAIL="mira@example.com",
        HZ_ORG__ROLE="engineering-manager",
        HZ_ORG__TIMEZONE="Europe/Berlin",
        USER="mira",
        LOGNAME="mira",
        SHELL="/bin/sh",
        PS1="$ ",
        TERM="xterm-256color",
        FORCE_COLOR="1",
        COLUMNS="110",
    )
    for key in ("CONFIG_HOME", "DATA_DIR", "CACHE_DIR", "STATE_DIR", "LOG_DIR"):
        env["HZ_" + key] = str(home / key.lower())
    return env


def hz(interpreter: Path, args: list[str], env: dict, cwd: Path) -> str:
    """Run the reviewed scene's hz argument list without a shell."""
    args = args[1:] if args[:1] == ["hz"] else args
    command = (
        [str(interpreter), "-I", env["HZ_PLUGIN_CAPTURE_BOOTSTRAP"], *args]
        if env.get("HZ_PLUGIN_CAPTURE_BOOTSTRAP")
        else [str(interpreter.parent / "hz"), *args]
    )
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise CaptureError("A screenshot CLI scene failed. Inspect its command in the editable scene plan")
    if len(result.stdout) > 256 * 1024:
        raise CaptureError("CLI capture is too long; choose a narrower command in docs/screenshots.toml")
    return result.stdout


def backend(interpreter: Path, env: dict, home: Path) -> tuple[subprocess.Popen, str]:
    """Start the owning installed app and keep its authentication token only in memory."""
    prefix = (
        [str(interpreter), "-I", "-u", env["HZ_PLUGIN_CAPTURE_BOOTSTRAP"]]
        if env.get("HZ_PLUGIN_CAPTURE_BOOTSTRAP")
        else [str(interpreter), "-I", "-u", "-m", "heinzel"]
    )
    process = subprocess.Popen(
        [*prefix, "ui", "--no-browser", "--port", "0"],
        cwd=home,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    lines = queue.Queue()

    def read() -> None:
        for line in process.stdout:
            lines.put(line)
        lines.put(None)

    threading.Thread(target=read, daemon=True).start()
    try:
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            try:
                line = lines.get(timeout=1)
            except queue.Empty:
                if process.poll() is not None:
                    break
                continue
            if line is None:
                break
            found = re.search(r"https?://127\.0\.0\.1:\d+/[^\s]*#token=[A-Za-z0-9_-]+", line)
            if found:
                return process, found.group()
        raise CaptureError("The app did not become ready. Run make preview to inspect it, then retry make screenshots")
    except BaseException:
        stop_backend(process)
        raise


def stop_backend(process: subprocess.Popen) -> None:
    """Reap only the isolated capture server, including on failed scenes or interruption."""
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)
    if process.stdout:
        process.stdout.close()


def local_requests(origin: str):
    """Keep browser capture requests on the isolated app's origin."""

    def handle(route):
        if route.request.url.startswith(origin + "/"):
            route.continue_()
        else:
            route.abort()

    return handle


def preview_document(name: str, scenes: list[dict], core: str) -> str:
    """A local, script-free contact sheet for a person's or agent's visual review."""
    figures = "".join(
        f'<figure><a href="{scene["name"]}.png"><img src="{scene["name"]}.png" '
        f'alt="{html.escape(scene["caption"], quote=True)}"></a><figcaption>'
        f"{html.escape(scene['surface'].upper())} · {html.escape(scene['caption'])}</figcaption></figure>"
        for scene in scenes
    )
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        f"<title>{html.escape(name)} screenshots</title><style>body{{font:16px/1.6 system-ui;margin:2rem;"
        "background:#faf8f3;color:#263b32}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));"
        "gap:1rem}figure{margin:0;padding:1rem;background:white;border:1px solid #d8ddd3;border-radius:12px}"
        "img{width:100%;height:auto}figcaption{margin-top:.75rem}a:focus-visible{outline:3px solid #a64028}</style>"
        f"<h1>{html.escape(name)}</h1><p>Isolated demonstration profile · Core {html.escape(core)} · "
        "Review these captures before committing. Click an image to inspect it at full size.</p>"
        f"<main>{figures}</main></html>\n"
    )


def scan_text(value: str) -> None:
    """Stop recognizable credentials and host identity before any publication step."""
    patterns = [
        r"(?:[?#&](?:access_)?token=)[A-Za-z0-9_-]+",
        r"Bearer\s+[A-Za-z0-9._-]{12,}",
        r"gh[pousr]_[A-Za-z0-9]{16,}",
        r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    ]
    if any(re.search(pattern, value, re.I) for pattern in patterns):
        raise CaptureError("Capture text contains a possible credential; use fictional fixtures before reviewing again")
    if re.search(
        r"(?:/Users/|/home/|/private/var/folders/|/var/folders/|/private/tmp/|/tmp/|[A-Za-z]:\\Users\\)[^\s/\\]+", value
    ) or any(
        not email.lower().endswith(("@example.com", ".example", "@example.org", "@example.test"))
        for email in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", value)
    ):
        raise CaptureError("Capture text contains private paths or personal identity; use fictional demonstration data")
    private = [str(Path.home()), socket.gethostname()]
    if any(part not in {"localhost", "demo-workstation"} and len(part) > 3 and part in value for part in private):
        raise CaptureError("Capture text contains host-specific information; replace it with a fictional fixture")


def redact_auth_presentation(page, tokens: tuple[str, ...] = (), private_paths: tuple[str, ...] = ()) -> None:
    """Hide session/authentication presentation before successful or diagnostic image saves."""
    page.evaluate(
        r"""({tokens, privatePaths}) => {
          const scrub = value => {
            let text = String(value);
            text = text.replace(/(?:https?:\/\/|[/?#])[^\s<>"']*[?#&](?:access_?token|token|code|auth)=[^\s<>"']*/gi,
                                '[authentication link hidden]');
            for (const token of tokens) if (token) text = text.split(token).join('[session hidden]');
            for (const path of privatePaths) if (path) text = text.split(path).join('/demo-profile');
            text = text.replace(/Bearer\s+[A-Za-z0-9._-]{12,}/gi, '[credential hidden]');
            text = text.replace(/gh[pousr]_[A-Za-z0-9]{16,}|sk-(?:proj-)?[A-Za-z0-9_-]{20,}/g, '[credential hidden]');
            return text;
          };
          const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          let node;
          while ((node = walker.nextNode())) {
            if (['SCRIPT','STYLE'].includes(node.parentElement?.tagName)) continue;
            const value = scrub(node.textContent);
            if (node.textContent !== value) node.textContent = value;
          }
          for (const element of document.querySelectorAll('*')) {
            for (const attribute of [...element.attributes]) {
              const value = scrub(attribute.value);
              if (value !== attribute.value) element.setAttribute(attribute.name, value);
            }
            if (element.matches('input,textarea')) {
              const value = scrub(element.value);
              if (value !== element.value) element.value = value;
            }
          }
          if (location.hash) history.replaceState(null, '', location.pathname + location.search);
        }""",
        {"tokens": list(tokens), "privatePaths": sorted(set(private_paths), key=len, reverse=True)},
    )


def safe_screenshot(
    page, path: Path, *, tokens: tuple[str, ...] = (), private_paths: tuple[str, ...] = (), clip: dict | None = None
) -> str:
    """Redact authentication presentation and reject unsafe text before writing any PNG."""
    redact_auth_presentation(page, tokens, private_paths)
    body = page.locator("body").inner_text()
    forms = page.locator("input,textarea").evaluate_all("els => els.map(el => el.value).join('\\n')")
    scan_text(body + "\n" + forms)
    page.screenshot(path=str(path), animations="disabled", clip=clip)
    return body


def safe_failure_message(error: Exception) -> str:
    """Keep arbitrary provider/browser exception text out of human and machine output."""
    if isinstance(error, tomllib.TOMLDecodeError):
        return "The editable screenshot plan has invalid TOML. Check docs/screenshots.toml syntax"
    if isinstance(error, CaptureError):
        message = str(error)
        try:
            scan_text(message)
        except ValueError:
            return "Capture failed because private authentication or machine data was detected; use fictional fixtures"
        if len(message) < 600 and not re.search(r"(?:https?://|/Users/|/home/)", message):
            return message
    return "Capture could not complete. Check the scene plan and isolated dependencies, then retry"


def readme_gallery(text: str, shots: list[dict]) -> str:
    """Maintain only the generated screenshot block, preserving the author's surrounding prose."""
    start, end = "<!-- screenshots:start -->", "<!-- screenshots:end -->"
    if (
        (start in text) != (end in text)
        or text.count(start) > 1
        or text.count(end) > 1
        or (start in text and text.index(start) >= text.index(end))
    ):
        raise CaptureError("README screenshot markers must occur once as a complete start/end pair")

    def image(shot: dict) -> str:
        return (
            f'<img src="{html.escape(shot["path"], quote=True)}" '
            f'alt="{html.escape(shot["caption"], quote=True)}" width="960">\n\n'
            f"{html.escape(shot['caption'])}"
        )

    ui = "\n\n".join(image(shot) for shot in shots if shot["surface"] == "ui")
    cli = "\n\n".join(image(shot) for shot in shots if shot["surface"] == "cli")
    block = (
        f"{start}\n## Screenshots\n\n{ui}\n\n<details>\n<summary>Command line</summary>\n\n"
        f"{cli}\n\n</details>\n\n[Open the screenshot gallery](docs/assets/screenshots/index.html).\n{end}"
    )
    if start in text:
        return re.sub(re.escape(start) + ".*?" + re.escape(end), lambda _: block, text, flags=re.S)
    return text.rstrip() + "\n\n" + block + "\n"


def publish_draft(root: Path, receipt: Path | None = None) -> dict:
    """Publish only a complete fresh bundle approved by an independent privacy and quality agent."""
    import tomlkit

    from heinzel_plugin_tools.planning import validate_definition

    folder = safe_path(root, DRAFT)
    plan = read_plan(root)
    definition = validate_definition(root, plan)
    bundle = json.loads(safe_path(folder, "review-input.json").read_text())
    validate_bundle(bundle, folder)
    if bundle.get("inputs_sha256") != input_digest(root, plan) or bundle.get("definition") != definition:
        raise CaptureError("Draft source inputs changed. Capture again before asking the agent to review")
    expected = [
        {"path": (OUTPUT / f"{scene['name']}.png").as_posix(), "surface": scene["surface"], "caption": scene["caption"]}
        for scene in plan["scenes"]
    ]
    if bundle.get("screenshots") != expected:
        raise CaptureError("Draft captions differ from the current scene plan. Capture again")
    for filename in bundle["transcripts"]:
        scan_text(safe_path(folder, filename).read_text())
    review = run_agent(root, bundle, receipt)
    # An independent agent may take minutes; recheck bytes and sources at the publication boundary.
    validate_bundle(bundle, folder)
    if input_digest(root, plan) != bundle["inputs_sha256"] or validate_definition(root, plan) != definition:
        raise CaptureError("Source inputs changed during review. Capture and review again")
    metadata_path = safe_path(root, "pyproject.toml")
    original_metadata = metadata_path.read_text()
    readme_path = safe_path(root, "README.md")
    original_readme = readme_path.read_text() if readme_path.exists() else None
    updated_readme = readme_gallery(original_readme or "", expected)
    document = tomlkit.parse(original_metadata)
    document.setdefault("tool", {}).setdefault("heinzel", {}).setdefault("catalog", {})["screenshots"] = expected
    target = safe_path(root, OUTPUT)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        for artifact in target.rglob("*"):
            safe_path(root, artifact.relative_to(root))
    manifest = {
        "format": 1,
        "plugin": bundle["plugin"],
        "core_version": bundle["core_version"],
        "inputs_sha256": bundle["inputs_sha256"],
        "images": {shot["path"]: bundle["images"][Path(shot["path"]).name] for shot in expected},
        "review_bundle": bundle,
        "privacy_review": review,
    }
    with tempfile.TemporaryDirectory(prefix=".gallery-stage-", dir=target.parent) as temporary:
        staging = Path(temporary) / "screenshots"
        staging.mkdir()
        for filename in [*bundle["images"], *bundle["transcripts"]]:
            shutil.copyfile(safe_path(folder, filename), staging / filename)
        # Regenerate the contact sheet from reviewed captions, never copy unreviewed supplier HTML.
        (staging / "index.html").write_text(preview_document(bundle["plugin"], plan["scenes"], bundle["core_version"]))
        (staging / "capture.json").write_text(json.dumps(manifest, indent=2) + "\n")
        backup = Path(temporary) / "previous"
        moved = False
        installed = False
        try:
            safe_path(root, OUTPUT)
            if target.exists():
                target.rename(backup)
                moved = True
            staging.rename(target)
            installed = True
            atomic_text(metadata_path, tomlkit.dumps(document))
            atomic_text(readme_path, updated_readme)
            return check_capture(root)
        except BaseException:
            if installed and target.exists():
                shutil.rmtree(target)
            if moved:
                backup.rename(target)
            atomic_text(metadata_path, original_metadata)
            if original_readme is None:
                readme_path.unlink(missing_ok=True)
            else:
                atomic_text(readme_path, original_readme)
            raise


def terminal_scene(page, command: list[str]) -> None:
    """Show real useful command results in the app terminal using safe argument quoting."""
    page.get_by_role("button", name="Open a terminal", exact=True).click()
    page.get_by_role("button", name="Full screen", exact=True).click()
    control = page.locator(".xterm-helper-textarea").first
    control.wait_for(state="attached")
    # PTY attachment precedes shell initialization; typing sooner races the initial prompt and corrupts the echo.
    page.wait_for_function(r"""() => [...document.querySelectorAll('.xterm-rows')].some(rows =>
        /\$\s*$/.test(rows.textContent.replace(/\u00a0/g, ' ').trimEnd()))""")
    control.focus()
    page.keyboard.type(shlex.join(["hz", *command]) + "; printf '\\033]0;Demo complete\\007'")
    page.keyboard.press("Enter")
    page.get_by_role("tab", name="Demo complete", exact=True).wait_for()


def prepared_version(interpreter: Path, metadata: dict) -> str:
    """Validate the explicit installed owner and current source's SDK requirements before execution."""
    if not interpreter.is_file() or not os.access(interpreter, os.X_OK):
        raise CaptureError("The prepared interpreter must be an existing Python executable")
    script = (
        "import json,sys; from importlib.metadata import version; "
        "from packaging.requirements import Requirement; from packaging.version import Version; "
        "core=version('heinzel'); requirements=[Requirement(r) for r in json.loads(sys.argv[2])]; "
        "compatible=all(Version(core) in r.specifier for r in requirements "
        "if r.name.lower().replace('_','-')=='heinzel' and (not r.marker or r.marker.evaluate())); "
        "print(json.dumps({'owner':version(sys.argv[1]),'core':core,'compatible':compatible}))"
    )
    installed = subprocess.run(
        [
            str(interpreter),
            "-I",
            "-c",
            script,
            metadata["project"]["name"],
            json.dumps(metadata["project"].get("dependencies", [])),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if installed.returncode:
        raise CaptureError("The prepared interpreter needs the owning plugin and a compatible Heinzel SDK installed")
    versions = json.loads(installed.stdout)
    if versions["owner"] != metadata["project"]["version"]:
        raise CaptureError("The prepared interpreter's owning plugin version differs from this source")
    if versions.get("compatible") is not True:
        raise CaptureError("The prepared SDK does not satisfy this plugin's declared compatibility requirement")
    return versions["core"]


def capture(
    root: Path, *, core: str | None, headed: bool, draft_only: bool = False, prepared_python: Path | None = None
) -> dict:
    """Prepare the owning artifact, record every scene, and publish a complete gallery only after success."""
    from playwright.sync_api import Error, sync_playwright
    from rich.console import Console
    from rich.terminal_theme import MONOKAI
    from rich.text import Text

    from heinzel_plugin_tools.planning import ensure_definition

    root = root.resolve()
    definition = ensure_definition(root)
    plan = read_plan(root)
    metadata = project_data(root)
    name = metadata["project"]["name"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
        raise CaptureError("The plugin name must start with a letter or digit and contain no option-like text")
    if not (root / PLAN).exists():
        write_default_plan(root)
    print(f"Preparing {name}; your normal app and credentials stay separate.", file=sys.stderr, flush=True)
    prepare = ["uv", "run", "--quiet", "--script", str(Path(__file__).with_name("cli.py")), "setup", name]
    if core:
        prepare += ["--core", core]
    if prepared_python is None:
        prepared = subprocess.run(prepare, cwd=root, capture_output=True, timeout=600)
        if prepared.returncode:
            raise CaptureError("Owning capture environment setup failed. Run the owning setup command, then retry")
    frontend = root / "web/package.json"
    if frontend.is_file() and "build" in json.loads(frontend.read_text()).get("scripts", {}):
        subprocess.run(
            ["uv", "run", "--no-project", "--script", str(root / "web/build.py"), "run", "build"],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=600,
        )
    interpreter = prepared_python.absolute() if prepared_python else root / ".venv/bin/python"
    version = prepared_version(interpreter, metadata)
    with tempfile.TemporaryDirectory(prefix="hz-screenshots-") as temporary:
        work = Path(temporary)
        env = demo_environment(work, interpreter)
        if plan.get("bootstrap"):
            env["HZ_PLUGIN_CAPTURE_BOOTSTRAP"] = str(root / plan["bootstrap"])
        terminal_bin = work / "bin"
        terminal_bin.mkdir()
        prefix = (
            [str(interpreter), "-I", env["HZ_PLUGIN_CAPTURE_BOOTSTRAP"]]
            if env.get("HZ_PLUGIN_CAPTURE_BOOTSTRAP")
            else [str(interpreter.parent / "hz")]
        )
        (terminal_bin / "hz").write_text("#!/bin/sh\nexec " + shlex.join(prefix) + ' "$@"\n')
        (terminal_bin / "hz").chmod(0o755)
        env["PATH"] = str(terminal_bin) + os.pathsep + env["PATH"]
        (work / ".profile").write_text(
            "PATH=" + shlex.quote(str(terminal_bin) + ":/usr/bin:/bin") + "; PS1='$ '; export PATH PS1\n"
        )
        themes = theme_names(root)
        if themes:
            hz(interpreter, ["system", "theme", "use", themes[0]], env, work)
        process, address = backend(interpreter, env, work)
        try:
            with sync_playwright() as playwright:
                try:
                    browser = playwright.chromium.launch(headless=not headed)
                except Error as error:
                    if "Executable doesn't exist" not in str(error):
                        raise
                    print("Installing the capture browser once…", file=sys.stderr, flush=True)
                    subprocess.run(
                        [sys.executable, "-m", "playwright", "install", "chromium"],
                        stdout=sys.stderr,
                        stderr=sys.stderr,
                        check=True,
                        timeout=600,
                    )
                    browser = playwright.chromium.launch(headless=not headed)
                try:
                    for scene in plan["scenes"]:
                        print(f"Capturing {scene['surface'].upper()} · {scene['name']}…", file=sys.stderr, flush=True)
                        page = browser.new_page(
                            viewport=scene.get("viewport", {"width": 1280, "height": 900}),
                            locale="en-US",
                            timezone_id="Europe/Berlin",
                            reduced_motion=scene.get("reduced_motion", "reduce"),
                        )
                        page.set_default_timeout(scene.get("timeout_ms", 15000))
                        if fixed_time := scene.get("browser_time", plan.get("browser_time")):
                            page.clock.set_fixed_time(datetime.fromisoformat(fixed_time))
                        phase = "scene preparation"
                        try:
                            if scene["surface"] == "cli":
                                output = hz(interpreter, scene["command"], env, work)
                                scan_text(output)
                                (work / f"{scene['name']}.txt").write_text(canonical_text(Text.from_ansi(output).plain))
                                console = Console(record=True, width=110, force_terminal=True, file=io.StringIO())
                                console.print(Text.from_ansi(output), end="", soft_wrap=True)
                                document = console.export_html(inline_styles=True, theme=MONOKAI)
                                document = document.replace(
                                    "</style>",
                                    "body{padding:24px;font:16px/1.5 monospace;}"
                                    "pre{white-space:pre;}p{font:14px system-ui;}</style>",
                                )
                                command = "hz " + " ".join(scene["command"])
                                document = document.replace("<body>", f"<body><p>{html.escape(command)}</p>")
                                page.set_content(document)
                                height = int(page.locator("pre").evaluate("el => el.getBoundingClientRect().bottom"))
                                if height > 2400:
                                    raise CaptureError(
                                        f"Scene {scene['name']}: output is too tall; choose a narrower hz command"
                                    )
                                page.set_viewport_size({"width": 1280, "height": max(280, height + 40)})
                            else:
                                base = address.split("#", 1)[0].rstrip("/")
                                page.route("**/*", local_requests(base))
                                appearance = scene.get("appearance", "light")
                                page.add_init_script(
                                    'localStorage.setItem("hz.onboarding",JSON.stringify('
                                    '{step:"you",visited:[],closed:true}));'
                                    f'localStorage.setItem("hz.theme",{json.dumps(appearance)});'
                                )
                                if scene.get("theme"):
                                    hz(interpreter, ["system", "theme", "use", scene["theme"]], env, work)
                                page.goto(base + scene.get("route", "/") + "#" + address.split("#", 1)[1])
                                page.locator("#splash").wait_for(state="hidden")
                                if scene.get("plugin_card"):
                                    field = page.get_by_role("searchbox", name="Search plugins")
                                    field.fill(name)
                                    page.get_by_text(
                                        metadata["project"].get("description", name), exact=True
                                    ).wait_for()
                                    field.blur()
                                else:
                                    page.get_by_role("main").wait_for()
                                for step in scene.get("steps", []):
                                    phase = "action " + step["action"]
                                    match step["action"]:
                                        case "terminal":
                                            terminal_scene(page, step["command"])
                                        case "click" | "hover":
                                            accessible_name = (
                                                re.compile(step["name_regex"]) if "name_regex" in step else step["name"]
                                            )
                                            scope = (
                                                page.get_by_role(step["within_role"])
                                                if step.get("within_role")
                                                else page
                                            )
                                            target = scope.get_by_role(step["role"], name=accessible_name, exact=True)
                                            if step.get("optional"):
                                                try:
                                                    target.wait_for(state="visible", timeout=1000)
                                                except Error:
                                                    continue
                                            if step["action"] == "hover":
                                                target.hover()
                                            else:
                                                target.click()
                                        case "fill":
                                            page.get_by_label(step["label"], exact=True).fill(step["value"])
                                        case "press":
                                            page.keyboard.press(step["key"])
                                        case "wait":
                                            target = (
                                                page.get_by_role(step["role"], name=step["name"], exact=True)
                                                if "role" in step
                                                else page.get_by_text(step["text"], exact=True).first
                                            )
                                            try:
                                                target.wait_for(timeout=1000 if step.get("optional") else None)
                                            except Error:
                                                if not step.get("optional"):
                                                    raise
                                        case "wait-webgl":
                                            page.wait_for_function("""() => [...document.querySelectorAll('canvas')]
                                            .some(c => {
                                                if (!c.width || !c.height) return false;
                                                const copy = document.createElement('canvas');
                                                copy.width = c.width; copy.height = c.height;
                                                const context = copy.getContext('2d');
                                                context.drawImage(c, 0, 0);
                                                const pixels = context.getImageData(0, 0, c.width, c.height).data;
                                                return pixels.some((value, index) => index % 4 === 3 && value > 0);
                                            })""")
                                page.evaluate(
                                    "async()=>{await document.fonts.ready;"
                                    "await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));}"
                                )

                            scan_text(scene["caption"])
                            phase = "capture framing"
                            clip = None
                            if scene.get("focus"):
                                focus = scene["focus"]
                                label = re.compile(focus["name_regex"]) if "name_regex" in focus else focus["name"]
                                box = page.get_by_role(focus["role"], name=label, exact=True).bounding_box()
                                if box is None:
                                    raise CaptureError(f"Scene {scene['name']}: focused view is not visible")
                                viewport = page.viewport_size
                                padding = focus.get("padding", 40)
                                width = min(viewport["width"], box["width"] + 2 * padding)
                                height = min(viewport["height"], box["height"] + 2 * padding)
                                clip = {
                                    "x": max(
                                        0, min(viewport["width"] - width, box["x"] + box["width"] / 2 - width / 2)
                                    ),
                                    "y": max(
                                        0, min(viewport["height"] - height, box["y"] + box["height"] / 2 - height / 2)
                                    ),
                                    "width": width,
                                    "height": height,
                                }
                            body = safe_screenshot(
                                page,
                                work / f"{scene['name']}.png",
                                tokens=(address.split("#token=", 1)[-1],),
                                private_paths=(str(work), str(work.resolve())),
                                clip=clip,
                            )
                            if scene["surface"] == "ui":
                                (work / f"{scene['name']}.txt").write_text(canonical_text(body))
                            if (work / f"{scene['name']}.png").stat().st_size > MAX_IMAGE:
                                raise CaptureError(f"Scene {scene['name']}: PNG exceeds 500 KiB; simplify its view")
                        except Error as error:
                            failure = safe_path(root, Path(".preview/screenshots") / f"{scene['name']}-failure.png")
                            failure.parent.mkdir(parents=True, exist_ok=True)
                            try:
                                safe_screenshot(
                                    page,
                                    failure,
                                    tokens=(address.split("#token=", 1)[-1],),
                                    private_paths=(str(work), str(work.resolve())),
                                )
                            except Exception:
                                failure.unlink(missing_ok=True)
                            raise CaptureError(
                                f"Scene {scene['name']} failed during {phase} ({type(error).__name__}). "
                                "Inspect private diagnostics and role/label steps"
                            ) from None
                        finally:
                            page.close()
                finally:
                    browser.close()
        finally:
            stop_backend(process)
        shots = [
            {
                "path": (OUTPUT / f"{scene['name']}.png").as_posix(),
                "surface": scene["surface"],
                "caption": scene["caption"],
            }
            for scene in plan["scenes"]
        ]
        folder = safe_path(root, DRAFT)
        folder.mkdir(parents=True, exist_ok=True)
        for artifact in folder.iterdir():
            safe_path(folder, artifact.name)
        for artifact in folder.glob("*"):
            if artifact.is_file():
                artifact.unlink()
        for scene in plan["scenes"]:
            for extension in ("png", "txt"):
                shutil.copyfile(work / f"{scene['name']}.{extension}", folder / f"{scene['name']}.{extension}")
        (folder / "index.html").write_text(preview_document(name, plan["scenes"], version))
        bundle = {
            "format": 1,
            "definition": definition,
            "plugin": name,
            "core_version": version,
            "inputs_sha256": input_digest(root, plan),
            "screenshots": shots,
            "images": {
                f"{scene['name']}.png": hashlib.sha256((folder / f"{scene['name']}.png").read_bytes()).hexdigest()
                for scene in plan["scenes"]
            },
            "transcripts": {
                f"{scene['name']}.txt": hashlib.sha256((folder / f"{scene['name']}.txt").read_bytes()).hexdigest()
                for scene in plan["scenes"]
            },
        }
        bundle["bundle_sha256"] = bundle_digest(bundle)
        prepare_review(folder, bundle)
    if draft_only:
        return {
            "ok": True,
            "plugin": name,
            "screenshots": shots,
            "fresh": False,
            "review_required": True,
            "preview": str(folder / "index.html"),
            "draft": str(folder),
            "plan": str(root / PLAN),
            "next": "Review REVIEW.md with an independent agent, then use --review-receipt <file>",
        }
    return publish_draft(root)


def main() -> int:
    """Offer a readable human workflow and a stable JSON result for agents."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--core")
    parser.add_argument("--python", type=Path, dest="prepared_python")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--draft", action="store_true")
    parser.add_argument("--review-receipt", type=Path)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    try:
        report = (
            publish_draft(args.project.resolve(), args.review_receipt)
            if args.review_receipt
            else capture(
                args.project.resolve(),
                core=args.core,
                headed=args.headed,
                draft_only=args.draft,
                prepared_python=args.prepared_python,
            )
        )
        if args.json:
            print(json.dumps(report))
        else:
            outcome = (
                "private captures ready for independent review"
                if report.get("review_required")
                else "approved gallery, catalog metadata and README are ready"
            )
            print(f"✓ {report['plugin']}: {len(report['screenshots'])} {outcome}.")
            print(
                f"Review: {report['preview']}\nRepeat: make screenshots NAME={report['plugin']}\n"
                f"Verify: make screenshots-check NAME={report['plugin']}"
            )
        if args.open:
            webbrowser.open(Path(report["preview"]).as_uri())
        return 0
    except Exception as error:  # The subprocess boundary must preserve the JSON result even if a browser adapter fails.
        message = safe_failure_message(error)
        if args.json:
            print(json.dumps({"ok": False, "error": message, "next": "Review docs/screenshots.toml and retry"}))
        print(f"Capture failed: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
