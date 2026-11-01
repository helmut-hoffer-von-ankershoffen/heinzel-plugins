"""A whole capture runs scene by scene in an isolated profile, leaves a reviewable private draft, and cleans up."""

import json
import os
import signal
import subprocess
import sys
import time
import types
from pathlib import Path

import pytest

from heinzel_plugin_tools import capture, planning, privacy

pytestmark = pytest.mark.unit

PNG = b"\x89PNG\r\n\x1a\n"
INTERPRETER = """#!/bin/sh
echo $$ > "$(dirname "$0")/backend.pid"
for argument in "$@"; do
  if [ "$argument" = "-c" ]; then
    printf '{"owner": "0.1.0", "core": "0.9.8", "compatible": true}'
    exit 0
  fi
  if [ "$argument" = "ui" ]; then
    echo "Serving on http://127.0.0.1:8123/#token=demo_session_token"
    exec sleep 120
  fi
done
"""
HZ = '#!/bin/sh\necho "Hello, Mira!"\n'


class FakeError(Exception):
    """Stands in for the browser automation library's error type."""


class FakeLocator:
    def __init__(self, page, label):
        self.page, self.label = page, label

    @property
    def first(self):
        return self

    def _act(self, action, *details):
        self.page.log.append((action, self.label, *details))
        if (action, self.label) in self.page.failures:
            raise FakeError(f"{action} {self.label} timed out")

    def click(self):
        self._act("click")

    def hover(self):
        self._act("hover")

    def fill(self, value):
        self._act("fill", value)

    def blur(self):
        self._act("blur")

    def focus(self):
        self._act("focus")

    def wait_for(self, **options):
        self._act("wait_for")

    def get_by_role(self, role, name=None, exact=False):
        return FakeLocator(self.page, f"{self.label}>{role}:{name}")

    def bounding_box(self):
        return self.page.boxes.get(self.label)

    def inner_text(self):
        return self.page.text

    def evaluate(self, script):
        return self.page.pre_height

    def evaluate_all(self, script):
        return ""


class FakePage:
    viewport_size = {"width": 1280, "height": 900}

    def __init__(self, browser):
        self.log, self.failures, self.boxes = browser.log, browser.failures, browser.boxes
        self.text, self.pre_height, self.png = browser.text, browser.pre_height, browser.png
        self.clock = types.SimpleNamespace(set_fixed_time=lambda value: self.log.append(("clock", str(value))))
        self.keyboard = types.SimpleNamespace(
            press=lambda key: self.log.append(("press", key)), type=lambda text: self.log.append(("type", text))
        )

    def set_default_timeout(self, value):
        self.log.append(("timeout", value))

    def set_content(self, document):
        self.log.append(("content", document))

    def set_viewport_size(self, size):
        self.log.append(("viewport", size))

    def route(self, pattern, handler):
        self.log.append(("route", pattern))

    def add_init_script(self, script):
        self.log.append(("init", script))

    def goto(self, url):
        self.log.append(("goto", url))

    def evaluate(self, script, argument=None):
        self.log.append(("evaluate", argument))

    def wait_for_function(self, script):
        self.log.append(("wait_for_function",))

    def locator(self, selector):
        return FakeLocator(self, selector)

    def get_by_role(self, role, name=None, exact=False):
        return FakeLocator(self, f"{role}:{name}")

    def get_by_text(self, text, exact=False):
        return FakeLocator(self, f"text:{text}")

    def get_by_label(self, label, exact=False):
        return FakeLocator(self, f"label:{label}")

    def screenshot(self, path, animations=None, clip=None):
        self.log.append(("screenshot", Path(path).name, clip))
        Path(path).write_bytes(self.png + Path(path).stem.encode())

    def close(self):
        self.log.append(("close",))


class FakeBrowser:
    def __init__(self, log, failures, settings):
        self.log, self.failures = log, failures
        self.boxes, self.text = settings["boxes"], settings["text"]
        self.pre_height, self.png = settings["pre_height"], settings["png"]

    def new_page(self, **options):
        self.log.append(("page", options["viewport"], options["reduced_motion"]))
        return FakePage(self)

    def close(self):
        self.log.append(("browser closed",))


