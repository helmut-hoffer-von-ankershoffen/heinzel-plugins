"""Fixture-only Jira and Confluence requester; real parsers, no external CLI or account."""

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys

from heinzel import Config, Kernel, Module, ModuleRecord, Settings, Window
from heinzel.heads.cli import build
from heinzel.kernel import Origin, discover
from rich.table import Table
from rich.console import Group
from rich.markdown import Markdown
from rich.text import Text

SINCE = datetime(2026, 10, 1, tzinfo=UTC)
UNTIL = datetime(2026, 11, 1, tzinfo=UTC)


def issue_table(items):
    table = Table("Issue", "Title", "State", "Owner")
    for item in items:
        table.add_row(item.key, item.title, item.state, item.assignee or "Unassigned")
    return table


def document_body(item):
    return Group(
        Text(item.title, style="bold cyan"),
        Markdown(item.text),
        Text("Source: " + (item.url or item.ref)),
        Text("Revision: " + (item.revision or "unknown")),
    )


CONTRACT = '---\nname: weekly-work-review\nkind: responsibility\nversion: 1.0.0\ndescription: Review issue progress against the widget launch plan.\nhz:\n  schema: 1\n  title: Weekly work review\n  requires: [tracker:read, documents:read]\n  inputs:\n    issues:\n      read: tracker.issues_updated\n      args: {project: WID}\n      window: 30d\n    plan:\n      read: documents.read\n      args: {ref: "https://acme.atlassian.net/wiki/spaces/WID/pages/123456/Widget+plan"}\n  outputs:\n    notes: {format: markdown}\n  agent:\n    tools: [Read]\n    max_usd: 0.5\n  timeout: 10m\n---\n\n# Weekly work review\n\n### Goal\n\nReview issue progress against the widget launch plan.\n\n### Requires\n\n- `issues`: fictional source data read through its installed adapter.\n- `plan`: fictional source data read through its installed adapter.\n\n### Maintains\n\n- `notes`: a concise local review with source links, named owners and the next checkpoint.\n\n### Done when\n\n- [ ] Each important change or decision names its source and next owner.\n\nThis contract is local demonstration data. It declares a workflow; no report has been generated.\n'
contract_folder = Path(os.environ["HZ_STATE_DIR"]) / "demonstration-contracts"
contract_folder.mkdir(parents=True, exist_ok=True)
(contract_folder / "weekly-work-review.prose.md").write_text(CONTRACT)
os.environ["HZ_HEINZEL__USER_DIR"] = str(contract_folder)


def launch(requester, runner_type, runner):
    configuration = Config.load()
    records, errors = discover()
    records.append(ModuleRecord("showcase", requester, Origin("heinzel-documentation-fixture", "1.0.0", builtin=False)))
    kernel = Kernel(configuration.settings(Settings, "hz"), records, errors, configuration)
    kernel.bind(runner_type, runner)
    sys.argv = ["hz", *sys.argv[1:]]
    build(kernel)()


SEARCH = json.loads(
    '[{"expand": "renderedFields", "id": "10003", "self": "https://acme.atlassian.net/rest/api/3/issue/10003", "key": "WID-3", "fields": {"summary": "Widget export drops the last row", "status": {"name": "In Progress", "statusCategory": {"key": "indeterminate"}}, "updated": "2026-10-05T12:00:00.000+0200", "assignee": {"accountId": "5b10ac8d82e05b22cc7d4ef5", "displayName": "Wilma Widget"}, "labels": ["export", "ui"]}}, {"expand": "renderedFields", "id": "10004", "self": "https://acme.atlassian.net/rest/api/3/issue/10004", "key": "WID-4", "fields": {"summary": "Document the widget API", "status": {"name": "Done", "statusCategory": {"key": "done"}}, "updated": "2026-10-06T00:00:00.000+0000", "assignee": null, "labels": []}}]'
)
PAGE = json.loads(
    '{"id": "123456", "status": "current", "title": "Widget plan", "spaceId": "98304", "parentId": "98305", "authorId": "5b10ac8d82e05b22cc7d4ef5", "createdAt": "2026-09-01T08:00:00.000Z", "version": {"number": 3, "message": "", "minorEdit": false, "authorId": "5b10ac8d82e05b22cc7d4ef5"}, "body": {"storage": {"representation": "storage", "value": "<h1>Widget launch plan</h1><p>Ship reliable widgets without losing export data.</p><h2>Scope</h2><ul><li>Mira: fix the export boundary.</li><li>Jonas: document the widget API.</li><li>Priya: verify dark-mode screenshots.</li></ul><h2>Next milestone</h2><p>Release review on Tuesday after all three checks pass.</p>"}}, "_links": {"webui": "/spaces/WID/pages/123456/Widget+plan", "base": "https://acme.atlassian.net/wiki"}}'
)

from heinzel import Tracker, Documents, Issue, Document
from heinzel_atlassian import Acli, Completed


class DemoAcli(Acli):
    def __init__(self):
        pass

    def path(self):
        return "/fixture/never-executed-acli"

    def version(self):
        return (1, 3, 39)

    def run(self, args, timeout):
        command = tuple(args[:3])
        if command == ("jira", "workitem", "search"):
            value = SEARCH
        elif command == ("jira", "workitem", "view"):  # search lists the keys; view reads each one's `updated`
            value = next(item for item in SEARCH if item["key"] == args[3])
        elif command == ("confluence", "page", "view"):
            value = PAGE
        else:
            raise ValueError("Unexpected vendor request in the offline demonstration")
        return Completed(0, json.dumps(value).encode(), b"", overflow=False)


showcase = Module(
    "showcase",
    "Documentation-only Atlassian requester: fictional data, real adapters.",
    requires=["tracker:read", "documents:read"],
)


@showcase.operation(render=issue_table)
def issues(tracker: Tracker, project: str) -> list[Issue]:
    """Read the fictional project's October issue changes through the real Jira adapter."""
    return tracker.issues_updated(project, Window(since=SINCE, until=UNTIL))


@showcase.operation(render=document_body)
def page(documents: Documents) -> Document:
    """Read the fictional Widget plan through the real Confluence adapter."""
    return documents.read("https://acme.atlassian.net/wiki/spaces/WID/pages/123456/Widget+plan")


os.environ["HZ_ATLASSIAN__SITE_URL"] = "https://acme.atlassian.net"
os.environ["HZ_CAPABILITIES__TRACKER"] = "atlassian"
os.environ["HZ_CAPABILITIES__DOCUMENTS"] = "atlassian"
launch(showcase, Acli, DemoAcli())
