## Audience

Someone considering Heinzelmännchen’s Atlassian plugin for workflows that need Jira issue changes and Confluence page content.

## Outcome

Show how a workflow can bring issue progress and its supporting plan together, while making clear that these are fictional, offline results. The plugin uses Atlassian’s `acli` for real reads; this demonstration substitutes local vendor replies.

## Scenes

1. **Jira changes in the app** — A compact table shows two fictional WID issues, their states and owners.
2. **The Confluence plan in the app** — Read the fictional launch plan alongside its source and revision.
3. **Structured Jira output** — Show the same kind of issue data as JSON for a workflow or script.
4. **Confluence output in the CLI** — Show the plan, source and revision in a shell capture.
5. **Workflow context** — The local Weekly work review contract shows how Jira and Confluence inputs can be declared. It does not claim that a report was generated.
6. **A second Jira parameter case** — In the app terminal, use lowercase `wid` and JSON output to demonstrate project-key normalization and structured results.

## Fictional fixtures

The existing `docs/screenshot_fixture.py` supplies the `showcase` operations, a local demonstration contract, and fictional Jira and Confluence responses. It exercises the real adapters through a fixture-only requester; it does not execute `acli` or connect to an account. The fixed browser time and fixture window keep the story coherent.

## Privacy pitfalls

Capture only the isolated fictional profile. Do not expose real issue titles, names, page URLs, credentials, account details, terminal history, or logs. The example Atlassian URL and people are fictional; captions must keep that clear. Do not imply the fixture proves a live connection or that a review report exists.

## Acceptance criteria

- All six existing scenes remain, including two useful app-terminal views, the workflow contract, and CLI results.
- Captions identify demo data and distinguish the fixture requester from a live Atlassian connection.
- Jira output shows the fictional issue keys, titles, states and owners; the lowercase parameter case returns structured WID data.
- The plan view shows the fictional content, source and revision; the contract view states that no report has been generated.
- Captures contain no real account data or secrets, and use only the existing bootstrap.

The existing plan already covers the useful behavior, so it is retained. Its TOML structure was inspected against the requested format; no parser or capture was run because code execution was excluded.
