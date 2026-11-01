**Audience.** People building Heinzelmännchen workflows that need Google Workspace context: recently changed files, document text, meeting schedules and relevant mail.

**Outcome.** Follow a fictional launch from “what changed?” to the plan, meetings, readiness figures and next actions. Show useful results inside the existing app terminal and CLI. Real use requires Google Workspace CLI (`gws`) and authorization; Gmail is opt-in. These screenshots demonstrate read behavior with fictional replies, not a connected account or completed launch.

**Scenes.** Preserve the existing eight-scene plan and captions unchanged:

1. **launch-files — UI:** Find launch-related files with `--days 3 --name Launch`. Show the fictional plan, metrics and readiness checklist.
2. **launch-files-week — UI:** Try `--days 7` without a name filter. The fixture returns the same three files; demonstrate another parameter case without claiming additional matches.
3. **launch-plan — UI:** Read the plan as formatted text, including its goal, owners, next milestone, source URL and revision.
4. **launch-week — UI:** See three fictional meetings with UTC start times and attendee names, including the readiness review and rollout checkpoint.
5. **launch-inbox — UI:** Show two launch-related messages with received dates, subjects and the fictional sender name.
6. **launch-files-json — CLI:** Show the file results as structured records suitable for further processing.
7. **launch-metrics — CLI:** Turn the fictional Sheet into a readable readiness table: export retention, screenshot checks and crash-free sessions.
8. **mail-content — CLI:** Finish with the message assigning Mira, Jonas and Priya their next checks.

**Fictional fixtures.** Reuse only the existing `docs/screenshot_fixture.py`, during explicit capture in an isolated profile. It supplies `DemoGws` replies and registers documentation-only `showcase` requesters that call the real adapters. The launch documents, metrics, messages, people and `example.com` addresses are fictional. `google files` is a product command; `showcase` commands are fixture-only demonstrations, not installed plugin features. The fixture returns a fixed file list rather than evaluating the Drive query.

**Privacy pitfalls.** Real file titles, document text, source URLs, meeting details and mail can disclose private information. The fixture's name-only meeting and inbox renderers do not establish general anonymization. Keep real account state, credentials and personal terminal history out of captures. Fixture sign-in markers do not prove authentication. `browser_time` fixes browser time; the fixture still uses Python's current time for file modification timestamps.

**Acceptance criteria.**

- Retain eight scenes: five useful app-terminal views and three CLI results, including both file-search parameter cases.
- Keep every caption explicit about fictional or fixture content. Show no invented Google editor, calendar grid, inbox panel or write-confirmation screen.
- Results must be readable at the declared viewport: document sections and revision, meeting columns, message subjects, readiness values and actionable mail text. CLI JSON must expose `ref`, `name`, `kind` and `modified_at`.
- Capture only through the isolated existing fixture. Do not interpret demo metrics as measured product performance or identical file lists as proof of filtering.
- Static validation by inspection: existing bootstrap path, ISO8601 browser time, unique lowercase scene names, captions under 180 characters, local `/` routes, positive dimensions/timeouts and argument-array commands all match the requested format. Terminal steps need no additional cell-text waits.

The plan is preserved unchanged. No bootstrap, imports, parser, product commands, network calls or captures were run; rendered acceptance remains to be checked during explicit capture.
