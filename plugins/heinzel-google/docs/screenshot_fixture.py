"""Documentation-only Workspace requester with real adapter conversions and fictional vendor replies."""

import base64
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from heinzel import (
    Calendar,
    Config,
    Document,
    Documents,
    Event,
    Kernel,
    Mail,
    MailContent,
    MailMessage,
    Module,
    ModuleRecord,
    Settings,
    Window,
)
from heinzel.heads.cli import build
from heinzel.kernel import Origin, discover
from heinzel_google import Gws, Process
from rich.console import Group
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text

SINCE = datetime(2026, 10, 19, tzinfo=UTC)
UNTIL = datetime(2026, 10, 26, tzinfo=UTC)
DOC = "launch-plan"
SHEET = "launch-metrics"
DOCUMENT = "application/vnd.google-apps.document"
SPREADSHEET = "application/vnd.google-apps.spreadsheet"


def paragraph(text, style="NORMAL_TEXT"):
    return {
        "paragraph": {"elements": [{"textRun": {"content": text + "\n"}}], "paragraphStyle": {"namedStyleType": style}}
    }


def message(identity):
    title = "Launch readiness: three checks left" if identity == "m1" else "Launch review: agenda and owners"
    body = (
        "Mira: verify the export boundary. Jonas: publish the API notes. Priya: check phone screenshots."
        if identity == "m1"
        else "Review the launch metrics on Thursday. Bring the three readiness checks and the rollout plan."
    )
    return {
        "id": identity,
        "threadId": "t" + identity,
        "internalDate": str(int(datetime(2026, 10, 20 if identity == "m1" else 21, 10, tzinfo=UTC).timestamp() * 1000)),
        "labelIds": ["INBOX"],
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "Launch updates <updates@example.com>"},
                {"name": "To", "value": "Mira Example <mira@example.com>"},
                {"name": "Subject", "value": title},
            ],
            "body": {"data": base64.urlsafe_b64encode(body.encode()).decode()},
        },
    }


class DemoGws(Gws):
    def run(self, executable, arguments, timeout):
        command = tuple(arguments[: arguments.index("--params")]) if "--params" in arguments else tuple(arguments)
        params = json.loads(arguments[arguments.index("--params") + 1]) if "--params" in arguments else {}
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        if command == ("--version",):
            return Process(0, b"gws 0.22.5\n")
        if command == ("drive", "files", "list"):
            value = {
                "files": [
                    {"id": DOC, "name": "Launch plan", "mimeType": DOCUMENT, "modifiedTime": now},
                    {"id": SHEET, "name": "Launch metrics", "mimeType": SPREADSHEET, "modifiedTime": now},
                    {
                        "id": "launch-readiness",
                        "name": "Launch readiness checklist",
                        "mimeType": DOCUMENT,
                        "modifiedTime": now,
                    },
                ]
            }
        elif command == ("drive", "files", "get"):
            file_id = params["fileId"]
            value = {
                "id": file_id,
                "name": "Launch metrics" if file_id == SHEET else "Launch plan",
                "mimeType": SPREADSHEET if file_id == SHEET else DOCUMENT,
                "version": "42",
            }
        elif command == ("docs", "documents", "get"):
            value = {
                "documentId": DOC,
                "title": "Launch plan",
                "revisionId": "demo-rev-7",
                "body": {
                    "content": [
                        paragraph("Launch plan", "TITLE"),
                        paragraph("Goal", "HEADING_2"),
                        paragraph("Ship reliable widgets with a measured rollout."),
                        paragraph("Owners and next checks", "HEADING_2"),
                        paragraph("Mira: export boundary. Jonas: API notes. Priya: phone screenshots."),
                        paragraph("Next milestone", "HEADING_2"),
                        paragraph("Thursday launch review, then a ten-percent rollout."),
                    ]
                },
            }
        elif command == ("sheets", "spreadsheets", "get"):
            rows = [
                ["Release check", "Target", "Observed"],
                ["Export rows", "100% retained", "100%"],
                ["Phone screenshots", "6 layouts", "6 passed"],
                ["Crash-free sessions", "99.9%", "99.95%"],
            ]
            value = {
                "properties": {"title": "Launch metrics"},
                "sheets": [
                    {
                        "properties": {"title": "Readiness", "sheetType": "GRID"},
                        "data": [{"rowData": [{"values": [{"formattedValue": v} for v in row]} for row in rows]}],
                    }
                ],
            }
        elif command == ("calendar", "events", "list"):
            value = {
                "timeZone": "Europe/Berlin",
                "items": [
                    {
                        "id": "launch-review",
                        "summary": "Launch readiness review",
                        "start": {"dateTime": "2026-10-22T13:00:00Z"},
                        "end": {"dateTime": "2026-10-22T13:30:00Z"},
                        "attendees": [
                            {"displayName": "Mira Example", "email": "mira@example.com"},
                            {"displayName": "Jonas Example", "email": "jonas@example.com"},
                        ],
                    },
                    {
                        "id": "one-on-one",
                        "summary": "Mira Example / Priya Example — one-on-one",
                        "start": {"dateTime": "2026-10-23T09:00:00Z"},
                        "end": {"dateTime": "2026-10-23T09:30:00Z"},
                        "attendees": [{"displayName": "Priya Example", "email": "priya@example.com"}],
                    },
                    {
                        "id": "rollout",
                        "summary": "Rollout checkpoint",
                        "start": {"dateTime": "2026-10-23T14:00:00Z"},
                        "end": {"dateTime": "2026-10-23T14:20:00Z"},
                    },
                ],
            }
        elif command == ("gmail", "users", "messages", "list"):
            value = {"messages": [{"id": "m1"}, {"id": "m2"}]}
        elif command == ("gmail", "users", "messages", "get"):
            value = message(params["id"])
        elif command == ("gmail", "users", "labels", "list"):
            value = {"labels": [{"id": "INBOX", "name": "INBOX"}]}
        else:
            raise ValueError("Unexpected vendor request in the offline demonstration")
        return Process(0, json.dumps(value).encode())


