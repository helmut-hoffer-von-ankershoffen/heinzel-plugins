"""A whole capture runs scene by scene in an isolated profile, deterministically and without any agent."""

import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import tomllib
import types
from pathlib import Path

import pytest

from heinzel_plugin_tools import capture, privacy

pytestmark = [pytest.mark.unit, pytest.mark.usefixtures("fictional_capture_terms")]

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
exec "$(dirname "$0")/hz" "$@"
"""
HZ = '#!/bin/sh\necho "Hello, Mira!"\n'
AGENTS = {"codex", "claude"}


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

    def dispatch_event(self, event):
        self._act("dispatch_event", event)

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

    def get_by_role(self, role, name=None, exact=False, include_hidden=False):
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
    url = "about:blank"

    def __init__(self, browser):
        self.log, self.failures, self.boxes = browser.log, browser.failures, browser.boxes
        self.text, self.pre_height, self.png = browser.text, browser.pre_height, browser.png
        self.page_title = browser.title
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
        self.url = url.split("#", 1)[0]

    def evaluate(self, script, argument=None):
        self.log.append(("evaluate", argument))
        return None

    def title(self):
        return self.page_title

    def wait_for_function(self, script):
        self.log.append(("wait_for_function",))

    def locator(self, selector):
        return FakeLocator(self, selector)

    def get_by_role(self, role, name=None, exact=False, include_hidden=False):
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
        self.title = settings.get("title", "Heinzel")

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
        commands=[],
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
    sync_api.TimeoutError = FakeError
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

    real_run = subprocess.run

    def run(command, **options):
        state.commands.append(command)
        assert Path(str(command[0])).name not in AGENTS, "the screenshot path must never start an agent"
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


def as_definition(text):
    """Write a scene plan in TOML for readability; the definition file is its JSON."""
    return json.dumps(tomllib.loads(text))


def record(state, **options):
    return capture.capture(state.owner, core=None, headed=False, prepared_python=state.interpreter, **options)


def backend_is_running(state):
    try:
        os.kill(int(state.pid_file.read_text()), 0)
    except ProcessLookupError:
        return False
    return True


def test_a_draft_capture_records_every_scene_privately(harness):
    report = record(harness, draft_only=True)
    folder = harness.owner / capture.DRAFT
    assert report["ok"] is True
    assert report["fresh"] is False
    assert report["draft"] == str(folder)
    assert [shot["surface"] for shot in report["screenshots"]] == ["ui", "ui", "cli"]
    draft = json.loads((folder / capture.DRAFT_MANIFEST).read_text())
    assert draft["plugin"] == "heinzel-harbor"
    assert draft["core_version"] == "0.9.8"
    assert not (folder / "REVIEW.md").exists()
    assert not (folder / "review.schema.json").exists()
    assert (folder / "cli.txt").read_text() == "Hello, Mira!\n"
    assert (folder / "ui.txt").read_text() == "Harbor greeting: Hello, Mira!\n"
    assert all((folder / name).read_bytes().startswith(PNG) for name in draft["images"])
    assert not (harness.owner / capture.OUTPUT).exists(), "A draft must not touch the public gallery"


def test_a_whole_capture_starts_no_agent_process(harness, monkeypatch):
    popened = []
    real_popen = capture.subprocess.Popen

    def popen(command, *args, **kwargs):
        popened.append(command)
        assert Path(str(command[0])).name not in AGENTS
        return real_popen(command, *args, **kwargs)

    monkeypatch.setattr(capture.subprocess, "Popen", popen)
    monkeypatch.setattr(capture.shutil, "which", lambda name: pytest.fail(f"looked up {name}"))
    assert record(harness)["fresh"] is True
    started = [Path(str(command[0])).name for command in harness.commands + popened]
    assert started
    assert not AGENTS & set(started)


def test_the_isolated_backend_is_always_reaped(harness):
    record(harness, draft_only=True)
    assert not backend_is_running(harness)


def test_ui_scenes_only_reach_the_local_app_and_use_the_demo_appearance(harness):
    record(harness, draft_only=True)
    goto = [entry[1] for entry in harness.log if entry[0] == "goto"]
    assert goto
    assert all(url.startswith("http://127.0.0.1:8123/") and url.endswith("#token=demo_session_token") for url in goto)
    init = next(entry[1] for entry in harness.log if entry[0] == "init")
    assert '"hz.theme","light"' in init
    assert "hz.onboarding" in init
    assert ("route", "**/*") in harness.log


def test_the_terminal_scene_types_one_quoted_hz_command(harness):
    record(harness, draft_only=True)
    typed = [entry[1] for entry in harness.log if entry[0] == "type"]
    assert typed == ["hz tides --help; printf '\\033]0;Demo complete\\007'"]


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
    assert len(harness.installs) == 1
    assert harness.installs[0][-2:] == ["install", "chromium"]


def test_an_unrelated_browser_launch_failure_is_not_papered_over_by_an_install(harness):
    harness.launch_errors.append(FakeError("Sandbox initialization failed"))
    with pytest.raises(FakeError):
        record(harness, draft_only=True)
    assert harness.installs == []
    assert not backend_is_running(harness)


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
        as_definition("""format = 1
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
""")
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
    assert ("dispatch_event", "complementary:Chat>button:Close the chat", "click") in harness.log


def test_capture_leaves_existing_chat_open(harness):
    first_heinzel = "complementary:Chat>heading:Meet your first Heinzelmännchen"
    harness.failures.add(("wait_for", first_heinzel))
    assert record(harness, draft_only=True)["ok"]
    assert ("dispatch_event", "complementary:Chat>button:Close the chat", "click") not in harness.log


def test_a_focused_scene_whose_target_is_not_visible_is_refused(harness):
    plan = harness.owner / capture.PLAN
    plan.parent.mkdir()
    plan.write_text(
        as_definition("""format = 1

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
""")
    )
    with pytest.raises(privacy.CaptureError, match="focused view is not visible"):
        record(harness, draft_only=True)


def test_a_focused_clip_is_centered_and_kept_inside_the_viewport(harness):
    plan = harness.owner / capture.PLAN
    plan.parent.mkdir()
    plan.write_text(
        as_definition("""format = 1

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
""")
    )
    harness.settings["boxes"]["region:Tides"] = {"x": 1200, "y": 10, "width": 300, "height": 200}
    record(harness, draft_only=True)
    clip = next(entry[2] for entry in harness.log if entry[0] == "screenshot" and entry[1] == "one.png")
    assert clip == {"x": 1280 - 380, "y": 0, "width": 380, "height": 280}


def test_a_complete_capture_publishes_deterministically_and_checks_fresh(harness):
    published = record(harness)
    assert published["fresh"] is True
    assert capture.check_capture(harness.owner)["ok"] is True
    assert (harness.owner / capture.PLAN).is_file(), "the default definition is written with the first gallery"
    assert "<!-- screenshots:start -->" in (harness.owner / "README.md").read_text()
    catalog = capture.project_data(harness.owner)["tool"]["heinzel"]["catalog"]["screenshots"]
    assert [shot["path"] for shot in catalog] == [f"docs/assets/screenshots/{n}.png" for n in ("ui", "terminal", "cli")]
    manifest = json.loads((harness.owner / capture.MANIFEST).read_text())
    assert manifest["format"] == 2
    assert "privacy_review" not in manifest


def test_a_page_title_or_url_with_private_data_stops_the_capture(harness):
    harness.settings["text"] = "Harbor greeting"
    harness.settings["title"] = "Inbox of someone@realmail.de"
    with pytest.raises(privacy.CaptureError, match="personal identity"):
        record(harness)
    assert not (harness.owner / capture.OUTPUT).exists()


def test_a_draft_goes_stale_when_the_definition_changes_after_capture(harness):
    record(harness, draft_only=True)
    plan = capture.read_plan(harness.owner)
    plan["scenes"][0]["caption"] = "A changed caption for the fictional harbor"
    (harness.owner / capture.PLAN).parent.mkdir(parents=True, exist_ok=True)
    (harness.owner / capture.PLAN).write_text(json.dumps(plan))
    with pytest.raises(privacy.StaleGallery, match="UI inputs changed"):
        capture.publish_draft(harness.owner)
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
    assert seen[0][:5] == ["uv", "run", "--quiet", "--no-project", "--no-cache"]
    assert seen[0][5] == "--script"


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
    assert "3 private draft captures ready." in out
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
    assert report["ok"] is False
    assert "CLI scene failed" in report["error"]
    assert "Capture failed:" in captured.err


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
    deadline = time.monotonic() + 5
    while backend_is_running(harness) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not backend_is_running(harness)


def test_capture_uses_physical_owned_temp_paths_even_when_the_os_returns_an_alias(harness, tmp_path, monkeypatch):
    physical = tmp_path / "physical-temp"
    physical.mkdir(mode=0o700)
    alias = tmp_path / "temporary-alias"
    alias.symlink_to(physical, target_is_directory=True)
    original_temporary = capture.tempfile.TemporaryDirectory
    original_environment = capture.demo_environment
    observed = []

    class AliasedTemporary:
        def __init__(self, **options):
            self.owned = original_temporary(prefix=options["prefix"], dir=physical)

        def __enter__(self):
            return str(alias / Path(self.owned.__enter__()).name)

        def __exit__(self, *args):
            return self.owned.__exit__(*args)

    def environment(home, interpreter):
        assert home == home.resolve(strict=True)
        assert home.parent == physical.resolve()
        env = original_environment(home, interpreter)
        for key in ("HOME", "HZ_CONFIG_HOME", "HZ_DATA_DIR", "HZ_CACHE_DIR", "HZ_STATE_DIR", "HZ_LOG_DIR"):
            path = Path(env[key])
            assert path.is_relative_to(home)
            assert path == path.resolve()
        observed.append(home)
        return env

    monkeypatch.setattr(capture.tempfile, "TemporaryDirectory", AliasedTemporary)
    monkeypatch.setattr(capture, "demo_environment", environment)
    assert record(harness, draft_only=True)["ok"] is True
    assert len(observed) == 1
    assert not observed[0].exists()
    assert alias.is_symlink()
    assert physical.is_dir()


def test_environment_does_not_canonicalize_a_foreign_supplied_path(tmp_path):
    physical = tmp_path / "foreign"
    physical.mkdir()
    alias = tmp_path / "foreign-alias"
    alias.symlink_to(physical, target_is_directory=True)
    env = capture.demo_environment(alias, tmp_path / "bin/python")
    assert env["HOME"] == str(alias)
    assert env["HZ_STATE_DIR"] == str(alias / "state_dir")
    assert alias.is_symlink()


def test_normal_capture_imports_leave_owned_vendor_source_inventory_unchanged(harness, tmp_path, monkeypatch):
    vendor = harness.owner / "src/fictional_vendor"
    vendor.mkdir()
    (vendor / "__init__.py").write_text("VALUE = 'Fictional harbor'\n")
    before = {path.relative_to(vendor): path.read_bytes() for path in vendor.rglob("*") if path.is_file()}
    audit = tmp_path / "capture-child-audit.jsonl"
    bootstrap = harness.owner / "docs/fixture.py"
    bootstrap.parent.mkdir(exist_ok=True)
    bootstrap.write_text(
        "import json,sys,time\nfrom pathlib import Path\n"
        f"sys.path.insert(0, {str(vendor.parent)!r})\n"
        "import fictional_vendor\n"
        f"audit = Path({str(audit)!r})\n"
        "with audit.open('a') as stream:\n"
        " stream.write(json.dumps({'args':sys.argv[1:], 'isolated':sys.flags.isolated, "
        "'no_bytecode':sys.dont_write_bytecode}) + '\\n')\n"
        "if 'ui' in sys.argv:\n"
        " print('Serving on http://127.0.0.1:8123/#token=demo_session_token', flush=True)\n"
        " time.sleep(120)\n"
        "else:\n print(fictional_vendor.VALUE)\n"
    )
    plan = harness.owner / capture.PLAN
    capture.write_default_plan(harness.owner)
    plan.write_text(json.dumps(json.loads(plan.read_text()) | {"bootstrap": "docs/fixture.py"}))
    harness.interpreter = Path(sys.executable)
    monkeypatch.setattr(capture, "prepared_version", lambda *_args: "0.9.16")
    original_environment = capture.demo_environment
    environment = {}

    def demo(home, interpreter):
        environment.update(original_environment(home, interpreter))
        return environment

    monkeypatch.setattr(capture, "demo_environment", demo)
    original_page = FakePage.__init__

    def page(self, browser):
        original_page(self, browser)

        def terminal(command):
            assert command == "hz tides --help; printf '\\033]0;Demo complete\\007'"
            executable = Path(environment["PATH"].split(os.pathsep)[0]) / "hz"
            subprocess.run(  # noqa: S603 - only the test-owned capture wrapper and fixed fictional command
                [str(executable), "tides", "--help"], env=environment, check=True, capture_output=True, timeout=10
            )

        self.keyboard.type = terminal

    monkeypatch.setattr(FakePage, "__init__", page)
    assert record(harness, draft_only=True)["ok"] is True
    children = [json.loads(line) for line in audit.read_text().splitlines()]
    assert len(children) == 3  # backend, native terminal command, CLI scene
    assert all(child["isolated"] == 1 and child["no_bytecode"] for child in children)
    assert {tuple(child["args"]) for child in children} == {("ui", "--no-browser", "--port", "0"), ("tides", "--help")}
    assert {path.relative_to(vendor): path.read_bytes() for path in vendor.rglob("*") if path.is_file()} == before
    assert not list(vendor.rglob("__pycache__"))


def test_installed_cli_capture_uses_owning_isolated_python_without_writing_bytecode(tmp_path):
    vendor = tmp_path / "owned_vendor"
    vendor.mkdir()
    (vendor / "__init__.py").write_text("VALUE = 'Fictional result'\n")
    binary = tmp_path / "bin"
    binary.mkdir()
    interpreter = binary / "python"
    interpreter.symlink_to(sys.executable)
    (binary / "hz").write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(tmp_path)!r})\n"
        "import owned_vendor\n"
        "assert sys.flags.isolated and sys.dont_write_bytecode\n"
        "assert sys.argv[1:] == ['fictional', '--json']\n"
        "print(owned_vendor.VALUE)\n"
    )
    before = sorted(path.relative_to(vendor) for path in vendor.rglob("*"))
    env = capture.demo_environment(tmp_path / "demo", interpreter)
    assert capture.hz(interpreter, ["fictional", "--json"], env, tmp_path) == "Fictional result\n"
    assert sorted(path.relative_to(vendor) for path in vendor.rglob("*")) == before


def test_external_prepared_python_keeps_existing_scans_without_owning_prefix_authority(harness, monkeypatch):
    def forbidden(*_args):
        pytest.fail("An external prepared environment must not gain owning-prefix redaction authority")

    monkeypatch.setattr(capture, "owning_prefix", forbidden)
    harness.settings["text"] = str(harness.interpreter.parent.parent)
    with pytest.raises(privacy.CaptureError, match="private paths"):
        record(harness, draft_only=True)


def test_normal_setup_routes_its_derived_identity_to_every_presentation_save(harness, monkeypatch):
    from heinzel_plugin_tools._presentation import OwningPrefix

    owned_bin = harness.owner / ".venv/bin"
    owned_bin.mkdir(parents=True)
    for name in ("python", "hz"):
        target = owned_bin / name
        target.write_bytes((harness.interpreter.parent / name).read_bytes())
        target.chmod(0o755)
    identity = OwningPrefix(str(harness.owner / ".venv"), ())  # synthetic wiring fixture, not a verification receipt
    observed = []
    original_run = capture.subprocess.run
    original_save = capture.safe_screenshot

    def run(command, **options):
        if command[:2] == ["uv", "build"]:
            (Path(command[command.index("-o") + 1]) / "heinzel_harbor-0.1.0-py3-none-any.whl").write_bytes(b"")
        if command[0] == "uv":  # setup, the capture wheel and the restored editable install
            return subprocess.CompletedProcess(command, 0)
        return original_run(command, **options)

    def attest(root, interpreter):
        assert root == harness.owner.resolve()
        assert interpreter == owned_bin / "python"
        return identity

    def save(*args, **options):
        observed.append(options["owning_interpreter_prefix"])
        return original_save(*args, **options)

    monkeypatch.setattr(capture.subprocess, "run", run)
    monkeypatch.setattr(capture, "owning_prefix", attest)
    monkeypatch.setattr(capture, "safe_screenshot", save)
    assert capture.capture(harness.owner, core=None, headed=False, draft_only=True)["ok"]
    assert observed
    assert all(value is identity for value in observed)


def _artifact_run(seen, *, build=0, wheel=True, install=0, restore=0):
    def run(command, **options):
        seen.append(command[:3])
        if command[1] == "build":
            if wheel:
                (Path(command[command.index("-o") + 1]) / "heinzel_harbor-0.1.0-py3-none-any.whl").write_bytes(b"")
            return subprocess.CompletedProcess(command, build)
        return subprocess.CompletedProcess(command, install if "--reinstall" in command else restore)

    return run


def test_capture_installs_the_built_wheel_and_restores_the_editable_install(harness, monkeypatch):
    seen = []
    monkeypatch.setattr(capture.subprocess, "run", _artifact_run(seen))
    with (
        pytest.raises(RuntimeError, match="scene failed"),
        capture.installed_artifact(harness.owner, harness.interpreter, owning=True),
    ):
        assert seen == [["uv", "build", "--wheel"], ["uv", "pip", "install"]]
        raise RuntimeError("scene failed")
    assert len(seen) == 3
    assert seen[2] == ["uv", "pip", "install"]


@pytest.mark.parametrize(
    ("options", "message"), [({"build": 1}, "built"), ({"wheel": False}, "built"), ({"install": 1}, "installed")]
)
def test_a_wheel_that_cannot_be_built_or_installed_stops_capture(harness, monkeypatch, options, message):
    seen = []
    monkeypatch.setattr(capture.subprocess, "run", _artifact_run(seen, **options))
    with (
        pytest.raises(privacy.CaptureError, match=message),
        capture.installed_artifact(harness.owner, harness.interpreter, owning=True),
    ):
        pytest.fail("capture must not start")


def test_an_external_prepared_interpreter_is_used_as_it_is(harness, monkeypatch):
    monkeypatch.setattr(capture.subprocess, "run", lambda *a, **k: pytest.fail("no install"))
    with capture.installed_artifact(harness.owner, harness.interpreter, owning=False):
        pass


def test_a_failed_restore_after_a_good_capture_fails_loudly(harness, monkeypatch):
    seen = []
    monkeypatch.setattr(capture.subprocess, "run", _artifact_run(seen, restore=1))
    with (
        pytest.raises(privacy.CaptureError, match="editable install was not restored"),
        capture.installed_artifact(harness.owner, harness.interpreter, owning=True),
    ):
        pass


def test_a_failed_restore_never_hides_the_capture_failure(harness, monkeypatch, capsys):
    monkeypatch.setattr(capture.subprocess, "run", _artifact_run([], restore=1))
    with (
        pytest.raises(RuntimeError, match="scene failed"),
        capture.installed_artifact(harness.owner, harness.interpreter, owning=True),
    ):
        raise RuntimeError("scene failed")
    assert "not restored" in capsys.readouterr().err


def test_verify_recaptures_and_passes_when_every_scene_renders_the_same_text(harness):
    record(harness)
    report = capture.verify(harness.owner, core=None, headed=False, prepared_python=harness.interpreter)
    assert report["ok"]
    assert report["transcripts_differ"] == []
    assert report["images_differ"] == []


def test_verify_fails_naming_the_command_when_displayed_text_changed_outside_the_ui_inputs(harness):
    """The reviewer's probe: a label from plugin Python changes; the digest stays, the re-capture catches it."""
    record(harness)
    (harness.interpreter.parent / "hz").write_text('#!/bin/sh\necho "Ahoy, Mira!"\n')
    assert capture.check_capture(harness.owner)["fresh"], "the narrow local digest does not see this change"
    with pytest.raises(privacy.StaleGallery, match=r"differs from the committed gallery \(cli.txt\)") as stale:
        capture.verify(harness.owner, core=None, headed=False, prepared_python=harness.interpreter)
    assert stale.value.command == "make screenshots NAME=heinzel-harbor"


