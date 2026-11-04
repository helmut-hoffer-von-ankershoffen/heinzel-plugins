## Audience

A person deciding whether Heinzelmännchen can bring Jira progress and a Confluence plan into a local workflow using their existing Atlassian CLI access.

## Outcome

Show the connection between issue changes, a source document, and a workflow that can use both. The gallery uses the existing offline fixture and real adapter parsers; it does not demonstrate a live Atlassian connection or a generated report.

## Scenes

1. **Jira issues:** A native app terminal shows fictional changes with their states and owners.
2. **Confluence plan:** A second terminal view shows the fictional launch plan, source, and revision.
3. **Issues as JSON:** A CLI result shows the structured issue data available to a workflow.
4. **Confluence in the CLI:** A CLI result shows the plan and its provenance.
5. **Workflow context:** The local Weekly work review contract declares both inputs and explains its goal. It has not generated a report.
6. **Jira parameters:** The native terminal shows the lowercase project key and JSON output, providing a second useful parameter case.

The existing plan already covers these behaviors, so it is preserved. The `showcase` commands are documentation-fixture operations, not commands supplied by the installed plugin.

## Fictional fixtures

`docs/screenshot_fixture.py` supplies a fictional Widget project, two Jira issues, a Confluence page, and a local workflow contract. Its fixture requester returns local vendor-shaped replies without invoking a real `acli` or accessing an account. The plan runs the bootstrap only during explicit capture.

## Privacy pitfalls

Use only the isolated fictional profile and fixture data. Avoid capturing real site URLs, issue text, names, account identifiers, terminal history, credentials, or unrelated notifications. The example URL and people in the fixture are fictional. Live Jira and Confluence content may contain sensitive or untrusted text.

## Acceptance criteria

- Capture all six existing scenes; the two app-terminal views and contract view are readable at their specified sizes.
- The issue view shows the fictional issue keys, titles, states, and owners; the page view shows the plan, source, and revision.
- The JSON and lowercase-project examples complete with fixture data, and the contract is clearly presented as a declaration rather than a generated report.
- Captions identify demo data and do not imply a live connection or production `showcase` commands.
- No real account data appears. Review the contact sheet after capture.
- The TOML is structurally checked against the requested format by inspection; capture and runtime validation were not run because code execution was excluded.
