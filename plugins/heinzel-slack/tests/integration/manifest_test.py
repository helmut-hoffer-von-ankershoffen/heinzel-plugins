"""The shipped manifest asks for as little as the plugin uses, and for no address on the internet."""

import json
from importlib.resources import files

import pytest

pytestmark = pytest.mark.integration


def test_manifest_is_minimal_and_needs_no_public_address():
    manifest = json.loads((files("heinzel_slack") / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["oauth_config"]["scopes"] == {"bot": ["chat:write", "im:write", "users:read"]}
    assert "user" not in manifest["oauth_config"]["scopes"]  # never acts as the person
    assert manifest["settings"]["socket_mode_enabled"] is True
    assert "request_url" not in json.dumps(manifest)
    assert "event_subscriptions" not in manifest["settings"]  # replies and reactions are not even delivered
    assert manifest["features"]["app_home"]["messages_tab_read_only_enabled"] is True


def test_no_operation_can_approve():
    from heinzel_slack import module

    names = {let.name for let in module.lets if hasattr(let, "name")}
    assert not {n for n in names if "approve" in n.lower() or "decide" in n.lower()}
