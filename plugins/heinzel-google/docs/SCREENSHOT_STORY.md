**Audience**

People who want their Heinzel workflows to read Google Workspace information: project leads preparing reviews, developers building workflows, and anyone gathering context from Docs, Sheets, Calendar and Gmail.

**Outcome**

“Ready for Thursday”: follow a fictional launch from its files to its plan, meetings, metrics and remaining actions. Help viewers decide whether these Google capability adapters fit their workflows.

`google files` is a shipped plugin operation. The `showcase` commands are documentation-only requesters supplied by the existing fixture; installing the plugin does not add them. Their output exercises the real adapters against fictional vendor replies.

**Scenes**

Preserve the existing eight scenes, their order, commands, routes and viewports. Add a fixed browser time and explicitly identify fictional replies in the final two captions.

1. **launch-files · UI:** In the native app terminal, list three days of files with `--name Launch`. Show Launch plan, Launch metrics and Launch readiness checklist.
2. **launch-files-week · UI:** Run the seven-day case without a name filter. Show the alternative parameters clearly. The fixture returns the same three files for both queries; this does not demonstrate different filtering results.
3. **launch-plan · UI:** Read the fictional Doc as formatted text, with its goal, owners, next milestone, source URL and revision. Make the preparation task feel concrete.
4. **launch-week · UI:** Show three meetings with UTC start times and attendee names, making the launch review and follow-up checkpoints easy to scan.
5. **launch-inbox · UI:** Show two launch-related messages with received dates, subjects and sender names through the fixture's focused mail query.
6. **launch-files-json · CLI:** Show the shipped file-list operation as structured data, including file references, names, kinds and modification times.
7. **launch-metrics · CLI:** Read the fictional Sheet as a table of release checks, targets and observations. Its percentages are example values, not product performance claims.
8. **mail-content · CLI:** End with the fictional readiness message's concrete assignments: export boundary, API notes and phone screenshots.

All UI scenes use the existing `/` route and native terminal. These are terminal result views, not dedicated Google document, calendar or inbox screens.

**Fictional fixtures**

Use only `docs/screenshot_fixture.py`, during an explicit capture in an isolated temporary profile. Its `DemoGws` supplies local replies while the installed adapters perform their normal conversions. It also registers the fixture-only `showcase` requester.

Retain the existing Launch documents, Readiness sheet, October 19–26, 2026 event/mail window, Mira/Jonas/Priya Example identities, and `example.com` addresses. Do not create fixture files or substitute connected accounts. Displayed source URLs identify fictional files; opening them is not part of the story.

**Privacy pitfalls**

A real account could expose document titles, file IDs, source URLs, event participants, subjects and message bodies. Keep capture state isolated, including terminal history and account settings. Do not run authentication, live connector tests, writes or external links for this story.

The fixture explicitly binds mail for demonstration; that does not mean Gmail access is enabled automatically after installation. These captures also do not establish live connectivity or demonstrate confirmed writes.

**Acceptance criteria**

- Eight scenes: five useful app-terminal views and three CLI results, with both file-query parameter cases visible.
- Every caption identifies fictional or fixture data and stays within 180 characters.
- Commands match the shipped operations or existing fixture requesters; no invented screens, shell commands, selectors or extra waits.
- Terminal actions finish successfully before capture; content, columns and source/revision details remain legible at the preserved viewport.
- Expected results match the fixture: three files, three meetings, two messages, the plan, three metric rows and the readiness assignments.
- `browser_time` fixes the browser clock only. The fixture uses Python's current time for file modification timestamps, so those values must not be asserted as fixed or used to claim reproducible freshness.
- TOML syntax and fields were statically reviewed against the requested contract and supplied definitions. No parser, bootstrap, plugin code, commands or captures were run; rendered results remain unverified.
