## Audience
People considering an Atlassian connector for workflows that need Jira issue updates and Confluence page content.

## Outcome
Show how a workflow can bring issue progress and a plan together through the `tracker` and `documents` capabilities. The screenshots use fictional data and the real adapters with a fixture-only requester; they do not demonstrate a live Atlassian connection.

## Scenes
1. **Jira issues:** A readable table of fictional issue titles, states and owners in the app terminal.
2. **Confluence plan:** The fictional Widget plan rendered in the app terminal, including its source and revision.
3. **Issues JSON:** The same kind of Jira result as structured CLI output for downstream use.
4. **Confluence CLI:** The plan and its source details in the shell.
5. **Workflow context:** The local Weekly work review contract declares both inputs and describes their purpose. It has not generated a report.
6. **Jira parameters:** A second terminal example uses lowercase `wid` and JSON output, showing project-key normalization and a different output format.

## Fictional fixtures
The existing `docs/screenshot_fixture.py` supplies two fictional WID issues, a Widget plan at revision 3, and a local demonstration contract. It binds the real adapters to a fixture-only requester that returns local vendor-shaped replies. The `showcase` commands are documentation fixtures, not commands supplied by the installed plugin.

## Privacy pitfalls
Capture only the isolated fictional profile: real issue titles, people, site URLs, page content, account details and terminal history could disclose private information. The example `acme.atlassian.net` URL is fictional. Do not imply the fixture proves authentication or live access; the README also notes that the assumed acli JSON shapes have not yet been verified against a signed-in acli.

## Acceptance criteria
- The issue table shows the fictional records and their states and owners; the plan shows its text, source and revision.
- Both UI terminal examples and useful CLI results are legible, and every caption identifies demo data.
- The contract view makes clear that it declares a workflow and has not generated a report.
- The lowercase project example returns the fictional WID records in JSON.
- Captures contain no real credentials, account data or private Atlassian content.
- The existing plan is retained because it already covers these behaviors. Its syntax and fields were reviewed against the supplied format; capture and runtime validation were not performed because execution was excluded.
