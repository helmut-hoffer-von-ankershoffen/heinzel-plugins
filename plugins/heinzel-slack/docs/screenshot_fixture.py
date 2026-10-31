"""Show the real Slack channel code against a documentation-only Slack: fictional people, no workspace, no token.

The decision code, the message builders and the store are the plugin's own. Only Slack is replaced by `DemoSlack`,
which records what would be posted. Nothing here can reach a real workspace.
"""

import os
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from heinzel import ChannelApprovalRequest, Config, Kernel, Module, ModuleRecord, Settings
from heinzel.heads.cli import build
from heinzel.kernel import Origin, discover
from pydantic import BaseModel, Field
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from heinzel_slack import SlackChannel, SlackService, SlackSettings, draft_digest
from heinzel_slack._slack import Identity

os.environ.setdefault("TZ", "Europe/Berlin")
time.tzset()
NOW = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
OWNER, STRANGER, TEAM, DM = "U0MIRA0001", "U0JONAS002", "T0DEMO0001", "D0DEMO0001"
DRAFT = (
    "Weekly report, 2 to 6 November\n\n"
    "- Shipped the reading list to ten percent of phones\n"
    "- Crash reports are quiet; rollout continues Thursday\n"
    "- Next: release notes, owner Jonas\n"
)


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
    assert row is not None
    payload: dict[str, Any] = {
        "type": "block_actions",
        "team": {"id": row.team},
        "user": {"id": user},
        "channel": {"id": row.channel},
        "container": {"message_ts": row.message_ts},
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
    assert receipt.status == "delivered"
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
    out.append(Verdict(who="Host asks for replies", verdict=f"{len(sent)} reply: {sent[0].decision} by {sent[0].actor}"))
    late = str(channel.post(request(request_id="weekly-report-2", preview=DRAFT + "- one more line\n")).reference)
    clock[0] = NOW + timedelta(hours=5)
    record("Mira presses Approve five hours later", click(service, late))
    return out


inbox_origin = Origin("heinzel-documentation-fixture", "1.0.0", builtin=False)
configuration = Config.load()
records, errors = discover()
records.append(ModuleRecord("showcase", showcase, inbox_origin))
kernel = Kernel(configuration.settings(Settings, "hz"), records, errors, configuration)
sys.argv = ["hz", *sys.argv[1:]]
build(kernel)()
