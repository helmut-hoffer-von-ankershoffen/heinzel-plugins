"""Exercise real private-sharing transactions against a loopback-only fictional Tailscale LocalAPI."""

import base64
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from socketserver import TCPServer

from heinzel import Config, Kernel, Settings
from heinzel.heads.cli import build
from heinzel.kernel import discover
from heinzel_tailscale import TailscaleCli
from heinzel_tailscale._cli import Result

DNS = "workstation.tail-example.ts.net"
PASSWORD = "documentation-only-local-api"
STATE = Path(os.environ["HZ_STATE_DIR"]) / "fictional-tailscale.json"
STATE.parent.mkdir(parents=True, exist_ok=True)
OTHER = {
    "svc:notes": {
        "TCP": {"8443": {"HTTPS": True}},
        "Web": {DNS + ":8443": {"Handlers": {"/": {"Proxy": "http://127.0.0.1:4444"}}}},
    }
}
if not STATE.exists():
    STATE.write_text(json.dumps({"version": 0, "writes": 0, "config": {"Services": OTHER}}))
    STATE.chmod(0o600)
LOCK = threading.Lock()


def state():
    return json.loads(STATE.read_text())


class LocalServer(ThreadingHTTPServer):
    """Bind without consulting DNS or any real network adapter."""

    def server_bind(self):
        TCPServer.server_bind(self)
        self.server_name = self.server_address[0]
        self.server_port = self.server_address[1]


class LocalAPI(BaseHTTPRequestHandler):
    """Only the expected authenticated conditional Serve endpoint; all other requests fail."""

    def log_message(self, *_arguments):
        pass

    def answer(self, status, body, etag=None):
        content = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        if etag is not None:
            self.send_header("ETag", str(etag))
        self.end_headers()
        self.wfile.write(content)

    def accepted(self):
        expected = "Basic " + base64.b64encode(f":{PASSWORD}".encode()).decode()
        return self.path == "/localapi/v0/serve-config" and self.headers.get("Authorization") == expected

    def do_GET(self):
        if not self.accepted():
            self.answer(403, {})
            return
        current = state()
        self.answer(200, current["config"], current["version"])

    def do_POST(self):
        if not self.accepted():
            self.answer(403, {})
            return
        with LOCK:
            current = state()
            if self.headers.get("If-Match") != str(current["version"]):
                self.answer(412, {})
                return
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 256 * 1024:
                self.answer(400, {})
                return
            changed = json.loads(self.rfile.read(size))
            if changed.get("Services") != OTHER:
                raise ValueError("Demonstration must preserve unrelated services")
            current.update(config=changed, version=current["version"] + 1, writes=current["writes"] + 1)
            temporary = STATE.with_suffix(".next")
            temporary.write_text(json.dumps(current))
            temporary.chmod(0o600)
            temporary.replace(STATE)
            self.answer(200, {})


class DemoCli(TailscaleCli):
    """Emulate only vendor discovery reads; the real ServeStore performs authenticated local HTTP writes."""

    def executable(self):
        return "/fixture/never-executed-tailscale"

    def run(self, arguments):
        if tuple(arguments) == ("status", "--json", "--peers=false"):
            payload = {"BackendState": "Running", "Self": {"DNSName": DNS + "."}, "CertDomains": [DNS]}
        elif tuple(arguments) == ("serve", "status", "--json"):
            payload = state()["config"]
        elif tuple(arguments) == ("debug", "local-creds"):
            return Result(
                0, f"curl -u:{PASSWORD} http://localhost:{server.server_port}/localapi/v0/status".encode(), b""
            )
        else:
            raise ValueError("Unexpected vendor request in the offline demonstration")
        return Result(0, json.dumps(payload).encode(), b"")


server = LocalServer(("127.0.0.1", 0), LocalAPI)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    config = Config.load()
    records, errors = discover()
    kernel = Kernel(config.settings(Settings, "hz"), records, errors, config)
    kernel.bind(TailscaleCli, DemoCli())
    sys.argv = ["hz", *sys.argv[1:]]
    build(kernel)()
finally:
    server.shutdown()
    server.server_close()
    if state()["config"].get("Services") != OTHER:
        raise ValueError("The fictional unrelated service must remain unchanged")
