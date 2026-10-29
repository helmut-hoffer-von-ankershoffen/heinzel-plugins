"""The installed Clock plugin uses the public setup contract and every head."""

import pytest
from heinzel import Config, Settings
from heinzel.heads.cli import build
from typer.testing import CliRunner

import heinzel_clock

pytestmark = pytest.mark.integration
runner = CliRunner()
AT = "2026-10-23T12:00:00Z"
INVALID_CLOCK = Config(files=(), data={"clock": {"zones": [{"name": "Asia/Tokyo", "hours": [19, 10]}]}})


@pytest.fixture
def kernel(make_kernel):
    return make_kernel(builtins=True, clock=heinzel_clock.module, settings_=Settings(disabled_modules={"org"}))


@pytest.fixture
def terminal(monkeypatch, tmp_path):
    from heinzel.heads.cli import _setup

    monkeypatch.setattr(_setup, "has_terminal", lambda: True)
    monkeypatch.chdir(tmp_path)


def test_a_collapsed_module_keeps_its_command_and_runs_its_step_under_setup(kernel, terminal):
    app = build(kernel)
    times = runner.invoke(app, ["clock", "--at", AT, "--json"])
    assert times.exit_code == 0, times.output
    assert times.stdout.startswith("[")
    help_text = runner.invoke(app, ["clock", "--help"]).output
    assert "--at" in help_text
    assert "setup" not in help_text  # the step is `hz setup clock`, never part of the module's commands
    assert "Commands" not in help_text
    result = runner.invoke(app, ["setup", "clock"], input="\n\n" + "\n" * 6 + "n\n")
    assert result.exit_code == 0, result.output
    assert "Nothing was saved." in result.output


def test_invalid_settings_fail_the_step_with_a_message_not_a_traceback(make_kernel, terminal):
    kernel = make_kernel(builtins=True, config=INVALID_CLOCK, clock=heinzel_clock.module)
    result = runner.invoke(build(kernel), ["setup", "clock"])
    assert result.exit_code == 1
    assert "clock failed: its configuration is invalid: ClockSettings zones.0" in " ".join(result.output.split())
    assert "hz system config show" in result.output


def test_invalid_settings_without_a_terminal_are_a_configuration_error(make_kernel):
    kernel = make_kernel(builtins=True, config=INVALID_CLOCK, clock=heinzel_clock.module)
    result = runner.invoke(build(kernel), ["setup"])
    assert result.exit_code == 1
    assert "Configuration error:" in result.stderr
    assert "Traceback" not in result.output
