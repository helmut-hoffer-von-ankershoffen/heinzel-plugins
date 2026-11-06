"""Exercise Core review and Slack decision code with a fictional workspace in an isolated gallery profile."""

import json
import os
import secrets
import stat
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from heinzel import ChannelApprovalRequest, Config, Kernel, Module, ModuleRecord, Settings
from heinzel.heads.cli import build
from heinzel.kernel import Origin, discover
from pydantic import BaseModel, Field
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

os.environ.setdefault("TZ", "Europe/Berlin")
time.tzset()
NOW = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
OWNER, STRANGER, TEAM, DM = "U0MIRA0001", "U0JONAS002", "T0DEMO0001", "D0DEMO0001"
BOT = "U0DEMO0001"
TITLE = "Weekly report is ready"
BODY = "Lotte finished the fictional reading-list rollout report. Mira can review it before the demo team meeting."
NOTICE = {"key": "gallery-notice", "helper": "Lotte", "title": TITLE, "body": BODY, "route": ""}
COMMAND = "Review exact channel posting account, destination, scope and full message"
RECEIPT = f"Ran `{COMMAND}`: The channel reported delivered. This does not approve the captured write."
CONFIRM = "/api/system/runner/chat/confirm"
CORE_ERROR_CATEGORIES = {
    "Channel actions require the authenticated owner and a trusted human confirmation": "owner_context_refused",
    "Choose one notice or one exact captured-write review": "invalid_proposal_kind",
    "Channel delivery requires a source-bound transport": "source_binding_unavailable",
    "The selected service has no reviewed source capture": "source_capture_missing",
    "Choose one available source-bound channel": "channel_selection_refused",
    "Channel delivery is disabled or its source changed": "feature_or_source_changed",
    "This channel cannot review its exact posting destination and scope": "destination_unverified",
    "This channel request already identifies different terms": "proposal_terms_conflict",
}
FIXTURE_METHODS = {"/auth.test": "auth_test", "/conversations.open": "open_dm", "/chat.postMessage": "post_message"}
DRAFT = (
    "Weekly report, 2 to 6 November\n\n"
    "- Shipped the reading list to ten percent of phones\n"
    "- Crash reports are quiet; rollout continues Thursday\n"
    "- Next: release notes, owner Jonas\n"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def core_error_category(body: bytes) -> str:
    """Map exact published Core errors to fixed labels without reporting response text."""
    if len(body) > 4096:
        return "unclassified"
    try:
        payload = json.loads(body)
    except (ValueError, RecursionError):
        return "unclassified"
    message = payload.get("error") if isinstance(payload, dict) else None
    return CORE_ERROR_CATEGORIES.get(message, "unclassified") if isinstance(message, str) else "unclassified"


def gallery_home() -> Path:
    """Refuse execution outside the toolkit's private, synthetic profile."""
    home = Path(os.environ["HOME"])
    info = home.stat()
    require(
        home == home.resolve(strict=True)
        and home.name.startswith("hz-screenshots-")
        and info.st_uid == os.getuid()
        and stat.S_ISDIR(info.st_mode)
        and stat.S_IMODE(info.st_mode) == 0o700,
        "Slack gallery requires a private toolkit home",
    )
    paths = {
        **{f"HZ_{name}": name.lower() for name in ("CONFIG_HOME", "DATA_DIR", "CACHE_DIR", "STATE_DIR", "LOG_DIR")},
        **{f"XDG_{name.upper()}_HOME": name for name in ("config", "data", "cache", "state")},
        "HZ_SYSTEM_DAEMON__UNIT_DIR": "daemon-units",
        "HZ_HEINZEL__USER_DIR": "workflows",
    }
    for key, relative in paths.items():
        path = home / relative
        require(os.environ.get(key) == str(path) and not path.is_symlink(), "Slack gallery profile path mismatch")
    require(
        os.environ.get("HZ_PLUGIN_CAPTURE_BOOTSTRAP") == str(Path(__file__).resolve())
        and os.environ.get("HZ_SYSTEM_CREDENTIAL__BACKEND") == "environment"
        and os.environ.get("HZ_UPDATE_CHECK") == "false"
        and not os.environ.get("HEINZEL_UI_RESUME"),
        "Slack gallery requires the toolkit capture environment",
    )
    return home


def fence_network(destination: tuple[str, int] | None = None) -> None:
    """Restrict Python network calls to the exact fixture listener and refuse subprocesses."""

    def audit(event: str, args: tuple) -> None:
        if event in {"subprocess.Popen", "os.exec", "os.fork", "os.posix_spawn", "os.system"}:
            raise PermissionError("Subprocesses are unavailable in the Slack gallery fixture")
        if event in {"socket.connect", "socket.sendto"} and args[1] != destination:
            raise PermissionError("Outbound network is outside the Slack gallery fixture")
        if event in {"socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr", "socket.getnameinfo"}:
            if destination is None or event != "socket.getaddrinfo" or args[:2] != destination:
                raise PermissionError("Name resolution is outside the Slack gallery fixture")

    sys.addaudithook(audit)


def run_gallery_ui(home: Path, *, smoke: bool) -> None:
    """Stage a notice with Core's private API and expose the actual installed UI."""
    from heinzel import CurrentUser
    from heinzel.heads import web
    from heinzel.kernel import boot

    token = secrets.token_urlsafe(24)
    posts: list[dict[str, Any]] = []
    rejections: list[str] = []
    requests = {name: {"attempted": 0, "accepted": 0} for name in (*FIXTURE_METHODS.values(), "other")}

    class StandIn(BaseHTTPRequestHandler):
        timeout = 2  # Bound reads even if another local process connects and sends nothing.

        def do_POST(self) -> None:
            counter = requests[FIXTURE_METHODS.get(self.path, "other")]
            counter["attempted"] += 1
            try:
                reply = self.slack_reply()
            except (RuntimeError, TypeError, ValueError):
                rejections.append("unexpected Slack request")
                reply = {"ok": False, "error": "outside_gallery_fixture"}
            else:
                counter["accepted"] += 1
            data = json.dumps(reply).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def slack_reply(self) -> dict[str, Any]:
            require(self.headers.get("Authorization") == f"Bearer {token}", "Wrong fixture transport credential")
            if self.path == "/auth.test":
                require(
                    self.headers.get_all("Content-Length") in (None, ["0"])
                    and self.headers.get_all("Transfer-Encoding") is None
                    and self.headers.get_content_type() == "application/json",
                    "Unexpected fixture auth.test framing",
                )
                return {"ok": True, "team_id": TEAM, "team": "Demo workspace", "user_id": BOT}
            size = int(self.headers.get("Content-Length", "0"))
            require(0 <= size <= 16_384, "Fixture Slack request too large")
            raw = self.rfile.read(size).decode()
            if self.headers.get("Content-Type", "").startswith("application/json"):
                body = json.loads(raw)
            else:
                body = {key: value[0] for key, value in parse_qs(raw).items()}
            require(isinstance(body, dict), "Unexpected fixture Slack body")
            if self.path == "/conversations.open" and body.get("users") == OWNER:
                return {"ok": True, "channel": {"id": DM}}
            if self.path == "/chat.postMessage" and body.get("channel") == DM and not posts:
                blocks = body.get("blocks")
                require(
                    body.get("text") == TITLE and isinstance(blocks, list) and BODY in json.dumps(blocks),
                    "Wrong notice at Slack stand-in",
                )
                posts.append(body)
                return {"ok": True, "channel": DM, "ts": "1.000100"}
            raise RuntimeError("Unexpected fixture Slack endpoint or duplicate post")

        def log_message(self, *_args: Any) -> None:
            pass  # Never print headers or request paths from the transport.

    with HTTPServer(("127.0.0.1", 0), StandIn) as server:
        fence_network(("127.0.0.1", server.server_port))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            # Core re-reads the profile when checking transport consent.
            os.environ["HZ_FEATURES"] = "connected_channels"
            kernel = boot(cwd=home)
            slack = sys.modules["heinzel_slack"]
            require(
                not kernel.errors and type(slack.__spec__.loader).__name__ == "SourceOnlyFinder",
                "Slack gallery requires installed source capture",
            )
            api_type = sys.modules["heinzel_slack._slack"].WebApi

            class LoopbackTransport:
                def api(self) -> Any:
                    return api_type(token, 2, base_url=f"http://127.0.0.1:{server.server_port}/")

                def has_tokens(self) -> tuple[bool, bool]:
                    return True, True

                def listener(self) -> None:
                    raise RuntimeError("Socket Mode is unavailable in the Slack gallery")

            kernel.bind(CurrentUser, CurrentUser(kernel.settings.state_dir / "gallery-identity"))
            kernel.bind(slack.Transport, LoopbackTransport())
            kernel.bind(slack.SlackSettings, slack.SlackSettings(owner=OWNER, team=TEAM))
            stage_notice(kernel, posts, rejections, requests, smoke=smoke)
            if not smoke:
                web.serve(kernel, port=0, browser=False, restartable=False)
        finally:
            server.shutdown()
            worker.join(timeout=2)


def stage_notice(
    kernel: Kernel,
    posts: list[dict[str, Any]],
    rejections: list[str],
    requests: dict[str, dict[str, int]],
    *,
    smoke: bool,
) -> None:
    """Use the same authenticated proposal operations and confirmation as the installed UI."""
    from fastapi.testclient import TestClient
    from heinzel.heads import web

    token = secrets.token_urlsafe(32)
    auth = {"Authorization": f"Bearer {token}"}
    with TestClient(web.build(kernel, port=8000, token=token, static=None), base_url="http://127.0.0.1:8000") as client:

        def stage(phase: str, path: str, **kwargs: Any) -> dict[str, Any]:
            response = client.post(path, headers=auth, **kwargs)
            if response.status_code != 200:
                print(
                    json.dumps(
                        {
                            "phase": phase,
                            "http_status": response.status_code,
                            "category": core_error_category(response.content),
                            "fixture_requests": requests,
                        }
                    ),
                    file=sys.stderr,
                )
                raise SystemExit(1)
            return response.json()

        created = stage("new_chat", "/api/heinzel/new-chat", json={"request_id": "gallery-session", "name": "Lotte"})
        session = created["session_id"]
        stage(
            "propose_notice",
            "/api/heinzel/propose-channel-item",
            json={"session_id": session, "request_id": NOTICE["key"], "channel": "slack", "notice": NOTICE},
        )
        chat = stage(
            "stage_review",
            "/api/system/runner/chat/propose-channel-item",
            params={"durable_session": session, "request_id": NOTICE["key"]},
        )
        require(chat["title"] == f"text {session}" and len(chat["actions"]) == 1, "Expected one recent review chat")
        action = chat["actions"][0]
        review = action["arguments"]["review"]
        require(
            action["operation"] == "deliver-channel-item"
            and action["status"] == "pending"
            and action["command"] == COMMAND
            and review["kind"] == "notice"
            and review["write_request"] is None
            and review["notice"] == {**NOTICE, "key": review["notice"]["key"]}
            and review["target"]
            == {
                "account": f"slack:{TEAM}:{BOT}",
                "destination": DM,
                "scope": f"slack:owner-dm:{OWNER}:chat.write:v1",
            }
            and not posts
            and not rejections,
            "Gallery proposal must show the exact notice and post nothing",
        )
        if not smoke:
            return
        decision = {"session": chat["id"], "action": action["id"]}
        require(
            client.post(CONFIRM, params=decision).status_code == 401 and not posts,
            "Unauthenticated gallery confirmation must be refused",
        )
        confirmed = stage("confirm_notice", CONFIRM, params=decision)
        require(
            len(posts) == 1 and not rejections and confirmed["messages"][-1]["text"] == RECEIPT,
            "Expected one exact Slack notice and the real Core delivery receipt",
        )
        require(
            client.post(CONFIRM, headers=auth, params=decision).status_code == 400
            and len(posts) == 1
            and not rejections,
            "Gallery confirmation replay must be refused before reaching Slack",
        )
    print(json.dumps({"slack_posts": 1, "unauthenticated_refused": True, "replay_refused": True}))


# Core must capture Slack before the CLI demonstration imports it directly.
if sys.argv[1:] in (["ui", "--no-browser", "--port", "0"], ["gallery-smoke"]):
    run_gallery_ui(gallery_home(), smoke=sys.argv[1:] == ["gallery-smoke"])
    raise SystemExit(0)

require(sys.argv[1:] in (["showcase", "answers"], ["showcase", "share"]), "Unknown Slack gallery command")
HOME = gallery_home()
fence_network()

from heinzel_slack import SlackChannel, SlackService, SlackSettings, draft_digest  # noqa: E402
from heinzel_slack._slack import Identity  # noqa: E402


class DemoSlack:
    """Records posts instead of sending them."""

    def __init__(self) -> None:
        self.posts: list[dict[str, Any]] = []
        self.updates: list[dict[str, Any]] = []

    def identity(self) -> Identity:
        return Identity(TEAM, "Demo workspace", "UBOT")

    def open_dm(self, user: str) -> str:
        return DM

    def post(self, channel: str, text: str, blocks: list[dict[str, Any]]) -> str:
        self.posts.append({"channel": channel, "text": text, "blocks": blocks})
        return f"1793{len(self.posts):06d}.000100"

    def update(self, channel: str, ts: str, text: str, blocks: list[dict[str, Any]]) -> None:
        self.updates.append({"channel": channel, "ts": ts, "text": text, "blocks": blocks})

    def display_name(self, user: str) -> str | None:
        return "Mira Example"


class DemoTransport:
    def __init__(self, slack: DemoSlack) -> None:
        self.slack = slack

    def api(self) -> DemoSlack:
        return self.slack

    def listener(self) -> Any:  # noqa: ANN401 - never used: clicks are handed to the service directly
        raise NotImplementedError

    def has_tokens(self) -> tuple[bool, bool]:
        return True, True


def rig() -> tuple[SlackService, SlackChannel, DemoSlack]:
    slack = DemoSlack()
    service = SlackService(
        SlackSettings(owner=OWNER, team=TEAM, approval_minutes=240),
        DemoTransport(slack),  # type: ignore[arg-type]
        Settings(state_dir=Path(os.environ["HZ_STATE_DIR"]) / "slack-demo"),
    )
    clock = [NOW]
    service.clock = lambda: clock[0]
    service.demo_clock = clock  # type: ignore[attr-defined]
    return service, SlackChannel(service), slack


def request(preview: str = DRAFT, request_id: str = "weekly-report-1") -> ChannelApprovalRequest:
    return ChannelApprovalRequest(
        request_id=request_id,
        helper="Lotte",
        action="Send the weekly report to the team",
        preview=preview,
        arguments_sha256=draft_digest(preview),
        expires_at=NOW + timedelta(hours=4),
    )


def click(service: SlackService, reference: str, *, user: str = OWNER, action: str = "hz_approve", **override: Any):
    row = service.store.get(reference)
    require(row is not None, "Expected a pending fictional Slack draft")
    payload: dict[str, Any] = {
        "type": "block_actions",
        "team": {"id": row.team},
        "user": {"id": user},
        "channel": {"id": row.channel},
        "container": {"type": "message", "channel_id": DM, "message_ts": row.message_ts},
        "message": {"ts": row.message_ts},
        "actions": [
            {
                "type": "button",
                "action_id": action,
                "value": override.pop("value", f"v1:{row.id}:{row.bound}"),
                "action_ts": f"{service.clock().timestamp():.6f}",
            }
        ],
    }
    payload.update(override)
    return payload


def draw(blocks: list[dict[str, Any]]) -> Group:
    """The message as the owner sees it in Slack, drawn from the blocks the plugin really posts."""
    lines: list[Any] = []
    for block in blocks:
        kind = block["type"]
        if kind == "header":
            lines.append(Text(block["text"]["text"], style="bold"))
        elif kind == "section":
            lines.append(Text(block["text"]["text"].replace("*", "").replace("_", "").replace(":mag: ", "")))
        elif kind == "rich_text":
            body = block["elements"][0]["elements"][0]["text"]
            lines.append(Panel(Text(body.rstrip()), border_style="grey50", padding=(0, 1)))
        elif kind == "context":
            lines.append(Text(block["elements"][0]["text"].replace("`", ""), style="dim"))
        elif kind == "actions":
            lines.append(Text("  ".join(f"[ {b['text']['text']} ]" for b in block["elements"]), style="bold cyan"))
    return Group(*lines)


showcase = Module("showcase", "Documentation-only Slack channel demonstration.")


def message_view(shown: Any) -> Panel:
    return Panel(shown, title="Slack direct message from Heinzelmännchen (demo workspace)", border_style="cyan")


@showcase.operation(render=lambda shown: message_view(shown))
def share() -> Any:
    """Share a fictional draft with Approve and Decline, as the real channel posts it."""
    _service, channel, slack = rig()
    receipt = channel.post(request())
    require(receipt.status == "delivered", "Expected one fictional Slack draft")
    return draw(slack.posts[0]["blocks"])


class Verdict(BaseModel):
    """One click and what the plugin made of it."""

    who: str = Field(description="Who pressed what.")
    verdict: str = Field(description="What the plugin did with it.")


def verdict_table(items: list[Verdict]) -> Table:
    table = Table("Click", "What the plugin did", title="Only the owner's click on this exact draft counts")
    for item in items:
        table.add_row(item.who, item.verdict)
    return table


@showcase.operation(render=verdict_table)
def answers() -> list[Verdict]:
    """Press buttons as the owner, a stranger and a replay; the real decision code answers each."""
    service, channel, _slack = rig()
    reference = str(channel.post(request()).reference)
    clock: list[datetime] = service.demo_clock  # type: ignore[attr-defined]
    out: list[Verdict] = []

    def record(who: str, payload: dict[str, Any]) -> None:
        result = service.handle(payload)
        reason = getattr(result, "reason", None)
        text = f"refused: {reason.replace('_', ' ')}" if reason else f"recorded: {result.state}"  # type: ignore[union-attr]
        out.append(Verdict(who=who, verdict=text))

    clock[0] = NOW + timedelta(minutes=5)
    record("Jonas (not the owner) presses Approve", click(service, reference, user=STRANGER))
    record("A button made for an older draft", click(service, reference, value=f"v1:{reference}:{'0' * 64}"))
    record("A typed reply 'approve' or a thumbs-up", {"type": "message", "user": OWNER, "text": "approve"})
    record("Mira presses Approve", click(service, reference))
    record("Same click again (a replay)", click(service, reference))
    sent = channel.replies([reference])
    out.append(
        Verdict(who="Host asks for replies", verdict=f"{len(sent)} reply: {sent[0].decision} by {sent[0].actor}")
    )
    late = str(channel.post(request(request_id="weekly-report-2", preview=DRAFT + "- one more line\n")).reference)
    clock[0] = NOW + timedelta(hours=5)
    record("Mira presses Approve five hours later", click(service, late))
    return out


inbox_origin = Origin("heinzel-documentation-fixture", "1.0.0", builtin=False)
configuration = Config.load(HOME)
records, errors = discover()
records.append(ModuleRecord("showcase", showcase, inbox_origin))
kernel = Kernel(configuration.settings(Settings, "hz"), records, errors, configuration)
sys.argv = ["hz", *sys.argv[1:]]
build(kernel)()
