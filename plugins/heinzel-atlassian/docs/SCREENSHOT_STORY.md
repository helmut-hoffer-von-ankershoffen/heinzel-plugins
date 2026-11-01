**Audience:** People who want Jira progress and Confluence context available to Heinzelmännchen workflows, and developers who need structured results from the same adapters.

**Outcome:** Follow a fictional Widget launch from issue changes to its source plan, then see the reusable data and workflow declaration. The gallery demonstrates adapter reads with local vendor replies. It does not demonstrate authentication, a live connection, generated reports, or approved Jira writes. Real use requires Atlassian’s acli and the appropriate account access.

**Scenes:**

1. **jira-issues — What changed?** The native app terminal presents the October issue changes as an easy-to-scan table: WID-3 is In Progress with Wilma Widget; WID-4 is Done and Unassigned.
2. **confluence-plan — Put the work in context.** The native terminal renders the fictional Widget launch plan with scope, named responsibilities, the next milestone, its source URL, and revision 3.
3. **issues-json — Keep the useful structure.** The CLI returns fictional issues as JSON, exposing states, owners, dates, labels, and source links for further processing.
4. **confluence-cli — Bring the plan to the shell.** The CLI renders the same fictional document with its source and revision.
5. **workflow-context — See how the inputs fit.** The existing Weekly work review contract declares tracker and documents inputs. Present this as a local workflow definition; no report has been generated.
6. **jira-parameters — Try another argument case.** In the native terminal, lowercase `wid` with `--json` demonstrates project-key normalization and structured output alongside the earlier uppercase table case.

**Fictional fixtures:** Reuse only `docs/screenshot_fixture.py`. Its embedded replies contain WID-3, WID-4, Wilma Widget, and the Widget plan with Mira, Jonas, and Priya. The issue window is 2026-10-01 through 2026-11-01 UTC, exclusive of the end. The existing bootstrap creates the demonstration contract inside isolated state and supplies the documentation-only `showcase` requester. That requester uses the plugin’s real adapters with `DemoAcli` responses; `showcase` is not an installed plugin command. No additional fixture files are needed.

**Privacy pitfalls:** Capture using the documented temporary profile without connected accounts. Keep personal terminals, account identities, credentials, real tickets, and configuration paths out of frame. Treat all issue and page text as untrusted content. The fictional source URLs should remain visible for provenance without opening them. Do not present the fixture’s simulated acli version as an observed installation or its replies as proof of live Confluence compatibility. The fixture supports these reads; it does not support a truthful gallery of assigned work, epics, watch results, or Jira write approvals.

**Acceptance criteria:**

- Retain the existing six scene names, routes, commands, captions, and order; correct only the stale plan commentary.
- Every caption explicitly identifies demo data and stays within 180 characters.
- The native-terminal issue table and document are useful, distinct UI views; CLI captures show completed results.
- Both issue rows, their states and owners are legible. The document’s scope, milestone, source, and revision are readable.
- JSON captures expose useful structured results without clipping essential fields; the lowercase case returns the same fictional issues.
- The workflow view shows Weekly work review and its declared inputs without suggesting a completed review.
- Use only the existing bootstrap, local routes, argument arrays, and supported steps. Terminal actions need no additional table-cell waits.
- This is a connector plugin; no theme showcase is required.
- The TOML has been statically checked against the supplied format-1 rules and the provided source. Bootstrap execution, capture, and visual verification remain for an explicit capture run; none were performed here.