def test_verify_lists_image_differences_and_gates_them_only_when_strict(harness):
    record(harness)
    harness.settings["png"] = PNG + b"other-font-rendering"
    report = capture.verify(harness.owner, core=None, headed=False, prepared_python=harness.interpreter)
    assert report["ok"]
    assert len(report["images_differ"]) == 3
    with pytest.raises(privacy.StaleGallery):
        capture.verify(harness.owner, core=None, headed=False, prepared_python=harness.interpreter, strict_images=True)


def test_verify_ignores_clock_readings_but_not_labels(harness):
    record(harness)
    (harness.interpreter.parent / "hz").write_text('#!/bin/sh\necho "Hello, Mira! 10:22"\n')
    transcript = harness.owner / capture.OUTPUT / "cli.txt"
    transcript.write_text("Hello, Mira! 02:01\n")
    manifest = json.loads((harness.owner / capture.MANIFEST).read_text())
    manifest["transcripts"]["cli.txt"] = hashlib.sha256(transcript.read_bytes()).hexdigest()
    (harness.owner / capture.MANIFEST).write_text(json.dumps(manifest))
    assert capture.verify(harness.owner, core=None, headed=False, prepared_python=harness.interpreter)["ok"]


def test_cli_arguments_stay_literal_and_never_become_interpreter_or_shell_options(tmp_path):
    binary = tmp_path / "bin"
    binary.mkdir()
    interpreter = binary / "python"
    interpreter.symlink_to(sys.executable)
    marker = tmp_path / "should-not-exist"
    (binary / "hz").write_text("import json, sys\nprint(json.dumps(sys.argv[1:]))\n")
    arguments = ["-c", f"open({str(marker)!r}, 'w').write('bad')", "; touch should-not-exist"]
    env = capture.demo_environment(tmp_path / "demo", interpreter)
    assert json.loads(capture.hz(interpreter, arguments, env, tmp_path)) == arguments
    assert not marker.exists()
    assert not (tmp_path / "should-not-exist").exists()
    with pytest.raises(privacy.CaptureError, match="bounded list"):
        capture.hz(interpreter, ["safe", "bad\x00argument"], env, tmp_path)