@pytest.fixture
def harness(tmp_path, monkeypatch):
    """A fictional plugin, a fake installed interpreter and an in-memory browser; nothing leaves the temp folder."""
    owner = tmp_path / "heinzel-harbor"
    (owner / "src/heinzel_harbor").mkdir(parents=True)
    (owner / "src/heinzel_harbor/__init__.py").write_text('raise RuntimeError("never import during capture")\n')
    (owner / "pyproject.toml").write_text(
        '[project]\nname="heinzel-harbor"\nversion="0.1.0"\ndescription="A fictional harbor."\n'
        'dependencies=["heinzel>=0.9.8,<0.10"]\n[project.entry-points."heinzel.modules"]\ntides="heinzel_harbor"\n'
    )
    (owner / "README.md").write_text("# Harbor\n")
    bin_directory = tmp_path / "installed/bin"
    bin_directory.mkdir(parents=True)
    interpreter = bin_directory / "python"
    interpreter.write_text(INTERPRETER)
    (bin_directory / "hz").write_text(HZ)
    for path in (interpreter, bin_directory / "hz"):
        path.chmod(0o755)

    state = types.SimpleNamespace(
        owner=owner,
        interpreter=interpreter,
        log=[],
        failures=set(),
        launch_errors=[],
        settings={"boxes": {}, "text": "Harbor greeting: Hello, Mira!", "pre_height": 400, "png": PNG},
        installs=[],
        browsers=[],
        pid_file=bin_directory / "backend.pid",
    )

    def launch(headless):
        if state.launch_errors:
            raise state.launch_errors.pop(0)
        browser = FakeBrowser(state.log, state.failures, state.settings)
        state.browsers.append(browser)
        return browser

    class Context:
        chromium = types.SimpleNamespace(launch=lambda headless: launch(headless))

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.Error = FakeError
    sync_api.sync_playwright = lambda: Context()

    class Text:
        def __init__(self, plain):
            self.plain = plain

        @classmethod
        def from_ansi(cls, value):
            return cls(value)

    class Console:
        def __init__(self, **options):
            self.lines = []

        def print(self, text, **options):
            self.lines.append(text.plain)

        def export_html(self, **options):
            return "<html><style></style><body><pre>" + "".join(self.lines) + "</pre></body></html>"

    modules = {
        "playwright": types.ModuleType("playwright"),
        "playwright.sync_api": sync_api,
        "rich": types.ModuleType("rich"),
        "rich.console": types.SimpleNamespace(Console=Console),
        "rich.terminal_theme": types.SimpleNamespace(MONOKAI=object()),
        "rich.text": types.SimpleNamespace(Text=Text),
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    def define(root, *, refresh=False):
        return planning.record_definition(
            root,
            capture.read_plan(root),
            "# Fictional story\nA harbor greeting in the app and a terminal result; no external credentials.",
            reviewer="Synthetic source-analysis agent",
        )

    monkeypatch.setattr(planning, "ensure_definition", define)
    monkeypatch.setattr(privacy.shutil, "which", lambda name: None)  # never start a real reviewing agent
    real_run = subprocess.run

    def run(command, **options):
        if command[1:4] == ["-m", "playwright", "install"]:
            state.installs.append(command)
            return subprocess.CompletedProcess(command, 0)
        return real_run(command, **options)

    monkeypatch.setattr(capture.subprocess, "run", run)
    yield state
    if state.pid_file.exists():
        try:
            os.kill(int(state.pid_file.read_text()), signal.SIGKILL)
        except (ProcessLookupError, ValueError):
            pass


def record(state, **options):
    return capture.capture(state.owner, core=None, headed=False, prepared_python=state.interpreter, **options)


def backend_is_running(state):
    try:
        os.kill(int(state.pid_file.read_text()), 0)
    except ProcessLookupError:
        return False
    return True


def test_a_draft_capture_records_every_scene_into_a_reviewable_private_bundle(harness):
    report = record(harness, draft_only=True)
    folder = harness.owner / capture.DRAFT
    assert report["ok"] is True and report["review_required"] is True and report["fresh"] is False
    assert [shot["surface"] for shot in report["screenshots"]] == ["ui", "ui", "cli"]
    bundle = json.loads((folder / "review-input.json").read_text())
    privacy.validate_bundle(bundle, folder)
    assert bundle["plugin"] == "heinzel-harbor" and bundle["core_version"] == "0.9.8"
    assert (folder / "REVIEW.md").is_file() and (folder / "review.schema.json").is_file()
    assert (folder / "cli.txt").read_text() == "Hello, Mira!\n"
    assert (folder / "ui.txt").read_text() == "Harbor greeting: Hello, Mira!\n"
    assert all((folder / name).read_bytes().startswith(PNG) for name in bundle["images"])
    assert not (harness.owner / capture.OUTPUT).exists(), "A draft must not touch the public gallery"


def test_the_isolated_backend_is_always_reaped(harness):
    record(harness, draft_only=True)
    assert not backend_is_running(harness)


def test_ui_scenes_only_reach_the_local_app_and_use_the_demo_appearance(harness):
    record(harness, draft_only=True)
    goto = [entry[1] for entry in harness.log if entry[0] == "goto"]
    assert goto and all(
        url.startswith("http://127.0.0.1:8123/") and url.endswith("#token=demo_session_token") for url in goto
    )
    init = next(entry[1] for entry in harness.log if entry[0] == "init")
    assert '"hz.theme","light"' in init and "hz.onboarding" in init
    assert ("route", "**/*") in harness.log


def test_the_plugin_card_scene_searches_for_the_plugin_by_name(harness):
    record(harness, draft_only=True)
    assert ("fill", "searchbox:Search plugins", "heinzel-harbor") in harness.log
    assert ("wait_for", "text:A fictional harbor.") in harness.log


def test_the_terminal_scene_types_one_quoted_hz_command(harness):
    record(harness, draft_only=True)
    typed = [entry[1] for entry in harness.log if entry[0] == "type"]
    assert typed == ["hz tides --help; printf '\\033]0;Demo complete\\007'"]


def test_session_tokens_are_scrubbed_from_every_page_before_a_screenshot(harness):
    record(harness, draft_only=True)
    scrubs = [entry[1] for entry in harness.log if entry[0] == "evaluate" and entry[1]]
    assert scrubs and all("demo_session_token" in argument["tokens"] for argument in scrubs)
    names = [entry for entry in harness.log if entry[0] == "screenshot"]
    assert [entry[1] for entry in names] == ["ui.png", "terminal.png", "cli.png"]


def test_a_failed_scene_names_itself_saves_a_private_diagnostic_and_stops_the_backend(harness):
    harness.failures.add(("wait_for", "main:None"))
    with pytest.raises(privacy.CaptureError, match=r"Scene terminal failed during scene preparation \(FakeError\)"):
        record(harness, draft_only=True)
    assert (harness.owner / ".preview/screenshots/terminal-failure.png").read_bytes().startswith(PNG)
    assert not backend_is_running(harness)
    assert harness.log[-1] == ("browser closed",)
    assert not (harness.owner / capture.DRAFT / "review-input.json").exists()


def test_a_missing_browser_is_installed_once_and_launch_is_retried(harness):
    harness.launch_errors.append(FakeError("Executable doesn't exist at /somewhere"))
    report = record(harness, draft_only=True)
    assert report["ok"] is True
    assert len(harness.installs) == 1 and harness.installs[0][-2:] == ["install", "chromium"]


def test_an_unrelated_browser_launch_failure_is_not_papered_over_by_an_install(harness):
    harness.launch_errors.append(FakeError("Sandbox initialization failed"))
    with pytest.raises(FakeError):
        record(harness, draft_only=True)
    assert harness.installs == [] and not backend_is_running(harness)


def test_an_oversized_cli_rendering_is_refused(harness):
    harness.settings["pre_height"] = 5000
    with pytest.raises(privacy.CaptureError, match="output is too tall"):
        record(harness, draft_only=True)


def test_an_image_over_the_size_limit_is_refused(harness):
    harness.settings["png"] = PNG + b"0" * capture.MAX_IMAGE
    with pytest.raises(privacy.CaptureError, match="PNG exceeds 500 KiB"):
        record(harness, draft_only=True)


def test_page_text_with_a_private_path_stops_the_capture_before_any_image_is_written(harness):
    harness.settings["text"] = "Opened /Users/someone/secret-notes.txt"
    with pytest.raises(privacy.CaptureError, match="private paths or personal identity"):
        record(harness, draft_only=True)
    assert not (harness.owner / capture.DRAFT).exists()


def test_cli_output_with_a_credential_is_refused(harness):
    (harness.interpreter.parent / "hz").write_text('#!/bin/sh\necho "token ghp_abcdefghijklmnopqrstuvwxyz0123456789"\n')
    with pytest.raises(privacy.CaptureError, match="possible credential"):
        record(harness, draft_only=True)


def test_a_failing_cli_scene_points_the_author_at_the_editable_plan(harness):
    (harness.interpreter.parent / "hz").write_text("#!/bin/sh\nexit 3\n")
    with pytest.raises(privacy.CaptureError, match="CLI scene failed"):
        record(harness, draft_only=True)
    assert not backend_is_running(harness)


def test_a_rich_plan_exercises_every_step_kind_and_a_focused_clip(harness):
    plan = harness.owner / capture.PLAN
    plan.parent.mkdir()
    plan.write_text(
        """format = 1
browser_time = "2026-11-02T10:00:00+01:00"

[[scenes]]
name = "tides"
surface = "ui"
route = "/?view=tides"
caption = "Tide table with a focused card, fictional data"
theme = "tide"
focus = {role = "region", name = "Tides", padding = 20}
steps = [
  {action = "click", role = "button", name = "Refresh", within_role = "main"},
  {action = "hover", role = "button", name_regex = "Tide.*"},
  {action = "click", role = "button", name = "Dismiss", optional = true},
  {action = "fill", label = "Station", value = "Mira Quay"},
  {action = "press", key = "Enter"},
  {action = "wait", role = "heading", name = "Tides"},
  {action = "wait", text = "High tide", optional = true},
  {action = "wait-webgl"},
]

[[scenes]]
name = "dark"
surface = "ui"
appearance = "dark"
reduced_motion = "no-preference"
viewport = {width = 800, height = 600}
timeout_ms = 5000
browser_time = "2026-11-03T08:00:00+01:00"
caption = "Dark appearance, fictional data"

[[scenes]]
name = "cli"
surface = "cli"
command = ["tides", "list"]
caption = "hz tides list, fictional data"
"""
    )
    theme = harness.owner / "src/heinzel_harbor/themes"
    theme.mkdir()
    (theme / "tide.toml").write_text('name = "tide"\n')
    harness.failures.add(("wait_for", "button:Dismiss"))  # optional click target absent: skipped, not fatal
    harness.failures.add(("wait_for", "text:High tide"))  # optional wait target absent: skipped, not fatal
    harness.settings["boxes"]["region:Tides"] = {"x": 100, "y": 100, "width": 300, "height": 200}
    assert record(harness, draft_only=True)["ok"] is True
    actions = [entry for entry in harness.log if entry[0] in {"click", "hover", "fill", "press"}]
    assert ("fill", "label:Station", "Mira Quay") in actions
    assert ("press", "Enter") in [entry[:2] for entry in actions]
    assert ("click", "main:None>button:Refresh") in actions
    assert any(entry[:1] == ("hover",) and "button:re.compile" in entry[1] for entry in actions)
    assert ("page", {"width": 800, "height": 600}, "no-preference") in harness.log
    assert any(entry[0] == "clock" and "2026-11-03" in entry[1] for entry in harness.log)


def test_a_focused_scene_whose_target_is_not_visible_is_refused(harness):
    plan = harness.owner / capture.PLAN
    plan.parent.mkdir()
    plan.write_text(
        """format = 1

[[scenes]]
name = "one"
surface = "ui"
caption = "First, fictional data"
focus = {role = "region", name = "Missing"}

[[scenes]]
name = "two"
surface = "ui"
caption = "Second, fictional data"

[[scenes]]
name = "cli"
surface = "cli"
command = ["tides"]
caption = "hz tides, fictional data"
"""
    )
    with pytest.raises(privacy.CaptureError, match="focused view is not visible"):
        record(harness, draft_only=True)


def test_a_focused_clip_is_centered_and_kept_inside_the_viewport(harness):
    plan = harness.owner / capture.PLAN
    plan.parent.mkdir()
    plan.write_text(
        """format = 1

[[scenes]]
name = "one"
surface = "ui"
caption = "First, fictional data"
focus = {role = "region", name = "Tides", padding = 40}

[[scenes]]
name = "two"
surface = "ui"
caption = "Second, fictional data"

[[scenes]]
name = "cli"
surface = "cli"
command = ["tides"]
caption = "hz tides, fictional data"
"""
    )
    harness.settings["boxes"]["region:Tides"] = {"x": 1200, "y": 10, "width": 300, "height": 200}
    record(harness, draft_only=True)
    clip = next(entry[2] for entry in harness.log if entry[0] == "screenshot" and entry[1] == "one.png")
    assert clip == {"x": 1280 - 380, "y": 0, "width": 380, "height": 280}


def test_a_complete_capture_publishes_only_after_an_exact_bundle_approval(harness, tmp_path):
    report = capture.capture(
        harness.owner, core=None, headed=False, draft_only=True, prepared_python=harness.interpreter
    )
    assert report["review_required"]
    bundle = json.loads((harness.owner / capture.DRAFT / "review-input.json").read_text())
    receipt = tmp_path / "receipt.json"
    review = {
        "format": 1,
        "bundle_sha256": bundle["bundle_sha256"],
        "reviewer": "Synthetic privacy agent",
        "decision": "approve",
        "checked_images": sorted(bundle["images"]),
        "checks": dict.fromkeys(privacy.CHECKS, True),
        "findings": [],
    }
    receipt.write_text(json.dumps(review))
    published = capture.publish_draft(harness.owner, receipt)
    assert published["fresh"] is True and published["privacy_reviewed"] is True
    assert published["reviewed_by"] == "Synthetic privacy agent"
    assert capture.check_capture(harness.owner)["ok"] is True
    assert "<!-- screenshots:start -->" in (harness.owner / "README.md").read_text()
    catalog = capture.project_data(harness.owner)["tool"]["heinzel"]["catalog"]["screenshots"]
    assert [shot["path"] for shot in catalog] == [f"docs/assets/screenshots/{n}.png" for n in ("ui", "terminal", "cli")]


def test_a_receipt_for_different_bytes_publishes_nothing(harness, tmp_path):
    capture.capture(harness.owner, core=None, headed=False, draft_only=True, prepared_python=harness.interpreter)
    bundle = json.loads((harness.owner / capture.DRAFT / "review-input.json").read_text())
    receipt = tmp_path / "receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "format": 1,
                "bundle_sha256": "0" * 64,
                "reviewer": "Synthetic privacy agent",
                "decision": "approve",
                "checked_images": sorted(bundle["images"]),
                "checks": dict.fromkeys(privacy.CHECKS, True),
                "findings": [],
            }
        )
    )
    original = (harness.owner / "pyproject.toml").read_text()
    with pytest.raises(privacy.CaptureError, match="does not match these captures"):
        capture.publish_draft(harness.owner, receipt)
    assert (harness.owner / "pyproject.toml").read_text() == original
    assert not (harness.owner / capture.OUTPUT).exists()