showcase = Module(
    "showcase",
    "Documentation-only Workspace requester with fictional content.",
    requires=["documents:read", "calendar:read", "mail:read"],
)


def document_body(item):
    return Group(
        Text(item.title, style="bold cyan"),
        Markdown(item.text),
        Text("Source: " + item.url),
        Text("Revision: " + (item.revision or "unknown")),
    )


@showcase.operation(render=document_body)
def notes(documents: Documents, ref: str) -> Document:
    """Read a fictional plan or metric sheet through the installed Google documents adapter."""
    return documents.read(ref)


def calendar_table(items):
    table = Table("UTC start", "Meeting", "People")
    for item in items:
        table.add_row(item.start.strftime("%a %H:%M"), item.title, ", ".join(p.name or "Guest" for p in item.attendees))
    return table


@showcase.operation(render=calendar_table)
def week(calendar: Calendar) -> list[Event]:
    """Read the fictional launch week's meetings through the installed Google calendar adapter."""
    return calendar.events(Window(since=SINCE, until=UNTIL))


def inbox_table(items):
    table = Table("Received", "Subject", "Sender")
    for item in items:
        table.add_row(item.received_at.strftime("%d %b"), item.subject, item.sender.name or "Launch updates")
    return table


@showcase.operation(render=inbox_table)
def inbox(mail: Mail) -> list[MailMessage]:
    """Read a focused fictional launch query through the installed Gmail adapter."""
    return mail.messages("from:updates@example.com subject:Launch", Window(since=SINCE, until=UNTIL))


def mail_body(item):
    return Group(Text(item.message.subject, style="bold cyan"), Text(item.text))


@showcase.operation(render=mail_body)
def message_content(mail: Mail) -> MailContent:
    """Read the fictional launch message body through the real Gmail adapter."""
    return mail.read("m1")


state = Path(os.environ["HZ_STATE_DIR"]) / "fictional-gws"
state.mkdir(parents=True, exist_ok=True)
(state / "credentials.enc").write_bytes(b"documentation-only-no-credential")
(state / "client_secret.json").write_text("{}")
executable = state / "gws"
executable.write_text("#!/bin/sh\nexit 99\n")
executable.chmod(0o700)
os.environ.update(
    GOOGLE_WORKSPACE_CLI_CONFIG_DIR=str(state),
    HZ_GOOGLE__GWS_PATH=str(executable),
    HZ_CAPABILITIES__DOCUMENTS="google",
    HZ_CAPABILITIES__CALENDAR="google",
    HZ_CAPABILITIES__MAIL="google",
)
config = Config.load()
records, errors = discover()
records.append(ModuleRecord("showcase", showcase, Origin("heinzel-documentation-fixture", "1.0.0", builtin=False)))
kernel = Kernel(config.settings(Settings, "hz"), records, errors, config)
kernel.bind(Gws, DemoGws())
sys.argv = ["hz", *sys.argv[1:]]
build(kernel)()
