## Audience

People considering the Atlassian plugin for a workflow that brings Jira changes and a Confluence plan together in Heinzelmännchen.

## Outcome

Show how fictional issue changes and a plan become readable workflow inputs, with both human-friendly terminal output and structured JSON. The screenshots demonstrate the real adapters using fixture-supplied vendor replies; they do not demonstrate a live Atlassian connection.

## Scenes

1. **Jira changes in the app** — A compact table shows two fictional Widget issues, their states and owners, including an unassigned issue.
2. **Confluence plan in the app** — The fictional launch plan shows its scope, next milestone, source and revision.
3. **Jira JSON in the CLI** — The same fictional changes appear as structured output for a programmatic workflow.
4. **Confluence in the CLI** — The plan, source and revision are readable from the command line.
5. **Workflow context** — A local Weekly work review contract declares Jira and Confluence inputs. It is a workflow definition, not a generated report.
6. **A second Jira parameter case** — Lowercase `wid` and `--json` demonstrate project-key normalization and structured output in the app terminal.

## Fictional fixtures

The existing `docs/screenshot_fixture.py` creates the local contract and supplies fictional Jira and Confluence replies to the real adapters. Its `showcase` commands exist only for this demonstration. The October 2026 window, Widget project, people, site and page are example data.

## Privacy pitfalls

Capture only the isolated fixture profile: issue titles, names, page text, URLs and terminal history from a real account may be sensitive. Do not display tokens, account details or private workspace data. Fixture results do not establish that acli is installed, authenticated or connected to the configured site. The story should not imply that a review was generated or that Jira was changed.

## Acceptance criteria

- All six existing scenes remain recognizable and visibly identify their contents as demo data.
- The app terminal shows the issue table and the plan; the CLI shows useful JSON and document output.
- The two Jira parameter cases show `WID` as a table and lowercase `wid` with JSON.
- The contract view identifies its two inputs without claiming a generated report.
- Captures contain only fictional fixture data and no credentials or real account information.
- Before publication, capture and inspect the images for legibility and confirm the gallery matches the plan. The plan has been checked against the supplied format and source by inspection; capture was not run.