def test_a_draft_goes_stale_when_the_plan_changes_after_capture(harness):
    capture.capture(harness.owner, core=None, headed=False, draft_only=True, prepared_python=harness.interpreter)
    plan = harness.owner / capture.PLAN
    plan.write_text(plan.read_text().replace("isolated demonstration profile", "changed caption", 1))
    with pytest.raises(privacy.CaptureError, match="definition is stale"):
        capture.publish_draft(harness.owner, None)
    assert not (harness.owner / capture.OUTPUT).exists()


def test_environment_setup_failure_is_reported_without_starting_a_browser(harness, monkeypatch):
    monkeypatch.setattr(capture.subprocess, "run", lambda command, **_: subprocess.CompletedProcess(command, 1))
    with pytest.raises(privacy.CaptureError, match="environment setup failed"):
        capture.capture(harness.owner, core="candidate.whl", headed=False, draft_only=True)
    assert harness.log == []


def test_the_owning_setup_is_prepared_with_the_selected_core_before_capture(harness, monkeypatch):
    seen = []

    def run(command, **options):
        seen.append(command)
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(capture.subprocess, "run", run)
    with pytest.raises(privacy.CaptureError):
        capture.capture(harness.owner, core="candidate.whl", headed=False, draft_only=True)
    assert seen[0][-4:] == ["setup", "heinzel-harbor", "--core", "candidate.whl"]


