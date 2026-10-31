# Bring the files, schedule and mail you need into one workflow.

Lead with useful Workspace content: recently changed files, readable notes, upcoming meetings and a focused mail
query. Show actual installed adapter results in the real app terminal and CLI. This plugin has no standalone
Google Drive, Gmail or calendar product screen; do not draw one for a screenshot.

## Runtime and command boundary

`hz google files --days 3 --name Launch` is a real released operation: it lists recently changed Google Docs and
Sheets. `hz google info` is metadata. There are no released `hz google calendar`, `hz google read` or `hz google mail`
commands. For capability demonstrations the bootstrap must register a **fixture-only** `showcase` requester using
public `Documents`, `Calendar` and `Mail` APIs. Adapt `prep()` in
[the capability tests](../tests/integration/capability_test.py). Label every `hz showcase ...` command as a local
demonstration, not a command added by the Google distribution.

## Required scenes, in gallery order

| Scene | Surface and actual action | Visible result and caption | Why it matters |
| --- | --- | --- | --- |
| Find the relevant work | UI terminal: `hz google files --days 3 --name Launch` | Three fictional Docs/Sheets with descriptive titles, changed times and types; render the actual Drive listing. Caption: “Recently changed launch files in the app terminal — fictional Workspace fixture.” | Gives an immediate answer to “what changed?” |
| Read the plan | UI terminal: proposed fixture command `hz showcase notes launch-plan` | Actual `Documents.read` Markdown: title, short checklist, owner names and revision. Caption: “Google Doc content ready for a workflow — local fictional plan.” | Shows the adapter reads useful content, not just links. |
| Prepare for the week | UI terminal: fixture command `hz showcase week` | Actual `Calendar.events` output with a launch review and two one-on-ones, local times and named attendees. Caption: “Upcoming meetings and their context — fictional calendar through the Google adapter.” | Explains the calendar capability with recognizable work. |
| Read structured files | CLI: `hz google files --days 3 --name Launch --json` | Compact complete Docs and Sheets metadata, with useful titles. Caption: “Changed Docs and Sheets as structured data for scripts — fictional files.” | Shows useful production CLI behavior beyond help. |
| Read the sheet | CLI: fixture command `hz showcase notes launch-metrics` | Actual `Documents.read` conversion of a Google Sheet into a small table of release metrics. Caption: “A Sheet becomes a readable table through the documents capability — local fixture.” | Shows that spreadsheets are supported, not just Docs. |
| Focus the inbox | UI terminal: fixture command `hz showcase inbox` | Two messages returned by the real Gmail adapter and one opened body with next action. Caption: “A focused mail query and its message content — fictional inbox, mail explicitly bound.” | Explains opt-in mail access through useful results. |
| Optional writes | CLI: fixture-only `hz showcase draft-mail` and `hz showcase create-event` in one narrowly rendered local demonstration command | Real `Mail.create_draft` and `Calendar.create_event` results against fake gws only, with draft subject and event time. Caption: “Optional draft and calendar write adapters against a local fixture; no mail sent or live event created.” | Covers optional write capabilities honestly. |

Keep at most eight captures. The optional write scene is required before claiming the gallery covers the whole
read/write plugin; omit that claim if the demonstration is not implemented. Do not represent a direct adapter
invocation as a confirmed production publish flow. Production writes are opt-in and performed through the host's
confirmation/publish operations; no capture should request real OAuth scopes, send mail or change a real calendar.
A local contract dry-run can support a later workflow scene but must not imply a report was generated.

## Fixture entry points

[conftest.py](../tests/conftest.py) provides `FakeGws`, `file`, `doc`, `json` and `output` helpers. Bind its behavior
at the gws runner boundary, retaining `GoogleDocuments`, `GoogleCalendar`, Gmail and all conversion code.
[The document tests](../tests/unit/docs_test.py), [sheet tests](../tests/unit/sheets_test.py),
[calendar tests](../tests/unit/calendar_test.py) and [mail tests](../tests/unit/mail_test.py) supply exact response
shapes. Use fictional file IDs `launch-plan` and `launch-metrics` where supported by the parser, or valid synthetic
alphanumeric IDs where it requires them; requester aliases can map the readable names to those fixture IDs.

Required vendor routes include `drive files list/get`, `docs documents get`, `sheets spreadsheets get`,
`calendar events list`, `gmail users messages list/get` and, only for the write scene, draft create/get and event
insert. Use `primary` only in the fixture. Populate `modifiedTime` from the capture's injected fixed clock or from
its isolated fixture clock so the three-day query actually matches. Do not hardcode old timestamps and silently
bypass filtering. User configuration binds documents/calendar to Google; mail is bound explicitly only for its
scenes. Fake sign-in files contain no usable credentials and exist only in the temporary profile.

## Accessible capture and acceptance

- Every UI scene opens `button` **Open a terminal**, then **Full screen**, and waits for the expected file title,
  document heading, calendar title or message subject after the actual command finishes.
- Assert each screenshot's data comes through the real adapter and the expected fake gws routes. The complete
  gallery covers Docs, Sheets, Drive metadata, calendar and mail; optional writes require local fixture evidence.
- All people and addresses are fictional `example.com` identities. Strip real environment credentials and never
  use the developer's gws config/keychain. No browser token, hostname, absolute path or live conference passcode
  enters the image, transcript or metadata. Unexpected requests fail; all network is loopback-only.
- Results fit the terminal without clipping; the first capture has three meaningful rows, not “No files”. Keep
  captions explicit about fictional fixtures. Review thumbnails and full images, not just successful exit codes.

## Current captured scope

The fixture-only requester fixes the demonstration week and mail query internally. Its `message-content` operation
reads the first matching mail body. The seven-scene gallery covers Drive metadata, Docs, Sheets, Calendar and
Gmail reads through the actual installed adapters. Optional write demonstrations are deferred: no captured scene
claims to demonstrate sending mail, calendar mutation or the entire read/write feature set.
