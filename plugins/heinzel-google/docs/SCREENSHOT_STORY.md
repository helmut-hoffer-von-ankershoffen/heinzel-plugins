**Audience.** People building Heinzelmännchen workflows that need Google Docs and Sheets content, calendar context, and optional Gmail access.

**Outcome.** Follow one fictional launch from its files to its plan, meetings, metrics, and next actions. Show the installed adapter processing local Workspace replies through real operations and capability methods. The plugin declares no dedicated panel; use the existing app terminal at `/`. The `showcase` commands and their renderers belong only to the documentation fixture. Production use requires gws and Google authorization; Gmail and calendar/mail writes are opt-in.

**Scenes.** Preserve the seven existing scenes, correct the calendar caption to describe attendees, and insert one additional native-terminal parameter case.

1. **launch-files — Find the launch material.** In the app terminal, run `hz google files --days 3 --name Launch`. Show the fictional Launch plan, Launch metrics, and Launch readiness checklist with their document types and references.
2. **launch-files-week — Explore a broader window.** Run `hz google files --days 7` in the app terminal. This demonstrates a second useful parameter case without a name filter. The fixture returns the same three canned files; these captures do not verify Google's server-side filtering.
3. **launch-plan — Understand the next milestone.** The fixture-only `showcase notes launch-plan` requester displays converted document headings, assigned checks, the Thursday review, source URL, and revision.
4. **launch-week — See who is involved.** The fixture-only calendar requester displays three meetings with UTC start times and attendees. These people are attendees, not verified meeting owners.
5. **launch-inbox — Find relevant updates.** The fixture-only mail requester shows two launch messages, received dates, subjects, and the fictional sender.
6. **launch-files-json — Inspect structured results.** Show the real file-listing operation's JSON output with fictional names, kinds, references, and modification timestamps.
7. **launch-metrics — Read a Sheet as a table.** The fixture-only documents requester displays the Readiness sheet's targets and observed values, including the fictional 99.95% crash-free figure.
8. **mail-content — Turn context into next actions.** The fixture-only mail requester reads the message assigning export-boundary, API-note, and phone-screenshot checks.

**Fictional fixtures.** Reuse only `docs/screenshot_fixture.py`, already referenced by the plan. During explicit capture it binds `DemoGws`, supplies local vendor replies, registers the documentation-only `showcase` module, and creates dummy sign-in files under the isolated `HZ_STATE_DIR`. Reuse its Mira, Jonas, and Priya Example characters, `example.com` addresses, document IDs, two messages, and calendar window of 19–26 October 2026. Calendar and mail dates are fixed; file modification timestamps come from Python's capture-time clock. No additional fixture files are proposed.

**Privacy pitfalls.** Capture only the isolated fictional profile. Real document URLs, file IDs, message bodies, addresses, meeting titles, terminal history, and local paths can expose private information. Sanitized text is not anonymized text. Keep fixture-only commands visibly identified in captions and accompanying prose. Dummy sign-in files do not establish a working Google connection, canned replies do not establish live query behavior, and fictional readiness metrics do not describe plugin quality. The fixture does not demonstrate confirmed writes or production authorization.

**Acceptance criteria.**

- Eight scenes retain every existing scene name and useful result; five show useful app-terminal views and three show CLI results.
- Both file-listing parameter cases appear in the native terminal. Their identical canned results are disclosed.
- Every caption explicitly identifies fictional content or replies and stays below 180 characters.
- Commands, fixture references, and `/` are supported by the provided source and existing plan. No dedicated Google screen is implied.
- Captures show completed, legible results at the existing UI viewport. Terminal actions supply completion synchronization; no individual-cell text waits are added.
- Expected fixture content includes three files, three calendar meetings, two mail summaries, document headings and revision, the three-row metrics table, and the message's next actions.
- No real account data or credentials appear. All demonstrated operations read data.
- This is a connector, so applied theme demonstrations are not applicable.
- Validation is by static inspection of TOML syntax, the requested schema, source declarations, and fixture behavior. No parser, bootstrap, application, or capture was executed; runtime layout and capture success remain to be verified during explicit capture.