@pytest.mark.parametrize("name", ["--option-like", "-x", "has space", ""])
def test_a_plugin_name_that_could_be_an_option_is_never_passed_to_tools(harness, name):
    pyproject = harness.owner / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace('name="heinzel-harbor"', f'name="{name}"'))
    with pytest.raises(privacy.CaptureError, match="no option-like text"):
        record(harness, draft_only=True)


def test_a_built_frontend_is_prepared_before_the_interpreter_is_checked(harness, monkeypatch):
    web = harness.owner / "web"
    web.mkdir()
    (web / "package.json").write_text(json.dumps({"scripts": {"build": "vite build"}}))
    order = []
    real = capture.subprocess.run

    def run(command, **options):
        order.append(Path(command[0]).name if command[0] != "uv" else "uv " + command[-1])
        return subprocess.CompletedProcess(command, 0) if command[0] == "uv" else real(command, **options)

    monkeypatch.setattr(capture.subprocess, "run", run)
    record(harness, draft_only=True)
    assert order[0] == "uv build"


def test_a_prepared_interpreter_that_is_not_executable_is_refused(harness, tmp_path):
    plain = tmp_path / "notpython"
    plain.write_text("")
    with pytest.raises(privacy.CaptureError, match="existing Python executable"):
        capture.capture(harness.owner, core=None, headed=False, prepared_python=plain)


