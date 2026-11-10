"""Only the attested owning prefix is fictionalized; all other privacy failures remain failures."""

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace

import pytest

from heinzel_plugin_tools import _presentation as presentation
from heinzel_plugin_tools import capture
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

    def __init__(self, texts, *, node_transport=None):
        self.texts = texts
        self.saved = False
        self.node_transport = node_transport

    def evaluate(self, script, argument):
        node = shutil.which("node")
        assert node
        transport = self.node_transport
        self.node_transport = None  # Compare only the first evaluation, which timed out in CI.
        entry = before_vm = after_vm = after_output = ""
        if transport:
            entry = (
                "const mark=phase=>require('node:fs').writeSync(2,phase+'\\n');mark('entry '+process.versions.node);"
            )
            before_vm = "mark('before-vm');"
            after_vm = "mark('after-vm');"
            after_output = "mark('after-output');"
        program = (
            f"{entry}"
            'const vm=require("node:vm");'
            f"const nodes={json.dumps(self.texts)}.map(textContent=>({{textContent,parentElement:{{tagName:'TD'}}}}));"
            "const context={NodeFilter:{SHOW_TEXT:4},location:{hash:'',pathname:'/'},document:{body:{},"
            "createTreeWalker:()=>{let i=0;return{nextNode:()=>nodes[i++]??null}},querySelectorAll:()=>[]}};"
            f"{before_vm}const outcome=vm.runInNewContext({json.dumps('(' + script + ')')},"
            f"context)({json.dumps(argument)});{after_vm}"
            f"console.log(JSON.stringify({{texts:nodes.map(n=>n.textContent),outcome}}));{after_output}"
        )
        if transport:
            output = _compare_node_transport(node, program, transport)
        else:
            output = subprocess.run(  # noqa: S603 - fixed Node program exercises the actual renderer
                [node, "-e", program], capture_output=True, text=True, check=True, timeout=5
            ).stdout
        result = json.loads(output)
        self.texts = result["texts"]
        return result.get("outcome")

    def locator(self, _selector):
        return SimpleNamespace(inner_text=lambda: "\n".join(self.texts), evaluate_all=lambda _script: "")

    def screenshot(self, **_options):
        self.saved = True


def _compare_node_transport(node, program, transport):
    """Use the same child and deadline, with or without waiting for captured pipe EOF."""
    assert transport in {"pipe", "file"}, "Use pipe or file for HZ_COMPARE_PRESENTATION_NODE"
    with ExitStack() as stack:
        stdout_file = stack.enter_context(tempfile.TemporaryFile()) if transport == "file" else None
        stderr_file = stack.enter_context(tempfile.TemporaryFile()) if transport == "file" else None
        process = stack.enter_context(
            subprocess.Popen(  # noqa: S603 - same fixed Node fixture as the ordinary test
                [node, "-e", program], stdout=stdout_file or subprocess.PIPE, stderr=stderr_file or subprocess.PIPE
            )
        )
        timeout_state = None
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired as error:
            timeout_state = "running" if process.poll() is None else "exited"
            process.kill()
            process.wait()
            stdout, stderr = error.stdout, error.stderr
        if stdout_file is not None and stderr_file is not None:
            stdout_file.seek(0)
            stderr_file.seek(0)
            stdout, stderr = stdout_file.read(), stderr_file.read()
        phases = []
        version = "unobserved"
        for line in (stderr or b"").splitlines():
            if entry := re.fullmatch(rb"entry ([0-9]+\.[0-9]+\.[0-9]+)", line):
                version = entry[1].decode()
                phases.append("entry")
            elif line in {b"before-vm", b"after-vm", b"after-output"}:
                phases.append(line.decode())
        state = timeout_state or "completed"
        print(
            f"Node transport={transport} child={state} phases={','.join(phases) or 'none'} node={version}",
            flush=True,
        )
        if timeout_state:
            pytest.fail("Node presentation comparison timed out after five seconds", pytrace=False)
        if process.returncode:
            pytest.fail(f"Node presentation comparison exited with status {process.returncode}", pytrace=False)
        return stdout


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
    page = TextPage(before, node_transport=os.environ.get("HZ_COMPARE_PRESENTATION_NODE"))
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
