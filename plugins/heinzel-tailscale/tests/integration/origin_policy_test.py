"""Only the owning session may prove the exact nonsecret origin policy loaded at server startup."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from heinzel import Config, Settings
from heinzel.heads import web

from heinzel_tailscale import TailscaleCli
from heinzel_tailscale import module as tailscale_module
from heinzel_tailscale._mapping import Mapping

pytestmark = pytest.mark.integration
TOKEN = "owning-session-for-origin-policy-proof"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
ONE = "https://workstation.tail-example.ts.net"
TWO = "https://other.example.test:9443"


def client_for(kernel, **options):
    return TestClient(
        web.build(kernel, port=8000, token=TOKEN, static=None, **options), base_url="http://127.0.0.1:8000"
    )


def expected(client, origins):
    running = client.get("/api/lifecycle", headers=AUTH).json()
    return {
        "instance": running["instance"],
        "version": running["version"],
        "settings": [{"section": "hz", "key": "ui_allowed_origins", "value": origins}],
    }


def test_actual_tailscale_apply_metadata_is_verified_by_the_replacement_owner(make_kernel, tmp_path):
    class StaticClient(TailscaleCli):
        def executable(self):
            return "/fake/tailscale"

        def json(self, arguments):
            if tuple(arguments) == ("status", "--json", "--peers=false"):
                return {
                    "BackendState": "Running",
                    "Self": {"DNSName": "workstation.tail-example.ts.net."},
                    "CertDomains": [ONE[8:]],
                }
            assert tuple(arguments) == ("serve", "status", "--json")
            return Mapping.for_node("workstation.tail-example.ts.net", 8000).enable({})

    def instance(config):
        kernel = make_kernel(
            builtins=True, tailscale=tailscale_module, config=config, settings_=config.settings(Settings, "hz")
        )
        kernel.bind(TailscaleCli, StaticClient())
        return client_for(kernel)

    config = Config.load(tmp_path)
    before = instance(config)
    directory = Path(os.environ["HZ_CONFIG_HOME"])
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "config.toml").write_text(
        f'[hz]\nui_allowed_origins = ["{ONE}"]\n'
        "[tailscale.intent]\nenabled = true\n"
        f'origin = "{ONE}"\nbackend_port = 8000\nhttps_port = 443\nadded_origin = true\nphase = "owned"\n'
    )
    row = before.get("/api/system/ui/status", params={"item": "tailscale:sharing"}, headers=AUTH).json()[0]
    assert row["problem"] is None
    assert row["item"]["toggle"]["checked"] is False
    apply = row["item"]["toggle"]["apply_settings"]
    assert apply == {"hz.ui_allowed_origins": [ONE]}
    assert not before.post(
        "/api/lifecycle/verify", headers=AUTH, json=expected(before, apply["hz.ui_allowed_origins"])
    ).json()["matches"]
    replacement = instance(config.reread())
    proof = replacement.post(
        "/api/lifecycle/verify", headers=AUTH, json=expected(replacement, apply["hz.ui_allowed_origins"])
    )
    assert proof.json()["matches"] is True
    ready = replacement.get("/api/system/ui/status", params={"item": "tailscale:sharing"}, headers=AUTH).json()[0]
    assert ready["item"]["toggle"]["checked"] is True
