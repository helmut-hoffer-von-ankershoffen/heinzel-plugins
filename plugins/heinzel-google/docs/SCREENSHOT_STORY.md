## Audience
People deciding whether Heinzelmännchen can bring Google Workspace information into their workflows, especially launch or project coordination.

## Outcome
Show how a fictional launch team can find recent files, read a plan and metrics, and review meetings and mail. The native app terminal and CLI demonstrate the plugin’s adapters using local replies; they do not demonstrate a live Google connection.

## Scenes
1. **Find launch files:** A three-day, name-filtered Drive listing in the app terminal.
2. **Broaden the search:** A seven-day listing without the name filter in the app terminal. The fixture returns the same fictional files for both cases, so this illustrates the available parameters, not their filtering effect.
3. **Read the plan:** The fixture’s requester reads a fictional Google Doc through the documents adapter.
4. **See the week:** The requester displays fictional meetings and attendees through the Calendar adapter.
5. **Scan the inbox:** The requester displays fictional launch messages through the Gmail adapter.
6. **Use structured output:** The CLI presents the fictional file listing as JSON.
7. **Read metrics:** The CLI renders a fictional Sheet as a table.
8. **Read a message:** The CLI displays a fictional message’s next actions.

## Fictional fixtures
The existing `docs/screenshot_fixture.py` supplies fictional Drive, Docs, Sheets, Calendar and Gmail replies and registers the documentation-only `showcase` requester. Its people, addresses, messages and launch results are examples. The `google files` operation belongs to the plugin; `showcase` commands are fixture helpers, not advertised plugin commands. The bootstrap runs only during an explicit capture.

## Privacy pitfalls
Capture only with the isolated fixture profile: real file names, document text, meeting attendees, email addresses and message bodies could reveal private information. Do not substitute real credentials or account data. The fixture’s successful responses do not prove sign-in, network access, Google permissions or write behavior. Mail access and calendar/mail writes require separate opt-in in actual use.

## Acceptance criteria
- All eight scenes show legible, completed results with captions identifying demo data; the first five are app-terminal views and the last three are CLI captures.
- Both `google files` parameter cases appear, without claiming the fixture proves filtering.
- The plan, metrics, calendar and mail scenes visibly contain the fictional content supplied by the existing fixture.
- No screenshot presents `showcase` as a shipped Google command or implies a live account was contacted.
- Review captures for accidental personal data and clipped output. TOML syntax and the supplied scene fields have been checked by inspection; capture and runtime validation were not performed because code execution was prohibited.
