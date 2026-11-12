## Audience
People considering a Google Workspace connector for Heinzelmännchen who want to see what it can retrieve before setting up an account.

## Outcome
Follow a fictional launch from finding its files to reading a plan, checking meetings and scanning mail. The gallery shows the app terminal and command-line output, with structured JSON and a spreadsheet table for people who want to use the results elsewhere.

## Scenes
1. **Find launch files:** Search the past three days by name in the app terminal.
2. **Broaden the search:** Try a seven-day search without a name filter. The fixture deliberately returns the same files, so this does not demonstrate filtering differences.
3. **Read the plan:** Show the fictional document’s goals, owners and next milestone.
4. **Review the week:** Show the fictional calendar events and attendee names.
5. **Scan the inbox:** Show a focused fictional Gmail query and its results.
6. **Use structured output:** Show the file search as JSON in the CLI.
7. **Read metrics:** Show the fictional spreadsheet as a table in the CLI.
8. **Read a message:** Show the body of a fictional launch message in the CLI.

## Fictional fixtures
The existing `docs/screenshot_fixture.py` supplies fictional Google responses and a documentation-only `showcase` requester. The `showcase` commands demonstrate the installed adapters through this fixture; they are not presented as built-in Google plugin commands. Its file-list response is fixed for both search cases, while modified times are generated at capture time.

## Privacy pitfalls
Use an isolated fictional profile and fixture responses, never a connected account or real document, calendar or mail content. Check captures for account identifiers, credentials and unrelated terminal history. Fixture addresses use `example.com`. Do not imply that the gallery proves live Google connectivity, write permissions or confirmation flows; Gmail and writes require their own opt-in setup.

## Acceptance criteria
- All eight scenes show readable results, with captions identifying fictional or fixture data.
- Both file-search parameter cases appear in the app terminal, and the caption explains their identical fixture results.
- The plan, calendar, inbox, JSON, spreadsheet and message scenes display the corresponding fixture output without clipping essential content.
- The `showcase` requester is identified as documentation-only, and no invented plugin panel or live Google result is implied.
- The plan has been checked against the requested structure by inspection; capture and executable TOML validation were not run because this request prohibits code execution.
