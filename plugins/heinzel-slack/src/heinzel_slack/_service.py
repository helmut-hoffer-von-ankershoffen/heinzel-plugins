"""The engine behind the channel: deliver a notice, share a draft, bring back an exact, owner-bound answer."""

import hashlib
import threading
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Literal, cast

from heinzel import (
    ChannelApprovalReply,
    ChannelApprovalRequest,
    ChannelNotice,
    ChannelReceipt,
    Check,
    HeinzelError,
    Settings,
    Status,
    __version__,
    clean_text,
)
from pydantic import BaseModel, Field

from heinzel_slack import _blocks
from heinzel_slack._decide import Decided, Denied, decide
from heinzel_slack._digest import check_draft, draft_digest
from heinzel_slack._models import DECIDED, DraftStanding, State
from heinzel_slack._settings import SlackSettings
from heinzel_slack._slack import Listener, SlackApi, SlackRefused, Transport
from heinzel_slack._store import Row, Store

DISTRIBUTION = "heinzel-slack"
CHANNEL = "slack"
Outcome = Literal["approved", "declined", "expired", "superseded"]


class About(BaseModel):
    """What this plugin is and how far it is set up; never a token."""

    plugin: str = Field(description="Distribution name.")
    version: str = Field(description="Installed version.")
    heinzel_version: str = Field(description="Version of the Heinzelmännchen it runs in.")
    owner: str = Field(description="Slack member ID drafts go to; empty if not set.")
    bot_token: bool = Field(description="Whether a bot token is stored.")
    app_token: bool = Field(description="Whether an app-level token is stored.")
    pending: int = Field(description="Shared drafts still waiting for an answer.")


class Listened(BaseModel):
    """What a listening pass saw."""

    approved: int = Field(description="Requests approved by their owner.")
    declined: int = Field(description="Requests declined by their owner.")
    refused: int = Field(description="Clicks that were not an answer; each is in the audit trail.")


def slot(request_id: str) -> str:
    """The identifier this plugin gives a host request: stable, so posting twice is one request."""
    return hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:32]


