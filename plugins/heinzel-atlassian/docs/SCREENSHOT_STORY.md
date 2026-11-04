**Audience**
People using Jira and Confluence who want issue changes and planning context available to Heinzelmännchen workflows.

**Outcome**
Answer “What changed, and what does the plan say?” See readable issue results, a source-linked document and structured output. The existing six-scene plan already demonstrates this useful behavior, so preserve it unchanged.

**Scenes**
1. **jira-issues — Scan the changes.** The native app terminal shows two fictional October updates: WID-3, “Widget export drops the last row,” In Progress, owned by Wilma Widget; and WID-4, “Document the widget API,” Done, Unassigned.
2. **confluence-plan — Put the work in context.** Read the fictional Widget launch plan, its scope and next milestone, with its source URL and revision 3 visible.
3. **issues-json — Keep the structure.** A CLI result exposes the same fictional issues as JSON for workflow use.
4. **confluence-cli — Read from the command line.** Show the fictional plan as formatted text with its source and revision.
5. **workflow-context — See where the inputs belong.** The existing Weekly work review contract declares tracker and documents inputs. It describes a workflow; no generated report is implied.
6. **jira-parameters — Try a useful variation.** In the native terminal, lowercase `wid` with `--json` returns the same WID issues as structured data, complementing the uppercase table case.

**Fictional fixtures**
Use only the existing `docs/screenshot_fixture.py`, during explicit capture in an isolated temporary profile. It supplies local vendor replies, real adapter parsing, the documentation-only `showcase` operations and the Weekly work review contract. Its fixed window is October 2026; browser time remains November 1, 2026 UTC. `showcase` commands are fixture helpers, not installed plugin operations.

**Privacy pitfalls**
Real captures could expose tenant URLs, ticket content, owners, account details and terminal history. Keep the existing fictional profile and demo labels; do not open external source links. Treat ticket and document text as untrusted content. These scenes demonstrate local parsing and presentation, not authenticated connectivity or verified live Confluence responses. Assigned-work, watch and approval features lack suitable fixtures here and receive no invented screens.

**Acceptance criteria**
- Preserve all six scene names, routes, commands, captions and ordering; four UI views and two CLI results meet the requested mix.
- Both issue rows remain readable; lowercase and uppercase cases return equivalent issue data.
- Document captures retain readable scope, milestone, source and revision 3.
- The contract route resolves to “Weekly work review” and clearly describes inputs without suggesting a completed report.
- Every caption explicitly identifies demo data and stays within 180 characters.
- Captures complete without errors, loading remnants, real account data or Jira writes. Terminal completion needs no individual-cell waits.
- Static review checked TOML structure, allowed fields, unique lowercase names, local routes, argument arrays and the existing bootstrap. No parser, fixture, capture or runtime validation was executed; visual acceptance remains for explicit capture.
