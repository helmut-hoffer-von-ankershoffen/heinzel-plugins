## Audience
Workflow authors and small teams who want Google Docs, Sheets, Calendar and Gmail available through Heinzelmännchen’s documents, calendar and mail capabilities.

## Outcome
**Walk into launch review with the plan, the people and the next checks in hand.** Follow one fictional launch from recently changed files to readable notes, meetings, metrics and mail. The screenshots demonstrate the installed adapters’ results using local vendor replies. Production use requires Google Workspace CLI setup and Google authorization; the demonstration does not establish a live connection.

Preserve the existing eight-scene plan: it already provides five useful views in the app’s native terminal and three CLI results. Its two file-list scenes exercise different parameter cases. Every UI scene uses the existing `/` route.

## Scenes
1. **recent-files — Find a starting point.** Run `hz google files --days 7` in the app terminal. Show Launch plan, Launch metrics and Launch readiness checklist, with their file kinds and references.
2. **launch-files — Make the request specific.** Run `hz google files --days 3 --name Launch` in the app terminal. Keep the parameters visible. The fixture returns the same three files for both requests; this demonstrates parameter usage, without demonstrating a reduction in results.
3. **launch-plan — Understand the work.** Show the fictional plan’s goal, named owners and next milestone as rendered document text, with its source URL and revision. The `showcase notes` requester belongs to the documentation fixture.
4. **launch-week — See who meets when.** Show three fictional meetings with UTC start times, titles and attendee names. Keep the UTC column heading readable.
5. **launch-inbox — Find the relevant conversation.** Show two fictional launch messages, received on 20 and 21 October, with subjects and sender names. The fixture requester uses `from:updates@example.com subject:Launch` and the launch-week window.
6. **launch-files-json — See the automation interface.** Show the real file-list operation’s JSON result, including file references, names, kinds and modification times, using fictional replies.
7. **launch-metrics — Read the evidence.** Show the Sheet’s Readiness table: export rows, phone screenshots and crash-free sessions, with targets and observed values. These figures are fictional project data, not plugin performance claims.
8. **mail-content — Leave with next actions.** Show the fictional message assigning Mira the export boundary, Jonas the API notes and Priya the phone screenshots. End on concrete work someone could act on.

## Fictional fixtures
Use only the existing `docs/screenshot_fixture.py`, during explicit capture in an isolated temporary profile. It registers the documentation-only `showcase` requester and substitutes `DemoGws` replies while retaining the real Google adapter conversions and fixture renderers. It creates its own dummy credential markers and a nonworking executable stub; no additional fixture files are required.

The supplied data contains three launch files, a plan, a Readiness sheet, three meetings and two messages. Mira Example, Jonas Example and Priya Example are fictional; addresses use `example.com`. Calendar and mail queries cover 19–26 October 2026. Preserve the existing browser time. Drive modification times come from Python’s current clock, so they are not fixed by the browser timestamp.

## Privacy pitfalls
Capture only the isolated fictional profile: document text, file URLs, message subjects, bodies and attendee details can disclose private information in a real account. Keep personal terminal history, account identity, credential contents and local user paths out of the frame. Treat fixture Google URLs as displayed references, without opening them.

Captions must retain their demo-data disclosure. Explain that `showcase` commands are documentation requesters, not operations installed by this plugin. The capture exercises reads; it does not demonstrate sending mail or modifying events. In production, Gmail access is opt-in and its read scope permits reading the mailbox; writes require additional authorization and confirmed publish operations.

## Acceptance criteria
- Preserve all eight scene names, commands, captions, order and viewports from the existing plan.
- Show completed, readable results in all five UI scenes and all three CLI scenes. Keep commands and useful output visible without clipping headings or columns.
- Confirm the scene-specific content above during capture review, including the same three files in both parameter cases, three calendar rows, two mail rows and the three metric checks.
- Retain source and revision context in document results and explicit UTC labeling in the calendar result.
- Use argument arrays throughout. Terminal actions already wait for completion; no individual table-cell waits are needed.
- Static validation against the supplied plan contract: root format, existing relative bootstrap, ISO8601 browser time, eight unique lowercase scene names, allowed surfaces, local routes, captions under 180 characters, positive viewports and timeouts, and supported terminal steps all conform. The returned TOML preserves the existing file verbatim. No parser, bootstrap, capture, import or network operation was run; rendered acceptance remains to be verified during explicit capture.
