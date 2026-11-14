"""The real `Gws` runner against a stand-in `gws` executable: arguments, environment, timeout and output bounds."""

import json
import sys
import threading
import time
import tracemalloc
from pathlib import Path

import pytest

from heinzel_google import GoogleSession, GoogleSettings, Gws, _gws

pytestmark = pytest.mark.integration

SCRIPT = """\
import json, os, sys, time
mode_file = os.path.join(os.path.dirname(sys.argv[0]), "mode")
mode = open(mode_file).read().strip() if os.path.exists(mode_file) else "echo"
if sys.argv[1:] == ["--version"]:
    print("gws 0.22.5")
elif mode == "echo":
    names = sorted(k for k in os.environ if k.startswith("HZ_CREDENTIAL_"))
    print(json.dumps({"argv": sys.argv[1:], "credentials": names}))
    sys.stderr.write("note\\n")
elif mode == "sleep":
    time.sleep(30)
elif mode == "flood":
    for _ in range(10):
        sys.stdout.write("x" * 100_000)
        sys.stdout.flush()
elif mode == "auth":
    print(json.dumps({"error": {"code": 401, "message": "Access denied.", "reason": "authError"}}))
    sys.exit(2)
"""


@pytest.fixture
def stand_in(tmp_path):
    script = tmp_path / "gws"
    script.write_text(f"#!{sys.executable}\n{SCRIPT}", encoding="utf-8")
    script.chmod(0o755)
    return str(script)


def test_arguments_arrive_as_a_list_and_credentials_stay_home(stand_in, monkeypatch):
    monkeypatch.setenv("HZ_CREDENTIAL_OTHER_TOKEN", "never-passed-on")
    process = Gws().run(stand_in, ["drive", "files", "get", "--params", '{"fileId":"x y; echo hi"}'], 10)
    assert process.exit_code == 0
    assert json.loads(process.stdout) == {
        "argv": ["drive", "files", "get", "--params", '{"fileId":"x y; echo hi"}'],
        "credentials": [],
    }
    assert process.stderr == b"note\n"
    assert not process.truncated


def test_a_run_past_its_timeout_is_stopped(stand_in, tmp_path, monkeypatch):
    (tmp_path / "mode").write_text("sleep")
    started = time.monotonic()
    process = Gws().run(stand_in, [], 0.5)
    assert process.exit_code is None
    assert time.monotonic() - started < 5


def test_output_past_the_limit_is_cut(stand_in, tmp_path, monkeypatch):
    (tmp_path / "mode").write_text("flood")
    monkeypatch.setattr(_gws, "MAX_BYTES", 1000)
    process = Gws().run(stand_in, [], 10)
    assert (len(process.stdout), process.truncated) == (1000, True)


def test_the_session_maps_a_real_auth_failure(stand_in, tmp_path, monkeypatch):
    (tmp_path / "mode").write_text("auth")
    session = GoogleSession(GoogleSettings(gws_path=stand_in), Gws())
    with pytest.raises(Exception, match="not signed in"):
        session.get("Google Drive", ("drive", "files", "get"), {"fileId": "x"}, "file x")


def test_sleep_waits(monkeypatch):
    waited: list[float] = []
    monkeypatch.setattr(_gws.time, "sleep", waited.append)
    Gws().sleep(2.0)
    assert waited == [2.0]


@pytest.fixture
def shell_stand_in(tmp_path):
    def make(body: str) -> str:
        script = tmp_path / "gws-sh"
        script.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        script.chmod(0o755)
        return str(script)

    return make


