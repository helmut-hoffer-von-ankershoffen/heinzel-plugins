"""Fixture-only capability requester; real GitHub conversions over fictional vendor responses."""

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


CONTRACT = "---\nname: weekly-code-review\nkind: responsibility\nversion: 1.0.0\ndescription: Review merged work and issue changes, with owners and source links.\nhz:\n  schema: 1\n  title: Weekly code review\n  requires: [code-host:read, tracker:read]\n  inputs:\n    merged:\n      read: code-host.merged_pull_requests\n      args: {repository: acme/widgets}\n      window: 30d\n    issues:\n      read: tracker.issues_updated\n      args: {project: acme/widgets}\n      window: 30d\n  outputs:\n    notes: {format: markdown}\n  agent:\n    tools: [Read]\n    max_usd: 0.5\n  timeout: 10m\n---\n\n# Weekly code review\n\n### Goal\n\nReview merged work and issue changes, with owners and source links.\n\n### Requires\n\n- `merged`: fictional source data read through its installed adapter.\n- `issues`: fictional source data read through its installed adapter.\n\n### Maintains\n\n- `notes`: a concise local review with source links, named owners and the next checkpoint.\n\n### Done when\n\n- [ ] Each important change or decision names its source and next owner.\n\nThis contract is local demonstration data. It declares a workflow; no report has been generated.\n"
contract_folder = Path(os.environ["HZ_STATE_DIR"]) / "demonstration-contracts"
contract_folder.mkdir(parents=True, exist_ok=True)
(contract_folder / "weekly-code-review.prose.md").write_text(CONTRACT)
os.environ["HZ_HEINZEL__USER_DIR"] = str(contract_folder)


def launch(requester, runner_type, runner):
    configuration = Config.load()
    records, errors = discover()
    records.append(ModuleRecord("showcase", requester, Origin("heinzel-documentation-fixture", "1.0.0", builtin=False)))
    kernel = Kernel(configuration.settings(Settings, "hz"), records, errors, configuration)
    kernel.bind(runner_type, runner)
    sys.argv = ["hz", *sys.argv[1:]]
    build(kernel)()


