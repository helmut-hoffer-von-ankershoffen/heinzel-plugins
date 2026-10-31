"""Real Slack, real posts. Runs only with `SLACK_PROOF=1`, the owner's member ID and both tokens in the environment.

The tokens reach the process from the official Slack CLI (`slack run` injects SLACK_BOT_TOKEN and SLACK_APP_TOKEN
and never prints them). A person must press the button; this test waits for them. Nothing here reads a token.
"""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from heinzel import ChannelApprovalRequest, ChannelNotice, Credentials, Settings
from heinzel.kernel import CredentialLet

from heinzel_slack import APP_TOKEN, BOT_TOKEN, SlackChannel, SlackService, SlackSettings, Transport, draft_digest

pytestmark = pytest.mark.e2e
LIVE = os.environ.get("SLACK_PROOF") == "1"


class Memory:
    name = "memory"

    def __init__(self, values: dict[str, str]) -> None:
        self.values = values

    def get(self, service: str, name: str) -> str | None:
        return self.values.get(name)

    def set(self, service: str, name: str, value: str) -> None:
        self.values[name] = value

    def delete(self, service: str, name: str) -> bool:
        return self.values.pop(name, None) is not None


@pytest.mark.timeout(1500)  # a person presses the button; skipped everywhere but a deliberate live run
@pytest.mark.skipif(not LIVE, reason="needs SLACK_PROOF=1, SLACK_BOT_TOKEN, SLACK_APP_TOKEN and SLACK_PROOF_OWNER")
def test_a_real_notice_and_a_real_draft(tmp_path):
    values = {"bot-token": os.environ["SLACK_BOT_TOKEN"], "app-token": os.environ["SLACK_APP_TOKEN"]}
    declared: list[tuple[str, CredentialLet]] = [("slack", BOT_TOKEN), ("slack", APP_TOKEN)]
    credentials = Credentials(Memory(values), declared)
    settings = SlackSettings(owner=os.environ["SLACK_PROOF_OWNER"], approval_minutes=30)
    service = SlackService(settings, Transport(settings, credentials), Settings(state_dir=tmp_path))
    channel = SlackChannel(service)
    assert channel.available()
    assert channel.owner_actor() == settings.owner

    sent = channel.deliver(
        ChannelNotice(
            key=f"live-{os.getpid()}",
            helper="Lotte",
            title="Hello from your Heinzelmännchen",
            body="You asked for a real message to prove the Slack channel works.",
            route="/heinzel?chat=hz-live",
        )
    )
    assert sent.status == "delivered", sent

    draft = "Weekly report\n\n- Slack channel: notices and approvals work\n- Nothing is sent until you press Approve\n"
    request = ChannelApprovalRequest(
        request_id=f"live-draft-{os.getpid()}",
        helper="Lotte",
        action="Send the weekly report",
        preview=draft,
        arguments_sha256=draft_digest(draft),
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )
    receipt = channel.post(request)
    assert receipt.status == "delivered", receipt
    marker = Path(os.environ.get("SLACK_PROOF_MARKER", tmp_path / "posted"))
    marker.write_text(f"{receipt.reference} {request.request_id}", encoding="utf-8")

    outcome = service.wait(request.request_id, float(os.environ.get("SLACK_PROOF_WAIT", "300")))
    replies = channel.replies([str(receipt.reference)])
    Path(str(marker) + ".outcome").write_text(f"{outcome.state} {outcome.approver} {outcome.approves(draft)} {replies}")
    assert outcome.state == "approved"
    assert [(r.decision, r.actor, r.arguments_sha256) for r in replies] == [
        ("approve", settings.owner, request.arguments_sha256)
    ]
    channel.settle(str(receipt.reference), "approved")
