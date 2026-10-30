"""Profile claims require the selected SDK and a complete managed lifecycle, not parser acceptance alone."""

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from heinzel_plugin_tools import cli, installation

pytestmark = pytest.mark.unit


def local_profile(tmp_path):
    wheel = tmp_path / "heinzel-1.0.0-py3-none-any.whl"
    wheel.write_bytes(b"accepted SDK fixture")
    profile = tmp_path / "local.json"
    profile.write_text(
        json.dumps(
            {
                "format": 2,
                "sdk": 1,
                "core_version": "1.0.0",
                "artifacts": [{"name": "heinzel", "version": "1.0.0", "url": str(wheel)}],
            }
        )
    )
    return profile, wheel


def test_isolation_removes_checkout_overrides_and_tool_authority_but_preserves_index_auth(tmp_path, monkeypatch):
    credential = str(tmp_path / "resolver-credential")
    for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "UV_OVERRIDE", "GH_TOKEN", "HZ_CONFIG_HOME"):
        monkeypatch.setenv(key, "unrelated")
    monkeypatch.setenv("UV_INDEX_PRIVATE_PASSWORD", credential)
    env = installation.isolated_environment(tmp_path)
    assert not {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "UV_OVERRIDE", "GH_TOKEN"} & env.keys()
    assert env["HZ_CONFIG_HOME"] == str(tmp_path / "config_home")
    assert env["UV_TOOL_DIR"] == str(tmp_path / "tools")
    assert env["UV_INDEX_PRIVATE_PASSWORD"] == credential


@pytest.mark.parametrize("failure", [None, "missing-checkpoint", "stale-update", "changed-artifact"])
def test_managed_acceptance_requires_offline_membership_and_updated_runtime(tmp_path, monkeypatch, failure):
    profile, wheel = local_profile(tmp_path)
    state = {"version": None, "updates": 0, "launches": 0}

    def run(command, *, cwd, env):
        assert "PYTHONPATH" not in env and "PYTHONHOME" not in env
        assert "UV_FIND_LINKS" not in env
        assert Path(env["UV_CONSTRAINT"]).read_text() == f"heinzel @ {wheel.as_uri()}\n"
        if str(command[0]).endswith("/bin/hz"):
            args = command[1:-1]
            if args[:3] == ["system", "plugin", "develop"]:
                state["version"] = "0.2.0" if state["updates"] else "0.1.0"
                if failure == "changed-artifact":
                    wheel.write_bytes(b"modified SDK")
                return '{"done":true}'
            if args[:2] == ["system", "update"]:
                state["updates"] += 1
                if failure != "stale-update":
                    state["version"] = "0.2.0"
                return '{"after":"1.0.0"}'
            if args[:3] == ["system", "plugin", "remove"]:
                state["version"] = None
                return '{"done":true}'
            assert args == ["lifecycleprobe", "ping"]
            return json.dumps(state["version"])
        assert command[1] == "-I"
        if "-c" in command and "startup_state_matches" in command[3]:
            if failure == "missing-checkpoint":
                raise SystemExit(1)
        elif str(command[2]).endswith("/heinzel"):
            assert env["UV_OFFLINE"] == "1"
            assert not Path(env["HZ_APP_PROFILE"]).exists()
            state["launches"] += 1
            return json.dumps(
                [{"distribution": "heinzel-lifecycle-probe", "enabled": True, "error": None}]
                if state["version"]
                else []
            )
        return ""

    monkeypatch.setattr(installation, "_run", run)
    if failure:
        with pytest.raises((ValueError, SystemExit)):
            installation.verify_managed_profile(tmp_path / "sdk/bin/python", profile)
    else:
        installation.verify_managed_profile(tmp_path / "sdk/bin/python", profile)
        assert state["updates"] == 1 and state["launches"] == 5


def test_public_profile_command_cannot_publish_an_unchecked_legacy_sdk(tmp_path, monkeypatch):
    core = tmp_path / "heinzel-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(core, "w") as archive:
        archive.writestr("heinzel-1.0.0.dist-info/METADATA", "Name: heinzel\nVersion: 1.0.0\n")
    output = tmp_path / "standard.json"
    output.write_text("preserve previous output")
    monkeypatch.setattr(cli, "projects", lambda: [])

    def refuse(selected, draft):
        assert selected == core
        assert json.loads(draft.read_text())["format"] == 2
        assert output.read_text() == "preserve previous output"
        raise SystemExit(2)

    monkeypatch.setattr(installation, "verify_profile", refuse)
    monkeypatch.setattr(sys, "argv", ["hz-plugin", "profile", "--core", str(core), "--output", str(output)])
    with pytest.raises(SystemExit) as failure:
        cli.main()
    assert failure.value.code == 2
    assert output.read_text() == "preserve previous output"


@pytest.mark.parametrize("change", ["wheel", "profile"])
def test_public_profile_preserves_previous_output_if_accepted_inputs_change(tmp_path, monkeypatch, change):
    core = tmp_path / "heinzel-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(core, "w") as archive:
        archive.writestr("heinzel-1.0.0.dist-info/METADATA", "Name: heinzel\nVersion: 1.0.0\n")
    output = tmp_path / "standard.json"
    output.write_text("previous accepted output")
    monkeypatch.setattr(cli, "projects", lambda: [])

    def accept_then_change(_selected, candidate):
        if change == "wheel":
            # Still a readable wheel: selecting it again would publish new, unaccepted bytes.
            replacement = tmp_path / "replacement.whl"
            replacement.write_bytes(core.read_bytes() + b"changed after acceptance")
            replacement.replace(core)
        else:
            value = json.loads(candidate.read_text())
            value["sdk"] = 99
            candidate.write_text(json.dumps(value))

    monkeypatch.setattr(installation, "verify_profile", accept_then_change)
    monkeypatch.setattr(sys, "argv", ["hz-plugin", "profile", "--core", str(core), "--output", str(output)])
    with pytest.raises(ValueError, match="changed"):
        cli.main()
    assert output.read_text() == "previous accepted output"


def test_a_failed_installed_step_retains_its_exit_code_and_diagnostics(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        installation.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 7, "Scoped repair needed\n"),
    )
    with pytest.raises(SystemExit) as failure:
        installation._run(["controlled-step"], cwd=tmp_path, env={})
    assert failure.value.code == 7
    assert capsys.readouterr().err == "Scoped repair needed\n"
