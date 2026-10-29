"""Heinzelmännchen's CLI head with this plugin discovered through its real entry point. Offline."""

import json

import pytest
from heinzel.heads.cli import build
from typer.testing import CliRunner

pytestmark = pytest.mark.integration

runner = CliRunner()


def invoke(kernel, *args: str):
    result = runner.invoke(build(kernel), list(args))
    assert result.exit_code == 0, result.output
    return result.output


def test_plugin_modules_are_discovered(boot):
    qualnames = [record.qualname for record in boot().modules]
    assert "example" in qualnames
    assert "example.hello" in qualnames


def test_info(boot):
    about = json.loads(invoke(boot(), "example", "info", "--json"))
    assert about["plugin"] == "heinzel-example"
    assert about["modules"] == ["example", "example.hello"]


def test_hello_submodule_collapses_into_a_command(boot):
    assert json.loads(invoke(boot(), "example", "hello", "--name", "Ada", "--json")) == {"text": "Hello, Ada!"}


def test_contributes_to_system_info(boot):
    sections = json.loads(invoke(boot(), "system", "info", "--json"))["sections"]
    assert sections["example"]["plugin"] == "heinzel-example"


def test_plugin_can_be_disabled(boot):
    kernel = boot(disabled_modules=frozenset({"example"}))
    assert not [r for r in kernel.modules if r.qualname.startswith("example")]


def test_greeting_is_configurable_through_the_environment(boot, monkeypatch):
    monkeypatch.setenv("HZ_EXAMPLE__GREETING", "Hi")
    assert json.loads(invoke(boot(), "example", "hello", "--name", "Ada", "--json")) == {"text": "Hi, Ada!"}


def test_greeting_is_configurable_through_a_config_file(monkeypatch, tmp_path):
    from heinzel import Config, Kernel
    from heinzel.kernel import discover

    (tmp_path / "hz.toml").write_text('[example]\ngreeting = "Moin"\n', encoding="utf-8")
    kernel = Kernel(records=discover()[0], config=Config.load(tmp_path))
    assert json.loads(invoke(kernel, "example", "hello", "--name", "Ada", "--json")) == {"text": "Moin, Ada!"}
