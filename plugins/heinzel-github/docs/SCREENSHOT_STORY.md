**Audience**
Developers and team leads who want GitHub changes available to Heinzelmännchen workflows through the `code-host:read` and `tracker:read` capabilities.

**Outcome**
“What shipped, and what needs attention?” Follow a fictional widget team through three merged changes, two issue updates, and a contract declaring both inputs. Show readable results and structured JSON so viewers can judge whether this adapter fits their workflows.

Production reads use GitHub CLI 2.40.0 or later and its authentication. The adapter sends GET requests; the account used by `gh` may have broader permissions. The useful reading commands shown here belong to the existing documentation fixture, not the installed plugin’s public CLI. The plugin’s own operation is `hz github info`.

**Scenes**
1. **merged-work — useful app view.** At `/`, run the existing fixture requester in the native terminal. Show October’s three merged pull requests with dates and authors: a small, readable account of what shipped.
2. **issue-changes — useful app view.** At `/`, show the two issue updates with state and owner. The wobbling widgets issue remains open with Grace; the API documentation issue is closed with Ada. Pull request #7 must be excluded from these issue results.
3. **merged-cli — shell result.** Show the same merged work outside the app, demonstrating the existing requester’s table rendering.
4. **issues-json — structured shell result.** Show the issue records as JSON, including source URLs, timestamps, owners, states and labels.
5. **workflow-context — declared workflow.** Preserve the existing `/contracts/weekly-code-review` scene. Show the local “Weekly code review” contract declaring both capabilities and inputs. It is an example declaration; no review or report has been generated.

Preserve all five existing scenes, their commands, routes and order. The plan changes only clarify fictional data and declaration wording, and add a fixed browser clock. This connector supplies no theme, so theme demonstration scenes are unnecessary.

**Fictional fixtures**
Use only `docs/screenshot_fixture.py`, during explicit capture. It binds `DemoGh` while retaining the real adapter and its conversions, and supplies documentation-only `showcase merged` and `showcase issues` operations. Both use the fixed UTC interval `[2026-10-01, 2026-11-01)`.

The fixture contains `acme/widgets` pull requests #7 “Render widgets in dark mode” by Ada, #8 “Keep the last row when exporting widgets” by Mira, and #9 “Add release readiness checks” by Jonas. Its issue results are #3 “Widgets wobble at high speed” and #4 “Document the widget API.” It also creates the existing demonstration contract beneath the isolated state directory. No additional fixture files or repository variants are needed.

**Privacy pitfalls**
Capture in the documented temporary profile without connected accounts. Keep real repositories, credentials, account names, paths and terminal history out of frame. Treat `acme/widgets`, the named contributors, and the simulated login and CLI version as demonstration values; matching public identities or URLs do not establish real activity. Do not open external source links or present fixture results as live GitHub access. The bootstrap writes local demonstration state only when capture is explicitly run.

**Acceptance criteria**
- Five scenes: three useful UI views and two CLI results; both data-reading cases appear in the native app terminal.
- Merged results contain #7, #8 and #9 in merge-date order. Issue results contain #3 open/Grace and #4 closed/Ada, excluding the pull request mixed into the vendor response.
- JSON exposes the same two issues with their typed fields and source URLs.
- The contract view shows “Weekly code review” and remains clearly a local declaration with no generated report.
- Every caption identifies fictional, fixture or demonstration content and stays within 180 characters. Tables, commands and relevant output remain readable without clipping or unrelated history.
- Terminal actions rely on their built-in completion handling; there are no individual-cell text waits, selectors, evaluation scripts or invented panels.
- The TOML below was manually checked for syntax, table scope and the requested field constraints. Runtime parsing and screenshot capture remain unverified: no imports, plugin execution, bootstrap execution or network calls were performed.
