## Audience

Someone considering Google Workspace integration who wants to see what Heinzelmännchen can do with calendar events, documents, spreadsheets, and mail before connecting an account.

## Outcome

A fictional launch week makes the adapter’s value concrete: an upcoming meeting appears in Core, the calendar opens into a week view, and real adapter conversions produce useful file, document, spreadsheet, and mail results. The source-review panel explains what executable was selected without implying that its digest authenticates a publisher or grants account access.

## Scenes

1. **Upcoming launch review — dark UI.** The Core home agenda shows the next fictional meeting. This is the closed state of the same calendar flow used in the next scene.
2. **Launch week — light UI.** Open the genuine Core calendar from the home footer and show the fictional launch review among the week’s events.
3. **Google source review — dark UI.** On a phone-sized viewport, open the plugin’s actual source-review panel. Its selected command, native executable, digest, and direct-executable description are fixture identity evidence, not authentication.
4. **Recent launch files — CLI.** Show the actual `google files` operation with a three-day name query and JSON output.
5. **A wider file window — CLI.** Show the same operation with seven days. The fixture returns fixed files, so this demonstrates the invocation, not server-side filtering.
6. **Launch plan — CLI.** Read the fictional Doc through the documentation-only `showcase notes` requester and the Google documents adapter.
7. **Launch metrics — CLI.** Read the fictional Sheet through the same requester, showing its formatted table.
8. **Launch message — CLI.** Read a fictional Gmail message body through the fixture requester and Google mail adapter.

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap. Its `DemoGws` supplies fictional Drive, Docs, Sheets, Calendar, and Gmail replies; it refuses login and does not execute Google’s CLI. It binds the real adapters and adds a documentation-only `showcase` module. The current-window calendar entries are anchored relative to capture time; the separate fixed October week is not evidence of live data. The file-list fixture returns the same rows regardless of query, so do not claim the results prove filtering.

Normal presentation fictionalization must be disclosed: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript.

## Privacy pitfalls

Inspect every image and transcript independently for account names, addresses, local paths, hostnames, credentials, tokens, URLs, and other identifying details. Only the explicitly verified mappings above are permitted; unknown identities fail review. The fixture’s `example.com` addresses and fictional content are deliberate demo data, but their presence does not establish privacy acceptance. Do not run a live connector test, sign in, or suggest that the gallery proves real-account access or a successful write. A digest demonstrates byte continuity only.

## Source-bound UI surface inventory

- `pyproject.toml` declares both `heinzel.modules: google = heinzel_google` and `heinzel.connected_sources: google = heinzel_google`. Their actual target, `src/heinzel_google/__init__.py`, registers documents, calendar, and mail providers; conditional captured-read, document-write, and draft-append services depend on host capabilities and source loading. `src/heinzel_google/_connected_calendar.py` describes host-owned approval; its introductory description says unregistered while `__init__.py` conditionally registers it. Treat availability and the exact host review UI as unresolved, not as a demonstrated screen.
- `src/heinzel_google/__init__.py` declares the private CLI/web `source_review` operation, `Google source review` action, and `source-review` view at `/?panel=google:source-review`; `src/heinzel_google/views/index.js` defines its actual contents. This is plugin-owned UI.
- The existing `docs/screenshots.toml` documents the Core home agenda and calendar-week flow, and `docs/screenshot_fixture.py` supplies the calendar events. These are Core feature UI fed by the Google adapter, not Google Calendar’s own interface. The plan retains that flow and adds its useful agenda state in dark mode. Capture must verify the named controls and rendered content.
- `src/heinzel_google/__init__.py` declares `info`, private `files`, setup, system-info, local health, and live health contributions. Core may render operations, setup, information, health, or approvals in generic surfaces; the provided plugin sources do not establish their exact routes or accessible controls. No channel, footer, or additional navigation contribution is declared in the inspected plugin entrypoint. Do not infer terminal-only behavior merely from missing plugin pages. `src/heinzel_google/_setup.py` can open external Google sign-in; that provider UI is outside this fixture and is not a plugin screen.
- `docs/screenshot_fixture.py` explicitly declares the `showcase` CLI requester and its renderers for document, calendar, inbox, and message results. The planned CLI captures are native command results, not feature UI. The provided sources do not establish that every such result lacks a Core-rendered counterpart.

## Acceptance criteria

- Capture three distinct genuine UI states: the useful Core agenda and week view plus the plugin source-review panel. The two calendar states must show meaningful different information, not merely a caption or theme change. Apply light and dark appearances as specified.
- Capture the listed CLI results as terminal output, including both parameter cases of `google files`; never present a terminal image as feature UI or forge HTML.
- Confirm the week and agenda show fictional events and that document, spreadsheet, and mail results match the fixture. If Core controls, routes, fixture behavior, or accessible names differ, stop and revise from observed source evidence rather than inventing a screen.
- Review every image and transcript independently under the privacy rules above. Keep SDK health status and all non-mapped Doctor details intact; reject unknown identities. Label all captions as demo data.
- This TOML has been checked against the requested format by inspection. It has not been parsed or capture-tested because code execution was prohibited; validate it with the screenshot tooling only during an explicitly authorized capture.
