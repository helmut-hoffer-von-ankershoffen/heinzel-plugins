"""Read fictional summary emails through the real Zoom adapter in a documentation-only requester."""

import sys
import os
from pathlib import Path
from datetime import UTC, datetime

from heinzel import (
    HeinzelError,
    Config,
    Kernel,
    MailContent,
    MailMessage,
    MailQuery,
    Meeting,
    Meetings,
    Module,
    ModuleRecord,
    Participant,
    Settings,
    Transcript,
    Window,
)
from heinzel.heads.cli import build
from heinzel.kernel import Origin, discover
from rich.console import Group
from rich.table import Table
from rich.text import Text

SINCE = datetime(2026, 10, 1, tzinfo=UTC)
UNTIL = datetime(2026, 11, 1, tzinfo=UTC)


def summary(title, decision, steps):
    return f"""Meeting summary for {title} (10/20/2026)

Hi Mira,

Quick recap

{decision}

Next steps

{steps}

Summary

Release readiness
The team checked the plan, owners and milestone.

Meeting ID: 812 3456 7890
Duration: 30 minutes
Participants: Mira Example, Jonas Example, Priya Example

AI-generated content may be inaccurate or misleading. Always check for accuracy.
Edit, share, and view the full summary in Zoom: https://us06web.zoom.us/meeting/summary/demo
"""


def email(identity, title, body, day):
    message = MailMessage(
        id=identity,
        sender=Participant(name="Zoom", email="no-reply@zoom.us"),
        recipients=[Participant(name="Mira Example", email="mira@example.com")],
        subject=f"Meeting summary for {title} (10/20/2026)",
        received_at=datetime(2026, 10, day, 9, 31, tzinfo=UTC),
        labels=["INBOX"],
    )
    if identity == "newsletter":
        message = message.model_copy(
            update={"subject": "Weekly news", "sender": Participant(name="Updates", email="updates@example.com")}
        )
    return MailContent(message=message, text=body, headers={"Date": "Tue, 20 Oct 2026 09:31:00 +0000"})


CONTENTS = {
    "sync": email(
        "sync",
        "Weekly sync",
        summary(
            "Weekly sync",
            "Ship the reading list on Thursday after the phone checks pass.",
            "- Jonas Example will update the release notes.\n- Priya Example will check the phone crash reports.\n- Mira Example will review the ten-percent rollout.",
        ),
        20,
    ),
    "launch": email(
        "launch",
        "Launch review",
        summary(
            "Launch review",
            "All readiness checks passed; begin a ten-percent rollout.",
            "- Mira Example will watch the release dashboard.\n- Jonas Example will share the API notes.",
        ),
        21,
    ),
    "newsletter": email("newsletter", "Weekly news", "Ordinary newsletter; no meeting summary sections.", 22),
}


class Mailbox:
    """Only the local demonstration mailbox; no real vendor or account can be consulted."""

    def messages(self, query, window):
        wanted = MailQuery.parse(query)
        return [
            item.message
            for item in CONTENTS.values()
            if window.since <= item.message.received_at < window.until and wanted.matches(item.message)
        ]

    def read(self, message):
        return CONTENTS[message]

    def thread(self, thread):
        raise HeinzelError("No conversations in this demonstration mailbox")

    def draft(self, draft):
        raise HeinzelError("No drafts in this demonstration mailbox")


inbox = Module("inbox", "Documentation-only fictional mailbox.")
inbox.provides("mail", name="inbox", modes={"read"}, hosts=["mail.invalid"])(Mailbox)
showcase = Module("showcase", "Documentation-only meeting-summary requester.", requires=["meetings:read"])


def summary_body(item):
    sections = [Text(item.meeting.title + " — parsed meeting summary", style="bold cyan")]
    sections.extend(Text(segment.text) for segment in item.segments)
    if item.meeting.url:
        sections.append(Text("Source: " + item.meeting.url))
    return Group(*sections)


@showcase.operation(render=summary_body)
def one(meetings: Meetings, meeting: str) -> Transcript:
    """Read one fictional summary through the real installed Zoom parser."""
    return meetings.transcript(meeting)


def meeting_table(items):
    table = Table("Meeting", "UTC start", "People")
    for item in items:
        table.add_row(
            item.title, item.started_at.strftime("%d %b %H:%M"), ", ".join(p.name or "Guest" for p in item.participants)
        )
    return table


@showcase.operation(render=meeting_table)
def ended(meetings: Meetings) -> list[Meeting]:
    """Find October's fictional summarized meetings through the real installed Zoom adapter."""
    return meetings.ended(Window(since=SINCE, until=UNTIL))


@showcase.operation
def said(meetings: Meetings) -> list[Transcript]:
    """Return parsed summary sections as typed data; these are not verbatim transcripts."""
    return meetings.transcripts(Window(since=SINCE, until=UNTIL))


CONTRACT = "---\nname: meeting-notes\nkind: responsibility\nversion: 1.0.0\ndescription: Keep decisions and next actions from the recent meeting summaries together.\nhz:\n  schema: 1\n  title: Meeting notes\n  requires: [meetings:read]\n  inputs:\n    summaries:\n      read: meetings.transcripts\n      window: 30d\n  outputs:\n    notes: {format: markdown}\n  agent:\n    tools: [Read]\n    max_usd: 0.5\n  timeout: 10m\n---\n\n# Meeting notes\n\n### Goal\n\nKeep decisions and next actions from the recent meeting summaries together.\n\n### Requires\n\n- `summaries`: fictional source data read through its installed adapter.\n\n### Maintains\n\n- `notes`: a concise local review with source links, named owners and the next checkpoint.\n\n### Done when\n\n- [ ] Each important change or decision names its source and next owner.\n\nThis contract is local demonstration data. It declares a workflow; no report has been generated.\n"
contract_folder = Path(os.environ["HZ_STATE_DIR"]) / "demonstration-contracts"
contract_folder.mkdir(parents=True, exist_ok=True)
(contract_folder / "meeting-notes.prose.md").write_text(CONTRACT)
os.environ["HZ_HEINZEL__USER_DIR"] = str(contract_folder)

configuration = Config.load()
data = {
    **configuration.data,
    "capabilities": {**configuration.data.get("capabilities", {}), "mail": "inbox", "meetings": "zoom"},
}
configuration = Config(files=configuration.files, data=data)
records, errors = discover()
origin = Origin("heinzel-documentation-fixture", "1.0.0", builtin=False)
records.extend([ModuleRecord("inbox", inbox, origin), ModuleRecord("showcase", showcase, origin)])
kernel = Kernel(configuration.settings(Settings, "hz"), records, errors, configuration)
sys.argv = ["hz", *sys.argv[1:]]
build(kernel)()
