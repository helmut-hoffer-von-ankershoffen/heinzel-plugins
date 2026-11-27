"""Only the attested owning prefix is fictionalized; all other privacy failures remain failures."""

import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from heinzel_plugin_tools import _presentation as presentation
from heinzel_plugin_tools import capture, capture_host
from heinzel_plugin_tools.privacy import CaptureError

pytestmark = pytest.mark.unit


@pytest.fixture
def environment(tmp_path):
    prefix = tmp_path / ".venv"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(prefix)], check=True, timeout=30)  # noqa: S603 - own Python creates a disposable test venv
    return tmp_path, prefix / "bin/python"


def test_real_selected_interpreter_attests_only_its_normal_owning_prefix(environment):
    root, interpreter = environment
    identity = presentation.owning_prefix(root, interpreter)
    assert identity.prefix == str(root / ".venv")
    identity.verify()
    (root / ".venv/pyvenv.cfg").write_text("replaced\n")
    with pytest.raises(CaptureError, match="changed"):
        identity.verify()


@pytest.mark.parametrize("reported", ["/", str(Path.home()), "/unknown/.venv"])
def test_reported_root_home_and_mismatched_prefixes_are_refused(environment, monkeypatch, reported):
    root, interpreter = environment
    monkeypatch.setattr(
        presentation.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            stdout=json.dumps([reported, str(interpreter), socket.gethostname()])
        ),
    )
    with pytest.raises(CaptureError, match="exact owning"):
        presentation.owning_prefix(root, interpreter)


def test_external_interpreter_cannot_request_prefix_redaction(environment):
    root, _interpreter = environment
    with pytest.raises(CaptureError, match="not the normal"):
        presentation.owning_prefix(root, Path(sys.executable))


def test_foreign_alias_and_reported_executable_are_not_accepted_as_identity(environment, monkeypatch):
    root, interpreter = environment
    alias = root / "alias"
    alias.symlink_to(root / ".venv", target_is_directory=True)
    for prefix, executable in [(str(alias), str(alias / "bin/python")), (str(root / ".venv"), sys.executable)]:
        monkeypatch.setattr(
            presentation.subprocess,
            "run",
            lambda *_args, _prefix=prefix, _executable=executable, **_kwargs: SimpleNamespace(
                stdout=json.dumps([_prefix, _executable, socket.gethostname()])
            ),
        )
        with pytest.raises(CaptureError, match="exact owning"):
            presentation.owning_prefix(root, interpreter)


def test_verified_darwin_system_alias_is_accepted_only_when_it_reaches_the_same_environment(environment, monkeypatch):
    root, interpreter = environment
    prefix = str(root.resolve() / ".venv")
    if sys.platform == "darwin" and prefix.startswith(("/private/var/", "/private/tmp/")):
        prefix = prefix.removeprefix("/private")
    monkeypatch.setattr(
        presentation.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            stdout=json.dumps([prefix, prefix + "/bin/python", socket.gethostname()])
        ),
    )
    assert presentation.owning_prefix(root, interpreter).prefix == prefix


def test_symlinked_environment_root_and_foreign_interpreter_are_refused(environment, tmp_path):
    root, interpreter = environment
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / ".venv").symlink_to(root / ".venv", target_is_directory=True)
    with pytest.raises(CaptureError, match="aliases"):
        presentation.owning_prefix(foreign, foreign / ".venv/bin/python")
    other = root / "other"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(other)], check=True, timeout=30)  # noqa: S603 - own Python creates a disposable test venv
    interpreter.unlink()
    interpreter.symlink_to(other / "bin/python")
    with pytest.raises(CaptureError, match="foreign environment"):
        presentation.owning_prefix(root, interpreter)


def test_group_writable_environment_is_not_a_redaction_authority(environment):
    root, interpreter = environment
    (root / ".venv").chmod(0o775)
    with pytest.raises(CaptureError, match="private, owned"):
        presentation.owning_prefix(root, interpreter)


