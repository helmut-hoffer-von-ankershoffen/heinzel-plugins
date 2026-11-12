## Audience

People deciding whether to connect Jira and Confluence to Heinzelmännchen workflows, especially those who want to see what the resulting records look like before installing.

## Outcome

Show how the adapter turns issue updates and a Confluence page into useful workflow inputs. The gallery uses an offline requester and fictional responses; it does not demonstrate a signed-in Atlassian connection.

## Scenes

1. **Jira issues:** In the app terminal, show fictional issue keys, titles, states and owners in a readable table.
2. **Confluence plan:** In the app terminal, read a fictional launch plan with its source and revision.
3. **Structured issues:** Show the same fictional Jira records as JSON for consumers that need structured output.
4. **Confluence in the CLI:** Show the fictional plan and its source in a shell result.
5. **Workflow context:** Show the local Weekly work review contract declaring tracker and documents inputs. It is a declaration, not a generated report.
6. **Jira parameters:** In the app terminal, use lowercase `wid` with JSON output to show project-key normalization and a second useful parameter case.

## Fictional fixtures

The existing `docs/screenshot_fixture.py` bootstraps a temporary demonstration contract and supplies local Jira and Confluence replies through a fixture-only requester. The real adapters parse those replies; no external CLI or account is used during the demonstration. The `showcase` operations are documentation fixtures, not plugin commands offered to users after installation.

## Privacy pitfalls

Keep captures isolated from real accounts, project names, issue content, people, page URLs and credentials. The example site and names are fictional. Do not imply that the screenshots verify authentication, live connectivity or the assumed acli JSON shapes against a signed-in acli.

## Acceptance criteria

- Capture all six scenes using the existing fixture bootstrap and preserve the demo-data captions.
- The issue table and plan are legible in the app terminal; the JSON and CLI plan show useful results.
- The contract view identifies the two declared inputs without suggesting that a report was generated.
- The lowercase project case returns the fictional WID records.
- Captures contain only fictional data and do not imply a live connection.
- Review the resulting gallery and run the documented offline freshness check during an explicitly authorized capture workflow.
