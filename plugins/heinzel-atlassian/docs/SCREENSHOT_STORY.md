**Audience:** Workflow authors who want Jira changes and Confluence context available through Heinzelmännchen’s `tracker` and `documents` capabilities.

**Useful outcome:** Give a fictional Widget release review a clear starting point: see changed issues, their owners and states, then read the launch plan with its source and revision. Structured CLI output demonstrates how those same results can feed a workflow.

**Distinct scenes:**

1. **jira-issues — See what needs attention.** The app’s native terminal displays WID-3, “Widget export drops the last row,” In Progress with Wilma Widget, alongside WID-4, “Document the widget API,” Done and Unassigned.
2. **confluence-plan — Understand the next milestone.** The native terminal renders the Widget plan with headings, scope, the release-review milestone, source URL and revision 3.
3. **issues-json — Inspect reusable data.** A CLI result shows the fictional issues as structured output, including normalized fields beyond the compact table.
4. **confluence-cli — Keep the context in the shell.** The CLI renders the same readable plan with its source and revision.

**Fictional fixture setup:** Preserve the existing four scenes and `docs/screenshot_fixture.py`. During an explicitly requested capture, use the documented temporary profile without connected accounts. The bootstrap registers documentation-only `showcase issues WID` and `showcase page` commands, binds the real Atlassian adapters, and substitutes local vendor-shaped replies through `DemoAcli`. Its issue window is October 2026; its tenant is the fictional `acme.atlassian.net`. These showcase commands are fixture helpers, not commands installed by the plugin. The plugin declares no dedicated UI panel, so both UI scenes correctly use `/` and the native terminal.

**Privacy pitfalls and installation limits:** Successful real reads can reveal tenant URLs, issue titles, assignee names and page content; error-message redaction does not anonymize those results. Keep captures entirely synthetic and do not open fixture source links. Real use requires acli 1.3.39 or later, authentication and matching site configuration. The plugin stores no authentication token itself. These captures demonstrate read-only adapter behavior, not a successful live connection. The README says vendor JSON shapes have not yet been verified against logged-in acli. Confluence support reads a known page; it does not search pages updated in a window.

**Acceptance criteria:**

- Preserve all four existing scene names, commands, routes and the existing bootstrap; improve captions and capture completion checks only.
- Both UI captures show useful completed results in the native terminal. The Jira table includes both issues and their owners/states; the Confluence view includes the milestone, source and revision 3.
- CLI captures show structured issue results and the readable document result without errors or truncation.
- Every caption explicitly identifies demo data. No personal profile, credentials, real tenant content or invented plugin screen appears.
- Static review confirms the TOML structure, four unique lowercase scene names, local routes, argument-array commands and captions under 180 characters against the requested contract. No code, imports, fixture, network request or capture was executed; runtime and visual acceptance remain capture-time checks.
## Current captured scope

The documentation bootstrap uses the test suites' in-memory vendor-runner pattern: it binds only `DemoAcli` at `Acli`
while retaining the actual installed capability adapters and conversions. It never executes a vendor client.
The fixed October window lives inside the fixture requester, so the displayed commands stay concise.
The workflow scene is a real seeded, valid local contract. It declares inputs; no agent or report generation runs.