class SlackService:
    """Posts to the owner's direct message and turns their clicks into exact, bound decisions."""

    def __init__(self, settings: SlackSettings, transport: Transport, hz: Settings) -> None:
        """Create the service; nothing is read or sent."""
        self._settings = settings
        self._transport = transport
        self._directory = hz.state_dir / "slack"
        self._store: Store | None = None
        self.clock: Callable[[], datetime] = lambda: datetime.now(UTC)
        self._lock = threading.Lock()
        self._counts = {"approved": 0, "declined": 0, "refused": 0}

    @property
    def store(self) -> Store:
        """The request store, created on first use."""
        if self._store is None:
            self._store = Store(self._directory)
        return self._store

    @property
    def settings(self) -> SlackSettings:
        """The plugin's settings."""
        return self._settings

    def usable(self) -> bool:
        """Whether an owner is set and both tokens are stored; no network."""
        bot, app = self._transport.has_tokens()
        return bool(self._settings.owner) and bot and app

    def about(self) -> About:
        """Describe the plugin and its setup."""
        try:
            installed = version(DISTRIBUTION)
        except PackageNotFoundError:  # pragma: no cover - only from an uninstalled source tree
            installed = "0.0.0"
        bot, app = self._transport.has_tokens()
        return About(
            plugin=DISTRIBUTION, version=installed, heinzel_version=__version__, owner=self._settings.owner,
            bot_token=bot, app_token=app, pending=len(self.store.pending()),
        )  # fmt: skip

    # --- notices ---------------------------------------------------------

    def deliver(self, notice: ChannelNotice) -> ChannelReceipt:
        """Post one notice to the owner's DM at most once per key; never raises for a delivery failure."""
        try:
            api, channel, _team = self._ready()
        except HeinzelError as error:
            return _receipt("refused", None, str(error))
        if not self.store.begin_delivery(notice.key, self.clock()):
            known = self.store.delivery(notice.key)
            if known and known[0] == "delivered":
                return _receipt("delivered", known[1], "already sent")
            return _receipt("unknown", known[1] if known else None, "an earlier attempt may have been sent")
        text, blocks = _blocks.notification(notice.helper, notice.title, notice.body, notice.route)
        try:
            ts = api.post(channel, text, blocks)
        except SlackRefused as error:
            self.store.forget_delivery(notice.key)
            return _receipt("refused", None, str(error))
        except HeinzelError as error:
            self.store.end_delivery(notice.key, "unknown", None)
            return _receipt("unknown", None, str(error))
        self.store.end_delivery(notice.key, "delivered", f"{channel}:{ts}")
        return _receipt("delivered", f"{channel}:{ts}", None)

    # --- approvals -------------------------------------------------------

    def post(self, request: ChannelApprovalRequest) -> ChannelReceipt:  # noqa: PLR0911 - one return per receipt kind
        """Share one request in the owner's DM, bound to its digest and expiry; idempotent by request id."""
        now = self.clock()
        if request.expires_at <= now:
            return _receipt("refused", None, "the request has already expired")
        try:
            check_draft(request.preview)
            api, channel, team = self._ready()
        except HeinzelError as error:
            return _receipt("refused", None, str(error))
        row = Row(
            id=slot(request.request_id), external=request.request_id, owner=self._settings.owner, team=team,
            channel=channel, message_ts="", bound=request.arguments_sha256, digest=draft_digest(request.preview),
            draft=request.preview, action=clean_text(request.action)[:150], helper=clean_text(request.helper)[:40],
            state="posting", created_at=now, expires_at=request.expires_at, decided_at=None, decided_by=None,
            detail="",
        )  # fmt: skip
        known = self.store.insert(row)
        if known is not None:
            if known.bound != row.bound or known.digest != row.digest:
                return _receipt("refused", None, "this request id was already used for different arguments")
            if known.state == "posting":
                return _receipt("unknown", None, "an earlier attempt may have been posted")
            return _receipt("delivered" if known.state != "failed" else "refused", known.id, f"already {known.state}")
        try:
            text, blocks = _blocks.approval(
                row.id, row.bound, row.action, row.helper, request.preview, request.link, row.expires_at
            )
            ts = api.post(channel, text, blocks)
        except SlackRefused as error:
            self.store.failed(row.id, "refused", self.clock())
            return _receipt("refused", None, str(error))
        except HeinzelError as error:
            return _receipt("unknown", None, str(error))
        self.store.posted(row.id, ts, self.clock())
        return _receipt("delivered", row.id, None)

    def replies(self, references: Sequence[str]) -> list[ChannelApprovalReply]:
        """The owner's decisions on these posted requests, oldest first: only clicks that passed every check."""
        self._expire_quietly()
        rows = [r for r in (self.store.get(ref) for ref in references) if r and r.state in DECIDED and r.decided_at]
        return [
            ChannelApprovalReply(
                request_id=row.external,
                arguments_sha256=row.bound,
                decision="approve" if row.state == "approved" else "decline",
                actor=row.owner,
                at=cast("datetime", row.decided_at),
            )
            for row in sorted(rows, key=lambda r: r.decided_at or r.created_at)
        ]

    def settle(self, reference: str, outcome: Outcome) -> None:
        """Mark a posted request as no longer open, best effort."""
        row = self.store.get(reference)
        if row is None:
            return
        if outcome in {"expired", "superseded"}:
            self.store.mark(row.id, outcome, self.clock())
        try:
            self._settle(self._transport.api(), self.store.get(reference) or row, outcome)
        except HeinzelError:
            self.store.deny(row.id, "message_not_updated", self.clock())

    def outcome(self, request_id: str, *, now: datetime | None = None) -> DraftStanding:
        """Where a request (by the id the host or `ask` gave) stands; applies expiry first.

        Raises:
            HeinzelError: If there is no such request.
        """
        self._expire_quietly(now)
        row = self.store.by_external(request_id)
        if row is None:
            msg = "There is no such approval request"
            raise HeinzelError(msg)
        decided = row.state in DECIDED
        return DraftStanding(
            request_id=row.external, state=cast("State", row.state), digest=row.bound,
            approver=row.decided_by if decided else None, decided_at=row.decided_at if decided else None,
            detail=_DETAIL[row.state],
        )  # fmt: skip

    def wait(self, request_id: str, seconds: float) -> DraftStanding:
        """Listen for clicks until `request_id` is decided or `seconds` pass, then say where it stands."""
        deadline = time.monotonic() + max(0.0, seconds)
        listener = self._listen_start()
        try:
            while True:
                result = self.outcome(request_id)
                if result.state != "pending" or time.monotonic() >= deadline:
                    return result
                time.sleep(0.2)
        finally:
            listener.stop()

    def listen(self, seconds: float) -> Listened:
        """Answer clicks on pending drafts for up to `seconds`, and stop early once none is waiting."""
        self._counts.update({"approved": 0, "declined": 0, "refused": 0})
        deadline = time.monotonic() + max(0.0, seconds)
        listener = self._listen_start()
        try:
            while time.monotonic() < deadline:
                self._expire_quietly()
                if not self.store.pending():
                    break
                time.sleep(0.2)
        finally:
            listener.stop()
        return Listened(**self._counts)

    def _listen_start(self) -> Listener:
        self._ready()
        listener = self._transport.listener()
        listener.start(self._on_payload)
        return listener

    def _on_payload(self, payload: dict[str, Any]) -> None:
        self.handle(payload)

    def handle(self, payload: object) -> Decided | Denied:
        """Treat one Slack interactive payload: decide it, record it, and mark the message answered."""
        now = self.clock()
        with self._lock:
            result = decide(self.store, payload, now)
            if isinstance(result, Denied):
                self.store.deny(result.request_id or "-", result.reason, now)
                self._counts["refused"] += 1
            else:
                self._counts[result.state] += 1
        if isinstance(result, Decided):
            row = self.store.get(result.request_id)
            if row is not None:
                try:
                    self._settle(self._transport.api(), row, f"answered_{result.state}")
                except HeinzelError:
                    self.store.deny(row.id, "message_not_updated", now)
        elif result.reason == "expired":
            self._expire_quietly()
        return result

    # --- internals -------------------------------------------------------

    def _ready(self) -> tuple[SlackApi, str, str]:
        owner = self._settings.owner
        if not owner:
            msg = "No Slack owner is set; run `hz setup slack` or `hz system config set slack.owner U01ABCDEF`"
            raise HeinzelError(msg)
        api = self._transport.api()
        who = api.identity()
        if self._settings.team and who.team_id != self._settings.team:
            msg = "The bot token belongs to another workspace than slack.team; refusing to post"
            raise HeinzelError(msg)
        return api, api.open_dm(owner), who.team_id

    def _expire_quietly(self, now: datetime | None = None) -> None:
        expired = self.store.expire_due(now or self.clock())
        if not expired:
            return
        try:
            api = self._transport.api()
        except HeinzelError:
            return
        for row in expired:
            try:
                self._settle(api, row, "expired")
            except HeinzelError:
                self.store.deny(row.id, "message_not_updated", self.clock())

    def _settle(self, api: SlackApi, row: Row, state: str) -> None:
        # The decision is already recorded; failing to edit the message must not undo or hide it.
        at = row.decided_at or self.clock()
        text, blocks = _blocks.settled(state, row.action, row.draft, row.bound, at)
        api.update(row.channel, row.message_ts, text, blocks)

    def checks(self) -> list[Check]:
        """Whether Slack is set up; never a request to Slack."""
        bot, app = self._transport.has_tokens()
        owner = self._settings.owner
        return [
            Check(
                name="owner",
                status=Status.UP if owner else Status.DEGRADED,
                detail=f"drafts go to {owner}" if owner else "no Slack member ID set",
                fix="" if owner else "hz system config set slack.owner U01ABCDEF",
            ),
            Check(
                name="bot token",
                status=Status.UP if bot else Status.DEGRADED,
                detail="stored" if bot else "not stored; posting needs the app's bot token",
                fix="" if bot else "hz system credential set bot-token --service slack",
            ),
            Check(
                name="app token",
                status=Status.UP if app else Status.DEGRADED,
                detail="stored" if app else "not stored; button clicks need the app-level token",
                fix="" if app else "hz system credential set app-token --service slack",
            ),
        ]

    def live(self) -> list[Check]:
        """Ask Slack who the bot token is and who it would write to: two reads, nothing posted."""
        try:
            api = self._transport.api()
            who = api.identity()
            name = api.display_name(self._settings.owner) if self._settings.owner else None
        except HeinzelError as error:
            return [Check(name="auth.test", status=Status.DOWN, detail=str(error), fix="hz slack manifest")]
        shown = f"{clean_text(name)} ({self._settings.owner})" if name else self._settings.owner or "nobody yet"
        return [
            Check(name="auth.test", status=Status.UP, detail=f"workspace {clean_text(who.team)} ({who.team_id})"),
            Check(name="drafts go to", status=Status.UP, detail=shown),
        ]


_DETAIL: dict[str, str] = {
    "posting": "The draft is being posted; it cannot be approved yet.",
    "pending": "Waiting for the owner to click Approve or Decline.",
    "approved": "The owner approved exactly this draft.",
    "declined": "The owner declined this draft.",
    "expired": "No answer in time. This is not an approval.",
    "superseded": "A newer draft replaced this one. This is not an approval.",
    "failed": "The draft never reached Slack. This is not an approval.",
}


def _receipt(
    status: Literal["delivered", "queued", "refused", "unknown"], reference: str | None, detail: str | None
) -> ChannelReceipt:
    return ChannelReceipt(
        channel=CHANNEL, status=status, reference=reference, detail=clean_text(detail)[:200] if detail else None
    )
