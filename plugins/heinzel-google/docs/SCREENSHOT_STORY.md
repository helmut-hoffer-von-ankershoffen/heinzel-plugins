## Audience and outcome

For someone deciding whether Google Workspace belongs in their Heinzel setup: see a fictional launch meeting arrive in Core’s agenda and calendar, inspect the selected executable, and explore sample Drive, Docs, Sheets, and Gmail results. The gallery shows adapter behavior with offline replies; it does not establish a real sign-in, live Google access, or a successful write.

## Scenes

1. **Next up, at a glance** — A dark Core agenda shows the fictional launch review in the footer. This makes the calendar integration useful without opening Google Calendar.
2. **The week takes shape** — Open the Core calendar in light appearance to see the fictional launch week. This is a different, useful state of the same calendar flow, not a duplicate footer capture.
3. **Know the selected source** — On a phone-sized dark view, inspect the fictional executable’s selected command, native binary and digest. The view itself explains that a digest proves byte continuity, not publisher identity or account access.
4. **Find launch files as JSON** — Run the real `google files` operation with a three-day window and a name argument against fictional replies.
5. **Try a wider window** — Run the same operation with seven days. The fixture returns the same canned file list, so this demonstrates the invocation rather than proving Google’s filtering.
6. **Read the launch plan** — A fixture-only requester renders a fictional Doc through the Google documents adapter.
7. **Read the metrics** — The same requester renders a fictional Sheet as a table through that adapter.
8. **Read the message** — A fixture-only requester renders a fictional Gmail message through the mail adapter.

## Fictional fixtures

`docs/screenshot_fixture.py` supplies `DemoGws`, an inert fictional executable, dummy credential files, fictional Workspace replies and a documentation-only `showcase` module. It binds the real Google adapters in an isolated profile; its `login` explicitly fails and its `run` returns canned responses. The moving calendar anchor supplies upcoming events; the separate fixed October 2026 events support the fixture’s `showcase week` operation. The existing plan is preserved because its eight scenes already demonstrate useful behavior in two actual Core calendar states, the plugin view and CLI results.

## Source-bound UI surface inventory

- `pyproject.toml` declares both `heinzel.modules` and `heinzel.connected_sources` entry points as `heinzel_google`. `src/heinzel_google/__init__.py` is therefore the declaration to inspect for both: it registers settings, services, document/calendar/mail providers, operations, setup, info and health; conditional captured-read, write and draft-append services depend on host support and source activation.
- **Plugin feature UI:** `src/heinzel_google/__init__.py` declares the `source-review` action, `Navigate(path="/?panel=google:source-review")`, and ABI-1 view; `src/heinzel_google/views/index.js` declares the actual panel and its identity and digest disclosure. Its `source_review` operation explicitly supports CLI and web. This is a real plugin view, not an invented route.
- **Core feature UI:** `README.md` and the existing `docs/screenshots.toml` identify the Core agenda/footer and calendar week fed by the calendar capability; `src/heinzel_google/__init__.py` registers `GoogleCalendar`, and `docs/screenshot_fixture.py` supplies events. The footer and opened calendar are distinct states of the Core feature. The supplied plugin source does not declare the Core implementation or independently establish every Core route or control; capture must verify the documented controls and actual rendered content.
- **Other Core-rendered possibilities:** `info`, private `files`, setup, `system_info`, offline health and live connector health are declared in `src/heinzel_google/__init__.py`; `src/heinzel_google/_setup.py` supplies interactive setup prompts. These contributions may be rendered by Core, but the supplied source does not establish their complete web presentation or routes. `README.md` documents CLI entry points; it does not prove they are terminal-only. No plugin channel, approval UI or footer contribution is declared in the inspected registration. Captured writes and approvals are host-mediated services, not evidence of a plugin-owned approval screen (`src/heinzel_google/_document_write.py`, `README.md`).
- **External provider UI:** Google’s browser sign-in and consent are external, invoked conditionally by setup (`src/heinzel_google/_setup.py`); they are not represented as Heinzel screens or exercised by the fixture.
- **CLI:** The plan uses native CLI captures for `google files` and fixture-only `showcase` operations, without claiming those behaviors are exclusively terminal-only. `src/heinzel_google/__init__.py` declares `files` private and read-only; the existing gallery and README document its invocation. `docs/screenshot_fixture.py` declares `notes` and `message_content`; they are not shipped plugin commands.
- **Evidence limit:** The README’s captured-write discussion describes source-only and installed-wheel coverage while explicitly withholding real-account and workflow acceptance. This gallery must not imply those outcomes or manufacture an approval screen.

## Privacy pitfalls and acceptance criteria

Normal presentation fictionalization is explicitly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail. An independent reviewer must inspect every image and transcript for paths, account names, email addresses, hostnames, tokens and other identifying details before publication. Fictional fixture addresses and titles must remain recognizable as example data.

Capture genuine rendered UI and native CLI output using the existing bootstrap only during explicit capture. Verify that the agenda and opened week each show meaningful fictional events, that the source review shows its real disclosure, and that light and dark appearances are actually applied. Check both file-query parameter cases and the Doc, Sheet and mail results against the fixture; do not claim that canned responses prove server-side filtering. Reject duplicate captures, caption-only differences, terminal output presented as feature UI, forged HTML, unexpected identities, errors or missing controls. Review every image and transcript independently; no live account, login, approval or provider write is implied. The TOML below has been checked against the requested structure by inspection; no project code or capture was executed.