class TextPage:
    """Execute the real presentation JavaScript against text-node fixtures, never manufactured product UI."""

    url = "http://127.0.0.1:8123/doctor"

    def __init__(self, texts):
        self.texts = texts
        self.saved = False

    def title(self):
        return "Heinzel"

    def evaluate(self, script, argument):
        node = shutil.which("node")
        assert node
        program = (
            'const vm=require("node:vm");'
            f"const nodes={json.dumps(self.texts)}.map(textContent=>({{textContent,parentElement:{{tagName:'TD'}}}}));"
            "const context={NodeFilter:{SHOW_TEXT:4},location:{hash:'',pathname:'/'},document:{body:{},"
            "createTreeWalker:()=>{let i=0;return{nextNode:()=>nodes[i++]??null}},querySelectorAll:()=>[]}};"
            f"const outcome=vm.runInNewContext({json.dumps('(' + script + ')')},context)({json.dumps(argument)});"
            "console.log(JSON.stringify({texts:nodes.map(n=>n.textContent),outcome}));"
        )
        result = subprocess.run([node, "-e", program], capture_output=True, text=True, check=True, timeout=5)  # noqa: S603 - fixed Node program exercises the actual renderer
        result = json.loads(result.stdout)
        self.texts = result["texts"]
        return result.get("outcome")

    def locator(self, _selector):
        return SimpleNamespace(inner_text=lambda: "\n".join(self.texts), evaluate_all=lambda _script: "")

    def screenshot(self, **_options):
        self.saved = True


@pytest.mark.usefixtures("fictional_capture_terms")
def test_only_exact_owning_path_text_changes_and_all_doctor_rows_statuses_and_details_remain(environment, tmp_path):
    root, interpreter = environment
    identity = presentation.owning_prefix(root, interpreter)
    before = [
        "hostname",
        "UP",
        "demo-workstation",
        "installation",
        "DEGRADED",
        f"not a uv tool environment ({identity.prefix}); update unavailable",
        f"library {identity.prefix}/lib/site-packages",
        "other",
        "DOWN",
        "Original error",
    ]
    page = TextPage(before)
    body = capture.safe_screenshot(page, tmp_path / "safe.png", owning_interpreter_prefix=identity)
    expected = [text.replace(identity.prefix, "/demo-profile/.venv") for text in before]
    assert page.texts == expected
    assert body == "\n".join(expected)
    assert page.saved


@pytest.mark.parametrize(
    "suffix",
    [
        "-other",
        "2",
        ".backup",
        "/../foreign",
        "/./lib",
        "/%2e/lib",
        "/%2E%2e/foreign",
        "/%252e%252e/foreign",
        "/lib%2f..%2fforeign",
        "/lib\\..\\foreign",
        "/lib//foreign",
    ],
)
def test_lookalike_and_traversal_paths_remain_private_and_refuse_screenshot(environment, tmp_path, suffix):
    root, interpreter = environment
    identity = presentation.owning_prefix(root, interpreter)
    value = identity.prefix + suffix
    page = TextPage(["DEGRADED", value])
    with pytest.raises(CaptureError, match="private paths"):
        capture.safe_screenshot(page, tmp_path / "refused.png", owning_interpreter_prefix=identity)
    assert page.texts == ["DEGRADED", value]
    assert not page.saved


def test_unknown_private_path_in_another_row_still_refuses_the_entire_capture(environment, tmp_path):
    root, interpreter = environment
    identity = presentation.owning_prefix(root, interpreter)
    page = TextPage([f"installation ({identity.prefix})", "/private/tmp/unknown-owner/secret"])
    with pytest.raises(CaptureError, match="private paths"):
        capture.safe_screenshot(page, tmp_path / "refused.png", owning_interpreter_prefix=identity)
    assert page.texts == ["installation (/demo-profile/.venv)", "/private/tmp/unknown-owner/secret"]
    assert not page.saved


