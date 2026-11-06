"""Exercise the installed wheel through the public CLI, outside the source directory."""

import json
import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.e2e


def test_installed_manifest(tmp_path):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("HZ_")}
    environment["HZ_PLUGINS_ENABLED"] = "true"
    environment.pop("PYTHONPATH", None)
    for key in ("CONFIG_HOME", "DATA_DIR", "CACHE_DIR", "STATE_DIR", "LOG_DIR"):
        environment[f"HZ_{key}"] = str(tmp_path / key.lower())
    result = subprocess.run(
        [sys.executable, "-m", "heinzel", "slack", "manifest", "--json"],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    manifest = json.loads(json.loads(result.stdout))
    assert manifest["settings"]["socket_mode_enabled"] is True
    assert manifest["oauth_config"]["scopes"]["bot"] == ["chat:write", "im:write", "users:read"]


def test_installed_kernel_discovers_both_channel_ports_without_credentials(tmp_path, monkeypatch):
    from heinzel import ApprovalChannel, Kernel, NotificationChannel, Settings
    from heinzel.kernel import discover

    from heinzel_slack import SlackChannel, SlackService, Transport

    monkeypatch.setenv("HZ_SYSTEM_CREDENTIAL__BACKEND", "environment")
    records, errors = discover()
    assert not errors
    kernel = Kernel(Settings(state_dir=tmp_path / "state"), records, errors)
    notices = kernel.implementations(NotificationChannel)
    approvals = kernel.implementations(ApprovalChannel)
    channel = next(item for item in notices if isinstance(item, SlackChannel))
    assert channel is next(item for item in approvals if isinstance(item, SlackChannel))
    assert kernel.resolve(SlackService) is channel._service
    assert isinstance(kernel.resolve(Transport), Transport)
    assert channel.owner_actor() is None
    assert not channel.available()
