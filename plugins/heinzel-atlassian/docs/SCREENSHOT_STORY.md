**Audience** — Engineers, team leads, and workflow authors who want Jira progress and Confluence context inside Heinzelmännchen.

**Outcome** — Follow one fictional Widget launch: see what changed, read the launch plan, inspect structured results, and understand how both sources can feed a declared workflow. These captures demonstrate real adapters receiving local fixture replies. They do not establish a working Atlassian connection. Normal use requires acli 1.3.39 or later, product logins, and capability configuration.

**Scenes**

1. **jira-issues · app terminal** — A compact table shows WID-3, “Widget export drops the last row,” In Progress with Wilma Widget, alongside WID-4, “Document the widget API,” Done and Unassigned. Useful progress at a glance.
2. **confluence-plan · app terminal** — Read the Widget launch plan: scope, named responsibilities, and Tuesday’s release review. Keep its source URL and revision 3 visible so the context remains traceable.
3. **issues-json · CLI** — Show the same fictional changes as structured data, including issue links, timestamps, and labels, demonstrating the adapter’s value to workflows.
4. **confluence-cli · CLI** — Show readable plan content, source, and revision directly in the shell.
5. **workflow-context · contract view** — Show Weekly work review declaring tracker and documents inputs and a notes output. Clearly identify it as a local declaration; no review or report has been generated.

**Fictional fixtures** — Use only the existing `docs/screenshot_fixture.py`. It supplies two October 2026 WID issues, page 123456 on the example site `acme.atlassian.net`, and the Weekly work review contract. Its `showcase issues` and `showcase page` commands are documentation-only requesters, not installed plugin operations. It substitutes `DemoAcli` while retaining the real adapters and parsers. The bootstrap runs only during explicit capture in an isolated temporary profile. Do not add fixture files. Preserve all five existing scenes, their order, routes, commands, and viewport sizes; add a fixed browser time, reduced motion, and an explicit demo-data caption for the workflow.

**Privacy pitfalls** — Keep real accounts, company tickets, personal paths, credentials, and terminal history out of captures. Display example links without opening them. Production authentication belongs to acli; the plugin stores no token. Browser-login replies cannot verify the configured site against the returned gateway, so these screenshots must not imply site verification. Confluence’s fixture shape is assumed from v2 REST and has not been checked live through acli. The existing bootstrap does not demonstrate assigned-work summaries, epic progress, attention, drafts, or approved writes; do not imply those were captured.

**Acceptance criteria**

- Five scenes include three useful app views and two useful CLI results, with demo data identified in every caption.
- Both issue rows and all four table columns are legible; the plan’s scope, milestone, source, and revision remain readable.
- JSON presents structured issue results; the contract view communicates declared inputs without suggesting a completed run.
- Commands are hz argument arrays. Routes come from the existing plan. Terminal actions rely on their built-in completion wait; no individual table-cell waits, selectors, eval, or shell commands are added.
- Static validation against the requested plan structure confirms unique lowercase scene names, captions under 180 characters, an ISO8601 browser time, and supported actions. No code, parser, capture, or runtime validator was executed, and no files were edited. Rendered acceptance remains to be verified during explicit capture.