PULLS = json.loads(
    '[{"url": "https://api.github.com/repos/acme/widgets/pulls/7", "id": 2000000007, "node_id": "PR_kwFakeNode07", "html_url": "https://github.com/acme/widgets/pull/7", "number": 7, "state": "closed", "locked": false, "title": "Render widgets in dark mode", "user": {"login": "ada", "id": 1001, "type": "User", "site_admin": false}, "body": "Adds a dark palette.", "created_at": "2026-10-12T09:00:00Z", "updated_at": "2026-10-21T08:00:00Z", "closed_at": "2026-10-20T16:30:00Z", "merged_at": "2026-10-20T16:30:00Z", "merge_commit_sha": "0000000000000000000000000000000000000007", "assignee": null, "assignees": [], "requested_reviewers": [], "labels": [{"id": 1, "node_id": "LA_kwFake1", "name": "ui", "color": "ededed", "default": false, "description": null}], "draft": false, "head": {"label": "acme:dark-mode", "ref": "dark-mode", "repo": {"full_name": "acme/widgets"}}, "base": {"label": "acme:main", "ref": "main", "repo": {"full_name": "acme/widgets"}}, "author_association": "MEMBER", "auto_merge": null}, {"url": "https://api.github.com/repos/acme/widgets/pulls/7", "id": 2000000007, "node_id": "PR_kwFakeNode07", "html_url": "https://github.com/acme/widgets/pull/8", "number": 8, "state": "closed", "locked": false, "title": "Keep the last row when exporting widgets", "user": {"login": "mira"}, "body": "Adds a dark palette.", "created_at": "2026-10-12T09:00:00Z", "updated_at": "2026-10-22T10:00:00Z", "closed_at": "2026-10-20T16:30:00Z", "merged_at": "2026-10-22T10:00:00Z", "merge_commit_sha": "0000000000000000000000000000000000000007", "assignee": null, "assignees": [], "requested_reviewers": [], "labels": [{"id": 1, "node_id": "LA_kwFake1", "name": "ui", "color": "ededed", "default": false, "description": null}], "draft": false, "head": {"label": "acme:dark-mode", "ref": "dark-mode", "repo": {"full_name": "acme/widgets"}}, "base": {"label": "acme:main", "ref": "main", "repo": {"full_name": "acme/widgets"}}, "author_association": "MEMBER", "auto_merge": null}, {"url": "https://api.github.com/repos/acme/widgets/pulls/7", "id": 2000000007, "node_id": "PR_kwFakeNode07", "html_url": "https://github.com/acme/widgets/pull/9", "number": 9, "state": "closed", "locked": false, "title": "Add release readiness checks", "user": {"login": "jonas"}, "body": "Adds a dark palette.", "created_at": "2026-10-12T09:00:00Z", "updated_at": "2026-10-23T12:00:00Z", "closed_at": "2026-10-20T16:30:00Z", "merged_at": "2026-10-23T12:00:00Z", "merge_commit_sha": "0000000000000000000000000000000000000007", "assignee": null, "assignees": [], "requested_reviewers": [], "labels": [{"id": 1, "node_id": "LA_kwFake1", "name": "ui", "color": "ededed", "default": false, "description": null}], "draft": false, "head": {"label": "acme:dark-mode", "ref": "dark-mode", "repo": {"full_name": "acme/widgets"}}, "base": {"label": "acme:main", "ref": "main", "repo": {"full_name": "acme/widgets"}}, "author_association": "MEMBER", "auto_merge": null}]'
)
ISSUES = json.loads(
    '[{"url": "https://api.github.com/repos/acme/widgets/issues/3", "repository_url": "https://api.github.com/repos/acme/widgets", "html_url": "https://github.com/acme/widgets/issues/3", "id": 3000000003, "node_id": "I_kwFakeNode03", "number": 3, "title": "Widgets wobble at high speed", "user": {"login": "ada", "id": 1001, "type": "User", "site_admin": false}, "labels": [{"id": 2, "node_id": "LA_kwFake2", "name": "bug", "color": "d73a4a", "default": true, "description": "Something isn\'t working"}], "state": "open", "locked": false, "assignee": {"login": "grace", "id": 1002, "type": "User", "site_admin": false}, "assignees": [{"login": "grace", "id": 1002, "type": "User", "site_admin": false}], "comments": 2, "created_at": "2026-09-20T08:00:00Z", "updated_at": "2026-10-05T10:00:00Z", "closed_at": null, "author_association": "MEMBER", "body": "Seen on the test bench."}, {"url": "https://api.github.com/repos/acme/widgets/issues/7", "repository_url": "https://api.github.com/repos/acme/widgets", "html_url": "https://github.com/acme/widgets/pull/7", "id": 3000000007, "node_id": "PR_kwFakeNode07", "number": 7, "title": "Render widgets in dark mode", "user": {"login": "ada", "id": 1001, "type": "User", "site_admin": false}, "labels": [], "state": "closed", "locked": false, "assignee": null, "assignees": [], "comments": 0, "created_at": "2026-10-12T09:00:00Z", "updated_at": "2026-10-21T08:00:00Z", "closed_at": "2026-10-20T16:30:00Z", "author_association": "MEMBER", "pull_request": {"url": "https://api.github.com/repos/acme/widgets/pulls/7", "html_url": "https://github.com/acme/widgets/pull/7", "merged_at": "2026-10-20T16:30:00Z"}, "body": "Adds a dark palette."}, {"url": "https://api.github.com/repos/acme/widgets/issues/3", "repository_url": "https://api.github.com/repos/acme/widgets", "html_url": "https://github.com/acme/widgets/issues/4", "id": 3000000003, "node_id": "I_kwFakeNode03", "number": 4, "title": "Document the widget API", "user": {"login": "ada", "id": 1001, "type": "User", "site_admin": false}, "labels": [{"name": "docs"}], "state": "closed", "locked": false, "assignee": {"login": "ada"}, "assignees": [{"login": "grace", "id": 1002, "type": "User", "site_admin": false}], "comments": 2, "created_at": "2026-09-20T08:00:00Z", "updated_at": "2026-10-22T09:00:00Z", "closed_at": null, "author_association": "MEMBER", "body": "Seen on the test bench."}]'
)

from heinzel import CodeHost, Tracker, PullRequest, Issue
from heinzel_github import Gh, GhResult


class DemoGh(Gh):
    def __init__(self):
        pass

    def executable(self):
        return "/fixture/never-executed-gh"

    def version(self):
        return (2, 103, 2)

    def logged_in(self):
        return True

    def account(self):
        return "mira"

    def run(self, args, *, host, timeout):
        route = next((arg for arg in args if arg.startswith("repos/")), "")
        if route == "repos/acme/widgets/pulls":
            value = PULLS
        elif route == "repos/acme/widgets/issues":
            value = ISSUES
        elif route == "user":
            value = {"login": "mira"}
        else:
            raise ValueError("Unexpected vendor request in the offline demonstration")
        return GhResult(0, json.dumps(value).encode(), "")


showcase = Module(
    "showcase",
    "Documentation-only GitHub requester: fictional data, real adapter.",
    requires=["code-host:read", "tracker:read"],
)


def pull_table(items):
    table = Table("Merged", "Pull request", "Author")
    for item in items:
        table.add_row(item.merged_at.strftime("%d %b"), f"#{item.number} {item.title}", item.author or "Unassigned")
    return table


@showcase.operation(render=pull_table)
def merged(code_host: CodeHost, repository: str) -> list[PullRequest]:
    """Show October's merged work through the real GitHub adapter; fixture-only requester."""
    return code_host.merged_pull_requests(repository, Window(since=SINCE, until=UNTIL))


@showcase.operation(render=issue_table)
def issues(tracker: Tracker, repository: str) -> list[Issue]:
    """Show October's issue changes through the real tracker adapter; fixture-only requester."""
    return tracker.issues_updated(repository, Window(since=SINCE, until=UNTIL))


os.environ["HZ_CAPABILITIES__CODE_HOST"] = "github"
os.environ["HZ_CAPABILITIES__TRACKER"] = "github"
launch(showcase, Gh, DemoGh())
