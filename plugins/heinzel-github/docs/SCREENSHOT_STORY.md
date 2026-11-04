## Audience

A team lead or workflow author deciding whether GitHub pull requests and issues can feed a Heinzelmännchen review workflow.

## Outcome

Show how the GitHub adapter supplies merged work and updated issues to a capability-based workflow, with readable terminal output and structured JSON for automation. The demonstration uses a fixture-only requester and fictional GitHub responses; it does not show a live GitHub connection or a generated review.

## Scenes

1. **Merged work, in light appearance:** Three fictional pull requests make recent changes and authors easy to scan in the app terminal.
2. **Issue changes, in dark appearance:** A second app-terminal view shows fictional issues, states, and owners. Pull requests are excluded from the issue results.
3. **Merged work in the CLI:** The same fictional pull requests show what a shell user receives from the demonstration requester.
4. **Issues as JSON:** Structured fictional issue results illustrate a format useful to scripts and agents.
5. **Workflow context:** A fictional local weekly-review contract declares merged-work and issue inputs. It is a workflow declaration, not a completed report.

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap and its `acme/widgets` responses, October 2026 window, and local weekly-review contract. The `showcase` commands are documentation-only requesters using the real adapter with a fake `gh` implementation; they are not built-in GitHub plugin commands.

## Privacy pitfalls

Capture only the isolated fixture profile. Check screenshots and terminal output for real account names, repository names, tokens, local paths, and unrelated terminal history. Fixture URLs and names are examples, not evidence of a live GitHub request.

## Acceptance criteria

- Both app-terminal views show useful, legible results, with light and dark appearances visibly applied.
- The merged view identifies pull requests and authors; the issue view shows issue states and owners without treating the fixture pull request as an issue.
- The CLI captures show a readable merged-work result and issue JSON, with no errors or clipped essential output.
- The workflow view identifies the two declared inputs and does not imply that a report was generated.
- Every caption identifies demo or fictional data, and the gallery makes the fixture-only requester clear.
- Captures contain no real credentials or private data. Review the generated images before publication.
- The plan is checked against the requested format by inspection; capture and runtime validation remain to be performed during explicit screenshot capture.
