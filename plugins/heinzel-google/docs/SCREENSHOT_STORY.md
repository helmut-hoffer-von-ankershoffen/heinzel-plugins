## Audience

Someone considering Google Workspace as Heinzelmännchen’s documents, calendar and mail provider, who wants to see useful everyday results and understand what the integration does before connecting an account.

## Outcome

Show a fictional launch team moving from an upcoming meeting to its calendar context, then inspecting the selected Google source and querying recent files. The remaining examples show how a requesting workflow can read a document, spreadsheet and message through the adapters. The gallery demonstrates offline adapter behavior, not a successful Google sign-in or live provider access.

## Scenes

1. **Upcoming review — dark UI.** Open the footer’s calendar summary to see the fictional launch review as the next meeting. This is a useful Core feature surface supplied with events by the Google calendar adapter.
2. **Calendar week — light UI.** Open the Core calendar pane and see the fictional launch-day meetings in context. This is a second meaningful state of the real calendar flow, not a duplicate or a caption change.
3. **Source review — dark UI.** Inspect the fictional selected executable and its digest in the plugin’s actual review panel. The panel explicitly says the digest does not authenticate the publisher and that review neither accesses the account nor grants a read.
4. **Recent launch files — CLI JSON.** Query three days with a name parameter and show structured fictional results from the actual `google files` operation.
5. **Recent files — CLI default presentation.** Query seven days without the name parameter. The fixture returns the same fixed file list, so this demonstrates a second invocation, not proven server-side filtering.
6. **Launch plan — CLI.** A documentation-only requester reads a fictional Doc through the documents adapter.
7. **Launch metrics — CLI.** The same requester reads a fictional Sheet, including its readiness table, through the documents adapter.
8. **Launch message — CLI.** The documentation-only requester reads the body of a fictional Gmail message through the mail adapter.

## Fictional fixtures

`docs/screenshot_fixture.py` is the existing bootstrap. Its `DemoGws` supplies fictional vendor replies, rejects login, and does not start a Google process. It binds the real adapters to a documentation-only `showcase` module; `showcase notes` and `showcase message-content` are fixture commands, not installed Google plugin commands. The fixture creates a stable, relative-to-capture calendar anchor, so no fixed browser time is imposed. Its file-list response is fixed regardless of query parameters. Example names, addresses, content, revisions, and the inert executable identity are demonstration data.

## Source-bound UI surface inventory

- `pyproject.toml` declares both `heinzel.modules` and `heinzel.connected_sources` entry points as `heinzel_google`. Their target is `src/heinzel_google/__init__.py`, which imports `module` from `src/heinzel_google/_module.py` and declares the services and capabilities. The connected-read service and captured-write/draft-append services are registered only under the feature and host-contract checks in that initializer. `src/heinzel_google/_connected_calendar.py` still describes the service as unregistered; this conflicts with conditional registration in the initializer and must not be presented as proof of an available approval flow.
- `src/heinzel_google/__init__.py` declares `source_review` for CLI and web, the `source-review` action navigating to `/?panel=google:source-review`, and an ABI-1 view. `src/heinzel_google/views/index.js` implements the actual panel and its limitations. This is genuine plugin UI.
- The calendar capability is declared with read and write modes in `src/heinzel_google/__init__.py`; `src/heinzel_google/_calendar.py` implements the adapter. `docs/screenshots.toml` and `docs/screenshot_fixture.py` identify the Core footer summary and calendar pane as the intended real rendered surfaces. Their Core implementation is not among the supplied files, so their exact rendering and accessible controls require capture verification. The two calendar scenes are Core feature UI, not Google’s own interface.
- `info`, `files`, setup, system info, local health and live health are declared in `src/heinzel_google/__init__.py`; sign-in registration is in `src/heinzel_google/_sign_in.py`. Setup prompts are implemented in `src/heinzel_google/_setup.py`. Core may render generic operation, setup, connector, information or Doctor surfaces; the supplied plugin files do not establish their exact routes or controls. Do not infer that these contributions are terminal-only merely because no additional plugin view is declared. The plan uses the existing CLI results without claiming exclusivity.
- `README.md` describes Google’s browser consent and `gws` sign-in. Those are external provider flows, not plugin or Core screens, and the fixture does not exercise them. The source describes confirmed writes and host-owned review/approval, but supplies no verified capture route or fixture for an approval screen. Do not invent one. No plugin channel or footer contribution is declared in the supplied module; the calendar footer is a Core capability-driven surface.
- The fixture’s `showcase` operations and Rich renderers are declared in `docs/screenshot_fixture.py`; their CLI results are documentation-only demonstrations. They must not be labeled as native plugin feature UI or ordinary installed commands.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript. Do not broadly replace hostnames, paths, health text, names or addresses. Check for real account identifiers, credentials, machine paths, hashes or other identifying details; the source-review digest and selected path deserve particular scrutiny. A fictional fixture does not itself establish that surrounding Core chrome is private.

## Acceptance criteria

- Capture all eight distinct scenes using the existing bootstrap, with applied dark and light views. Verify the footer summary and calendar pane actually show the fictional events; verify the source review is the real ABI-1 panel. Stop and report a failed or unavailable surface rather than substitute a terminal, fabricated HTML, duplicate capture or caption-only change.
- Show both actual `google files` parameter cases, and label the fixed response and fixture-only requester commands accurately. Verify the document, sheet and message results contain their fictional content. Do not claim live filtering, account connection, approval, writes or provider acceptance.
- Inspect every image and transcript independently for privacy, including all Core chrome and diagnostics. Apply only the two verified presentation mappings stated above; unknown identities fail review. Confirm mappings preserve health status and all other Doctor detail.
- The TOML below preserves the existing useful plan. It has been checked structurally against the supplied format and constraints by inspection; no project code, fixture, capture, network request or TOML parser was executed, so runtime controls and captures remain unverified.