@pytest.mark.parametrize(
    "context",
    [
        "https://example.invalid/?path={prefix}",
        "https://example.invalid/?path= {prefix}",
        "https://example.invalid/?path=\t{prefix}",
        "https://example.invalid/?path=\n{prefix}/lib",
        "demo@example.invalid {prefix}",
        "demo@{prefix}",
        "mailto:demo@example.invalid?body= {prefix}",
    ],
)
def test_url_and_email_contexts_do_not_gain_path_redaction(environment, tmp_path, context):
    root, interpreter = environment
    identity = presentation.owning_prefix(root, interpreter)
    value = context.format(prefix=identity.prefix)
    page = TextPage(["DOWN", value])
    with pytest.raises(CaptureError, match="private paths"):
        capture.safe_screenshot(page, tmp_path / "refused.png", owning_interpreter_prefix=identity)
    assert page.texts == ["DOWN", value]
    assert not page.saved


@pytest.mark.parametrize(
    "hostname", ["foreign-host", "/private/tmp/host", "demo@example.invalid", "https://demo.invalid", "", "host name"]
)
def test_hostname_must_independently_match_controller_and_be_unambiguous(environment, monkeypatch, hostname):
    root, interpreter = environment
    monkeypatch.setattr(
        presentation.subprocess,
        "run",
        lambda *_a, **_kw: SimpleNamespace(stdout=json.dumps([str(root / ".venv"), str(interpreter), hostname])),
    )
    with pytest.raises(CaptureError, match="hostname"):
        presentation.owning_prefix(root, interpreter)
    if hostname != "foreign-host":
        monkeypatch.setattr(presentation.socket, "gethostname", lambda: hostname)
        with pytest.raises(CaptureError, match="hostname"):
            presentation.owning_prefix(root, interpreter)


@pytest.mark.parametrize("hostname", ["UP", "DOWN", "doctor", "fictional-host.example"])
def test_common_word_hostname_requires_the_same_independent_verification(environment, monkeypatch, hostname):
    root, interpreter = environment
    monkeypatch.setattr(presentation.socket, "gethostname", lambda: hostname)
    monkeypatch.setattr(
        presentation.subprocess,
        "run",
        lambda *_a, **_kw: SimpleNamespace(stdout=json.dumps([str(root / ".venv"), str(interpreter), hostname])),
    )
    assert presentation.owning_prefix(root, interpreter).hostname == hostname


def test_verified_hostname_change_invalidates_environment_evidence(environment, monkeypatch):
    root, interpreter = environment
    identity = presentation.owning_prefix(root, interpreter)
    assert identity.hostname == socket.gethostname()
    monkeypatch.setattr(presentation.socket, "gethostname", lambda: "changed-host")
    with pytest.raises(CaptureError, match="changed"):
        identity.verify()


@pytest.fixture
def capture_before_browser(monkeypatch):
    """These prefix lifecycle checks must stop before any browser work."""

    def unexpected_browser():
        pytest.fail("The prefix lifecycle check started a browser")

    monkeypatch.setitem(
        sys.modules, "playwright.sync_api", SimpleNamespace(Error=RuntimeError, sync_playwright=unexpected_browser)
    )
    monkeypatch.setitem(sys.modules, "rich.console", SimpleNamespace(Console=unexpected_browser))
    monkeypatch.setitem(sys.modules, "rich.terminal_theme", SimpleNamespace(MONOKAI=None))
    monkeypatch.setitem(sys.modules, "rich.text", SimpleNamespace(Text=unexpected_browser))


