"""The Slack channel: core's notification and approval ports (ADR 0112), carried by the service.

A channel carries words and never decides. `replies` returns only clicks that passed every check in `_decide`, and
the host checks them again against the exact pending request before it consumes any approval.
"""

from collections.abc import Sequence
from typing import Literal

from heinzel import (
    ApprovalChannel,
    ChannelApprovalReply,
    ChannelApprovalRequest,
    ChannelNotice,
    ChannelReceipt,
    NotificationChannel,
)

from heinzel_slack._service import CHANNEL, SlackService


class SlackChannel(NotificationChannel, ApprovalChannel):
    """Notices and approvals in the owner's own Slack direct message."""

    name = CHANNEL

    def __init__(self, service: SlackService) -> None:
        """Wrap the service; nothing is sent."""
        self._service = service

    def available(self) -> bool:
        """Owner set and both tokens stored; the network is not asked."""
        return self._service.usable()

    def owner_actor(self) -> str | None:
        """The owner's Slack member ID from the plugin's settings, or None until Slack is set up."""
        return self._service.settings.owner if self._service.usable() else None

    def deliver(self, notice: ChannelNotice) -> ChannelReceipt:
        """Post one notice, at most once per key."""
        return self._service.deliver(notice)

    def post(self, request: ChannelApprovalRequest) -> ChannelReceipt:
        """Share one request with Approve and Decline; its reference is what `replies` and `settle` take."""
        return self._service.post(request)

    def replies(self, references: Sequence[str]) -> list[ChannelApprovalReply]:
        """Decisions the owner pressed on these requests."""
        return self._service.replies(references)

    def settle(self, reference: str, outcome: Literal["approved", "declined", "expired", "superseded"]) -> None:
        """Close a request's message."""
        self._service.settle(reference, outcome)
