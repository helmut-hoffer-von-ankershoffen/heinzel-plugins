**Audience**
Google Workspace users and workflow authors who want Docs, Sheets, Calendar and Gmail content available inside Heinzelmännchen.

**Outcome**
Follow a fictional launch from finding its files to understanding its owners, meetings, metrics and next actions. The real plugin operations and adapters process local demo replies. Preserve the existing eight-scene plan: its useful results already tell this story.

**Scenes**
1. **recent-files — Find the working set.** Show the seven-day Docs and Sheets listing in the native app terminal.
2. **launch-files — Ask a focused question.** Show the three-day, name-filtered command as a second useful parameter case. The fixture returns the same three launch files; do not imply that this comparison proves filtering against Google.
3. **launch-plan — Understand the next milestone.** Show the fictional document’s goal, named owners and rollout milestone as rendered text, with its source and revision.
4. **launch-week — Put the work on the calendar.** Show three fictional meetings, UTC start times and attendee names.
5. **launch-inbox — Find the relevant conversation.** Show two fictional launch messages, their dates, subjects and sender name.
6. **launch-files-json — Carry results into another workflow.** Show the real file-list operation’s structured output with fictional references, names, kinds and modification times.
7. **launch-metrics — Read the evidence.** Show the fictional Sheet’s Readiness table: export retention, phone layouts and crash-free sessions.
8. **mail-content — Leave with concrete actions.** Show the fictional message assigning export, API-note and phone-screenshot checks.

The first five scenes use the existing `/` app surface and native terminal. The `showcase` commands are documentation-only requesters supplied by the bootstrap, not commands installed by this plugin alone. They exercise the actual Google adapters. No dedicated Workspace dashboard is implied.

**Fictional fixtures**
Use only the existing `docs/screenshot_fixture.py`, and run it only during explicit capture in an isolated profile. It supplies Launch plan, Launch metrics, Launch readiness checklist, three events and two messages. People are Mira, Jonas and Priya Example; addresses use `example.com`. Retain the existing browser time. File modification times come from the fixture process’s current UTC time, so do not require them to equal the frozen browser time.

**Privacy pitfalls**
Keep real accounts, credentials, inboxes, document links and personal paths out of captures. Fixture-created credential placeholders do not demonstrate authentication. These scenes demonstrate offline reads, not successful Google connectivity or writes. Real use requires gws and Google authorization; Gmail access is opt-in. Preserve the demo-data captions and the distinction between plugin commands and fixture-only requesters.

**Acceptance criteria**
- Preserve all eight scene names, commands, captions, routes, viewports and ordering.
- Capture useful completed results in at least two native-terminal UI views, both file-search parameter cases, and the CLI JSON result.
- Document headings, owner actions, calendar columns, mail subjects and Sheet values must be readable at the planned viewport; confirm this during capture.
- All displayed content must match the existing fixture. No invented screens, fixture files or live-account content.
- Terminal actions already wait for completion; add no exact waits for individual cells.
- Static review confirms the format-1 structure, existing relative bootstrap, ISO8601 browser time, eight unique lowercase scene names, captions under 180 characters, local routes and hz argument arrays. No imports, source execution, network access or capture was performed; runtime rendering remains unverified.