@pytest.mark.parametrize("external", [False, True])
@pytest.mark.parametrize("tamper", [False, True, "attestation-failure"])
@pytest.mark.usefixtures("capture_before_browser")
def test_capture_attests_after_wheel_config_replacement_and_restores(environment, monkeypatch, external, tamper):
    root, interpreter = environment
    events = []
    identities = []
    run = subprocess.run
    attest = capture.owning_prefix
    config = root / ".venv/pyvenv.cfg"
    original = config.read_bytes()
    reviewed_digest = "a" * 64

    def replace_config():
        replacement = config.with_suffix(".replacement")
        replacement.write_bytes(original)
        replacement.replace(config)

    def command(args, **kwargs):
        if args[0] != "uv":
            return run(args, **kwargs)
        if args[1] == "build":
            events.append("build")
            (Path(args[args.index("-o") + 1]) / "fictional.whl").touch()
        elif "--reinstall" in args:
            events.append("install")
            replace_config()
        elif "--editable" in args:
            events.append("restore")
        else:
            events.append("setup")
        return SimpleNamespace(returncode=0)

    def identity(*args):
        events.append("attest")
        if tamper == "attestation-failure":
            raise CaptureError("attestation refused")
        result = attest(*args)
        identities.append(result)
        if tamper:
            replace_config()
        return result

    class StopBeforeBackend(Exception):
        pass

    def demo(*args):
        events.append("demo")
        if identities:
            identities[0].verify()
        raise StopBeforeBackend

    def authorize(candidate_root, plan, selected_python, digest):
        assert candidate_root == root
        assert plan == {"scenes": []}
        assert selected_python == interpreter
        assert digest == reviewed_digest
        events.append("authorize")

    monkeypatch.setattr(capture, "read_plan", lambda *_: {"scenes": []})
    monkeypatch.setattr(capture, "project_data", lambda *_: {"project": {"name": "fictional"}})
    monkeypatch.setattr(capture, "prepared_version", lambda *_: "0.0.0")
    monkeypatch.setattr(capture.subprocess, "run", command)
    monkeypatch.setattr(capture, "owning_prefix", identity)
    monkeypatch.setattr(capture, "demo_environment", demo)
    monkeypatch.setattr(capture_host, "require_approval", authorize)
    failure = CaptureError if tamper and not external else StopBeforeBackend
    with pytest.raises(failure):
        capture.capture(
            root,
            core=None,
            headed=False,
            prepared_python=interpreter if external else None,
            prepared_approval=reviewed_digest if external else None,
        )
    expected = ["setup", "build", "install", "attest"]
    if tamper != "attestation-failure":
        expected.append("demo")
    assert events == (["authorize", "demo"] if external else [*expected, "restore"])


@pytest.mark.parametrize("unsafe", ["root-alias", "bin-alias", "config-alias", "writable", "foreign-python"])
@pytest.mark.usefixtures("capture_before_browser")
def test_capture_refuses_unsafe_existing_environment_before_setup(environment, monkeypatch, unsafe):
    root, interpreter = environment
    if unsafe == "writable":
        (root / ".venv").chmod(0o775)
    elif unsafe == "foreign-python":
        other = root / "other"
        subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(other)], check=True, timeout=30)  # noqa: S603 - disposable test venv
        interpreter.unlink()
        interpreter.symlink_to(other / "bin/python")
    else:
        path = {
            "root-alias": root / ".venv",
            "bin-alias": interpreter.parent,
            "config-alias": root / ".venv/pyvenv.cfg",
        }[unsafe]
        target = path.with_name(path.name + "-original")
        path.rename(target)
        path.symlink_to(target, target_is_directory=target.is_dir())

    def forbidden(*args, **kwargs):
        pytest.fail("unsafe existing environment reached execution or attestation")

    monkeypatch.setattr(capture, "read_plan", lambda *_: {"scenes": []})
    monkeypatch.setattr(capture, "project_data", lambda *_: {"project": {"name": "fictional"}})
    monkeypatch.setattr(capture.subprocess, "run", forbidden)
    monkeypatch.setattr(capture, "owning_prefix", forbidden)
    with pytest.raises(CaptureError):
        capture.capture(root, core=None, headed=False)