def test_the_command_line_prints_a_human_summary_and_opens_the_contact_sheet(harness, monkeypatch, capsys):
    opened = []
    monkeypatch.setattr(capture.webbrowser, "open", lambda url: opened.append(url))
    monkeypatch.setattr(
        sys,
        "argv",
        ["capture", "--project", str(harness.owner), "--python", str(harness.interpreter), "--draft", "--open"],
    )
    assert capture.main() == 0
    out = capsys.readouterr().out
    assert "3 private captures ready for independent review." in out
    assert "make screenshots-check NAME=heinzel-harbor" in out
    assert opened == [(harness.owner / capture.DRAFT / "index.html").as_uri()]


def test_the_command_line_emits_one_json_document_for_agents(harness, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["capture", "--project", str(harness.owner), "--python", str(harness.interpreter), "--draft", "--json"],
    )
    assert capture.main() == 0
    assert json.loads(capsys.readouterr().out)["plugin"] == "heinzel-harbor"


def test_a_failed_command_line_run_returns_safe_json_and_status_one(harness, monkeypatch, capsys):
    (harness.interpreter.parent / "hz").write_text("#!/bin/sh\nexit 3\n")
    monkeypatch.setattr(
        sys,
        "argv",
        ["capture", "--project", str(harness.owner), "--python", str(harness.interpreter), "--draft", "--json"],
    )
    assert capture.main() == 1
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["ok"] is False and "CLI scene failed" in report["error"]
    assert "Capture failed:" in captured.err