def test_gws_runs_from_a_neutral_directory(shell_stand_in, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # a project directory, perhaps with a .env gws would read
    process = Gws().run(shell_stand_in("pwd"), [], 10)
    assert process.stdout.decode().strip() == _gws.NEUTRAL


def test_a_run_that_ignores_sigterm_is_killed(shell_stand_in, monkeypatch):
    monkeypatch.setattr(_gws, "GRACE", 0.3)
    started = time.monotonic()
    # Two seconds to install the trap before SIGTERM arrives, also on a loaded machine.
    process = Gws().run(shell_stand_in("trap '' TERM\necho ready\nwhile :; do sleep 1; done"), [], 2.0)
    assert process.exit_code is None
    assert 2.0 + 0.3 <= time.monotonic() - started < 10  # SIGTERM was ignored, SIGKILL ended it


def test_output_held_open_by_an_escaped_child_counts_as_cut(shell_stand_in, monkeypatch):
    monkeypatch.setattr(_gws, "GRACE", 0.3)
    child = "import subprocess, sys; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(3)'], "
    child += "start_new_session=True); print('partial')"
    process = Gws().run(shell_stand_in(f'{sys.executable} -c "{child}"'), [], 10)
    assert process.truncated


def test_login_runs_with_the_terminal_and_returns_its_exit_code(shell_stand_in):
    assert Gws().login(shell_stand_in("exit 3"), ["auth", "login"], 10) == 3
    assert Gws().login(shell_stand_in("sleep 5"), [], 0.2) is None


def test_a_login_that_ignores_sigterm_is_killed(shell_stand_in, monkeypatch):
    monkeypatch.setattr(_gws, "GRACE", 0.3)
    assert Gws().login(shell_stand_in("trap '' TERM\nwhile :; do sleep 1; done"), [], 2.0) is None


LAUNCHD_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
"""The PATH a launchd service gets when its plist sets none: no Homebrew directory in it."""


@pytest.fixture
def npm_gws(no_homebrew, tmp_path):
    """gws as npm installs it under Homebrew: a link in Homebrew's bin to a `#!/usr/bin/env node` launcher, with
    `node` in that bin. The stand-in `node` runs the launcher with Python; it prints what gws 0.22.5 prints."""
    directory = Path(no_homebrew[0])
    directory.mkdir(parents=True)
    node = directory / "node"
    node.write_text(f'#!/bin/sh\nexec {sys.executable} "$@"\n', encoding="utf-8")
    node.chmod(0o755)
    launcher = tmp_path / "homebrew-arm" / "lib" / "node_modules" / "cli" / "run.js"
    launcher.parent.mkdir(parents=True)
    launcher.write_text(
        "#!/usr/bin/env node\nimport sys\n"
        'if sys.argv[1:] == ["--version"]:\n'
        '    print("gws 0.22.5")\n'
        '    print("This is not an officially supported Google product.")\n'
        "else:\n"
        '    print(\'{"id": "x"}\')\n',
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    (directory / "gws").symlink_to(launcher)
    return str(directory / "gws")


@pytest.mark.parametrize("configured", [True, False], ids=["google.gws_path", "found by Heinzel"])
def test_npm_gws_under_a_launchd_path_says_its_version_and_answers(npm_gws, monkeypatch, configured):
    monkeypatch.setenv("PATH", LAUNCHD_PATH)
    session = GoogleSession(GoogleSettings(gws_path=npm_gws if configured else None), Gws())
    assert session.executable() == npm_gws
    assert session.version() == "0.22.5"
    assert session.get("Google Drive", ("drive", "files", "get"), {"fileId": "x"}, "file x")[0] == {"id": "x"}


CONSENT = "https://accounts.google.com/o/oauth2/auth?client_id=example&scope=x"


def test_a_sign_in_hands_over_each_line_and_returns_the_exit_code(shell_stand_in):
    script = shell_stand_in(f'echo "Open this URL in your browser to authenticate:"\necho "{CONSENT}" >&2\nexit 0')
    lines: list[str] = []
    code = Gws().sign_in(script, ["auth", "login"], lines.append, threading.Event(), 10.0)
    assert code == 0
    assert lines == ["Open this URL in your browser to authenticate:", CONSENT]  # stderr too


def test_a_stopped_sign_in_is_killed_with_what_it_started(shell_stand_in, tmp_path):
    marker = tmp_path / "child-alive"
    script = shell_stand_in(f'echo "{CONSENT}"\n(sleep 2; touch {marker}) &\nwhile :; do sleep 1; done')
    stop = threading.Event()
    lines: list[str] = []

    def line(text: str) -> None:
        lines.append(text)
        stop.set()  # the person cancelled after the page was shown

    started = time.monotonic()
    assert Gws().sign_in(script, [], line, stop, 30.0) is None
    assert time.monotonic() - started < 5
    time.sleep(2.5)
    assert not marker.exists()  # its whole process group was stopped


def test_a_sign_in_past_its_time_is_stopped(shell_stand_in):
    assert (
        Gws().sign_in(shell_stand_in("while :; do sleep 1; done"), [], lambda _: None, threading.Event(), 0.3) is None
    )


def test_a_sign_in_reads_only_so_much_of_its_output(shell_stand_in, monkeypatch):
    monkeypatch.setattr(_gws, "SIGN_IN_OUTPUT", 20)
    lines: list[str] = []
    script = shell_stand_in("echo first-line-here\necho second-line-is-dropped\necho third")
    assert Gws().sign_in(script, [], lines.append, threading.Event(), 10.0) == 0
    assert lines == ["first-line-here"]


def test_a_sign_in_reads_nothing_from_standard_input(shell_stand_in):
    lines: list[str] = []
    started = time.monotonic()
    code = Gws().sign_in(shell_stand_in('read x; echo "got:[$x]"'), [], lines.append, threading.Event(), 5.0)
    assert code is not None
    assert time.monotonic() - started < 3
    assert lines == ["got:[]"]


def test_one_huge_line_keeps_memory_bounded_and_is_skipped(shell_stand_in):
    lines: list[str] = []
    script = shell_stand_in("head -c 20000000 /dev/zero | tr '\\0' a\necho\necho after")
    tracemalloc.start()
    try:
        code = Gws().sign_in(script, [], lines.append, threading.Event(), 60.0)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert code == 0
    assert peak < 5_000_000, peak
    assert lines == []  # past SIGN_IN_OUTPUT nothing more is looked at


def test_an_overlong_line_is_skipped_whole_and_the_next_one_read(shell_stand_in, monkeypatch):
    monkeypatch.setattr(_gws, "SIGN_IN_LINE", 8)
    lines: list[str] = []
    script = shell_stand_in("printf 'https://accounts.google.com/long\\nshort\\n'")
    assert Gws().sign_in(script, [], lines.append, threading.Event(), 10.0) == 0
    assert lines == ["short"]


def test_a_failing_line_handler_never_stalls_gws(shell_stand_in):
    def broken(_: str) -> None:
        raise RuntimeError

    script = shell_stand_in(f'echo "{CONSENT}"\nhead -c 2000000 /dev/zero\nexit 0')
    started = time.monotonic()
    assert Gws().sign_in(script, [], broken, threading.Event(), 30.0) == 0  # the pipe is drained, gws ends
    assert time.monotonic() - started < 10
