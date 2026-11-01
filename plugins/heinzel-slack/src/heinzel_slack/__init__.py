"""Tell the owner what needs them, and ask for approval of an exact draft, in their own Slack direct message.

A Heinzelmännchen plugin that registers one channel, `slack`, for core's two ports (ADR 0112): a
`NotificationChannel` for notices and an `ApprovalChannel` for drafts with Approve and Decline. It uses the owner's own
private Slack app (installed from `hz slack manifest`), posts only to the owner's direct message with it, and counts
one thing as an answer: the owner pressing a button on the message that carries the exact draft. The host decides
what an answer is worth; see the README.
"""

import secrets
from datetime import timedelta
from pathlib import Path

from heinzel import (
    ChannelApprovalRequest,
    ChannelNotice,
    ChannelReceipt,
    Check,
    ConfigEditor,
    HeinzelError,
    Prompter,
)
from pydantic import JsonValue

from heinzel_slack._channel import SlackChannel
from heinzel_slack._decide import APPROVE, DECLINE
from heinzel_slack._digest import MAX_DRAFT, check_draft, draft_digest
from heinzel_slack._models import DraftStanding, SharedDraft
from heinzel_slack._module import module
from heinzel_slack._service import About, Listened, SlackService, slot
from heinzel_slack._settings import SlackSettings
from heinzel_slack._slack import APP_TOKEN, BOT_TOKEN, Transport

module.settings(SlackSettings)
module.service(Transport)
module.service(SlackService)
module.service(SlackChannel)


@module.operation
def info(service: SlackService) -> About:
    """Show this plugin's version, the Heinzelmännchen it runs on, and how far Slack is set up (never a token)."""
    return service.about()


@module.info
def system_info(service: SlackService) -> About:
    """Contribute this plugin's details to `hz system info`."""
    return service.about()


@module.operation
def manifest() -> str:
    """Print the Slack app manifest: paste it at api.slack.com/apps (Create New App, From a manifest)."""
    return (Path(__file__).parent / "manifest.json").read_text(encoding="utf-8")


@module.operation(read_only=False, private=True)
def notify(channel: SlackChannel, title: str, reason: str, helper: str = "", route: str = "") -> ChannelReceipt:
    """Tell the owner something in Slack; the reason is shown as why they are being told.

    Raises:
        HeinzelError: If the title or reason is empty.
    """
    if not title.strip() or not reason.strip():
        msg = "A notification needs a title and the reason the person is being told"
        raise HeinzelError(msg)
    notice = ChannelNotice(
        key=secrets.token_hex(16), helper=helper.strip() or "Heinzel", title=title.strip()[:120],
        body=reason.strip()[:500], route=route,
    )  # fmt: skip
    return channel.deliver(notice)


@module.operation(read_only=False, private=True)
def ask(service: SlackService, channel: SlackChannel, action: str, draft: str, helper: str = "") -> SharedDraft:
    """Share a draft in Slack with Approve and Decline; the answer is bound to these exact bytes and to the owner.

    Nothing is approved by this call; `wait` or `status` report the owner's answer.

    Raises:
        HeinzelError: If the draft cannot be reviewed as it is, or Slack is not set up or refuses.
    """
    check_draft(draft)
    expires = service.clock() + timedelta(minutes=service.settings.approval_minutes)
    request = ChannelApprovalRequest(
        request_id=secrets.token_hex(16), helper=helper.strip() or "Heinzel", action=action.strip()[:100] or "A draft",
        preview=draft, arguments_sha256=draft_digest(draft), expires_at=expires,
    )  # fmt: skip
    receipt = channel.post(request)
    if receipt.status != "delivered":
        msg = f"The draft was not shared ({receipt.status}): {receipt.detail or 'no reason given'}"
        raise HeinzelError(msg)
    return SharedDraft(
        request_id=request.request_id, digest=request.arguments_sha256, state="pending", expires_at=expires
    )


@module.operation
def status(service: SlackService, request_id: str) -> DraftStanding:
    """Where a shared draft stands: waiting, approved, declined, expired or replaced.

    Raises:
        HeinzelError: If there is no such request.
    """
    return service.outcome(request_id)


@module.operation(read_only=False, private=True)
def wait(service: SlackService, request_id: str, seconds: float = 120.0) -> DraftStanding:
    """Listen for the owner's click on a shared draft, up to `seconds`, and report where it stands.

    Raises:
        HeinzelError: If Slack is not set up or there is no such request.
    """
    return service.wait(request_id, seconds)


@module.operation(read_only=False, private=True)
def listen(service: SlackService, seconds: float = 300.0) -> Listened:
    """Answer clicks on any waiting draft for `seconds`; clicks are only registered while something listens.

    Raises:
        HeinzelError: If Slack is not set up.
    """
    return service.listen(seconds)


@module.job(schedule="*/5 * * * *", name="listen", timeout="5m")
def listen_job(service: SlackService) -> JsonValue:
    """Every five minutes, listen for four when a draft is waiting for its owner's click; otherwise do nothing."""
    if not service.usable() or not service.store.pending():
        return {"listened": False}
    return {"listened": True, **service.listen(240).model_dump(mode="json")}


@module.health
def ready(service: SlackService) -> list[Check]:
    """Owner and both tokens are set; nothing is asked of Slack."""
    return service.checks()


@module.health(live=True)
def live(service: SlackService) -> list[Check]:
    """Ask Slack who the bot is and whose direct message gets the drafts; two reads, nothing posted."""
    return service.live()


@module.setup(required=False)
def setup(settings: SlackSettings, prompter: Prompter, editor: ConfigEditor) -> None:
    """Say whose Slack this is; the two tokens are stored with `hz system credential set`."""
    owner = prompter.text("Your Slack member ID (profile, three dots, Copy member ID)", default=settings.owner)
    path = editor.write("slack.owner", owner.strip())
    prompter.say(f"Saved to {path}. Create the app with `hz slack manifest`, then store its two tokens:")
    prompter.say("  hz system credential set bot-token --service slack   (xoxb-..., from Install App)")
    prompter.say("  hz system credential set app-token --service slack   (xapp-..., scope connections:write)")


__all__ = [
    "APPROVE",
    "APP_TOKEN",
    "BOT_TOKEN",
    "DECLINE",
    "MAX_DRAFT",
    "About",
    "DraftStanding",
    "Listened",
    "SharedDraft",
    "SlackChannel",
    "SlackService",
    "SlackSettings",
    "Transport",
    "check_draft",
    "draft_digest",
    "module",
    "slot",
]
