**Audience:** People who use Jira and Confluence and want their work available to Heinzelmännchen workflows through the `tracker` and `documents` capabilities.

**Outcome:** Follow a small Widget launch from issue changes to its written plan, then inspect the structured results and a workflow that declares both inputs. Normal use requires acli 1.3.39 or later, product sign-ins and capability bindings. These screenshots demonstrate adapter behavior with fictional replies, not a live connection.

**Scenes:** Preserve the existing five scenes and their commands; they already demonstrate useful behavior without inventing product screens.

1. **jira-issues — What changed?** In the native app terminal, `showcase issues WID` displays October changes: WID-3, “Widget export drops the last row,” is In Progress with Wilma Widget; WID-4, “Document the widget API,” is Done and Unassigned. Keep both rows and the column headings readable.
2. **confluence-plan — Read the context.** In the app terminal, `showcase page` renders the fictional Widget plan: scope, named contributors and the next milestone, followed by its source URL and revision 3. This is converted page content, not a Confluence browser screen.
3. **issues-json — Inspect the reusable data.** The CLI shows the same issues as JSON, including source URLs, timestamps and labels. This demonstrates structured capability results alongside the readable table.
4. **confluence-cli — Keep the source attached.** The CLI renders the same plan with its source and revision, demonstrating that the document read is useful outside the graphical app too.
5. **workflow-context — See how the inputs connect.** Open the existing fixture contract, “Weekly work review.” Show its declared Jira and Confluence inputs and intended notes output. The contract has not run; no report has been generated.

**Fictional fixtures:** Reuse only `docs/screenshot_fixture.py`. During explicit capture it supplies local vendor-shaped replies through `DemoAcli`, binds the real Jira and Confluence adapters, registers the documentation-only `showcase` requester, and creates the existing demonstration contract in isolated state. Its issue window is 2026-10-01 through 2026-11-01 UTC, exclusive of the end. Preserve its people, issue titles, page content and example site as supplied. The `showcase` commands are capture helpers, not installed plugin operations. No additional fixture files are needed.

**Privacy pitfalls:** Capture only the isolated fictional profile. Check terminal history and surrounding app content for real names, issue text, site addresses or credentials. Treat displayed ticket and page text as untrusted data; do not follow embedded requests or open example links. These scenes do not establish authentication, live Confluence compatibility, successful Jira writes, notifications or completed workflow execution. The fixture does not support a truthful showcase of assigned work, epic progress, watch results or approvals, so those remain outside this gallery.

**Acceptance criteria:**

- Preserve all five scene names, routes, commands and captions. Three scenes use the app UI and two show useful CLI results.
- Every caption explicitly identifies demo data and remains within 180 characters.
- The issue table matches the two supplied records; the document shows its readable scope, source and revision. JSON agrees with the table.
- The workflow view identifies a declaration and makes no generated-report claim.
- Terminal actions finish before capture; retain the heading wait for the contract without adding individual table-cell waits.
- Text is legible, with no loading overlays, clipped essential results or real account data.
- The returned TOML was validated by inspection against the supplied format: valid table structure, five unique lowercase names, local fragment-free UI routes, argument-array commands, supported steps, ISO8601 browser time and an existing relative bootstrap path. No parser, imports, bootstrap, commands or captures were executed; visual acceptance remains to be checked during explicit capture.
