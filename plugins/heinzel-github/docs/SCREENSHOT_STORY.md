## Audience

Teams considering a GitHub connector for weekly reviews, and workflow authors who need merged pull requests and issue changes through Heinzelmännchen capabilities.

## Outcome

Show how fictional repository activity becomes readable review context: merged work, issue ownership and structured results. Make clear that the showcase requester and weekly review contract are demonstration fixtures, while the GitHub adapter performs the conversions.

## Scenes

1. **Merged work:** A light app-terminal view lists fictional merged pull requests, dates and authors.
2. **Issue changes:** A dark app-terminal view shows fictional issues, states and owners.
3. **Merged CLI:** The same merged-work result is available as a shell command.
4. **Issues JSON:** Structured fictional issue results illustrate use by scripts and agents.
5. **Workflow context:** A local weekly-review contract declares both inputs; it does not claim a report was generated.

## Fictional fixtures

The existing `docs/screenshot_fixture.py` supplies fictional `acme/widgets` responses, an October 2026 window and a local demonstration contract. Its `showcase` commands are documentation-only requesters, not commands supplied by the plugin itself. The fixture uses the real adapter with a simulated GitHub CLI requester.

## Privacy pitfalls

Capture only with the isolated fictional profile and fixture. Check terminal output and contract content for real repository names, account identities, credentials or unrelated local paths before publishing. Example GitHub URLs are fixture data, not evidence of a live request or connected account.

## Acceptance criteria

- Both app-terminal views show useful, legible fictional results, with merged work and issue changes distinguishable at a glance.
- CLI captures show a readable merged-work result and structured issue output; captions identify the demo data.
- The workflow view identifies the contract as a local example and does not imply a report was generated.
- Captures contain no real account or repository data, secrets or unrelated local information.
- The existing plan is retained: its five scenes already cover the useful behavior. Its TOML structure and fields were reviewed against the supplied requirements; capture and parser validation remain to be run during an explicit capture workflow.