def test_the_command_line_publishes_a_supplied_receipt(harness, monkeypatch, capsys, tmp_path):
    seen = []
    monkeypatch.setattr(
        capture,
        "publish_draft",
        lambda root, receipt: (
            seen.append((root, receipt))
            or {"plugin": "heinzel-harbor", "screenshots": [], "preview": str(root / "index.html")}
        ),
    )
    monkeypatch.setattr(
        sys, "argv", ["capture", "--project", str(harness.owner), "--review-receipt", str(tmp_path / "r.json")]
    )
    assert capture.main() == 0
    assert seen == [(harness.owner.resolve(), tmp_path / "r.json")]
    assert "approved gallery, catalog metadata and README are ready" in capsys.readouterr().out


def test_a_backend_that_never_prints_its_address_is_reported_and_reaped(harness):
    harness.interpreter.write_text(
        '#!/bin/sh\necho $$ > "$(dirname "$0")/backend.pid"\n'
        'for a in "$@"; do\n'
        '  [ "$a" = "-c" ] && { printf \'{"owner": "0.1.0", "core": "0.9.8", "compatible": true}\'; exit 0; }\n'
        '  [ "$a" = "ui" ] && { echo "starting..."; exit 1; }\n'
        "done\n"
    )
    with pytest.raises(privacy.CaptureError, match="did not become ready"):
        record(harness, draft_only=True)
    time.sleep(0.05)
    assert not backend_is_running(harness)
