## Audience and outcome

A person considering the Google Workspace connector can see how a fictional launch day appears in Heinzel’s calendar, inspect the selected Workspace CLI source, and explore real adapter output for files, documents, spreadsheets and mail. The gallery demonstrates offline behavior; it does not establish a successful Google sign-in, live provider access, a write, or a complete workflow.

## Scenes

1. **Next up, in context — dark UI.** Open the footer calendar summary for the fictional launch review. This shows the immediate value of the calendar adapter in an ordinary Core surface.
2. **Plan the week — light UI.** Open Core’s calendar pane and see the fictional launch meetings together. This is a distinct, useful state of the same calendar flow.
3. **Inspect the source — dark UI.** Open the actual Google source review panel and show the fictional selected executable and its digest. The panel explains that a digest is not publisher authentication or permission to read an account.
4. **Find recent files — CLI.** Show the Google `files` operation with a three-day, name-filtered JSON invocation.
5. **Broaden the window — CLI.** Show the same operation with a seven-day window. The fixture returns the same canned file list, so this demonstrates the invocation, not server-side filtering.
6. **Read the launch plan — CLI.** Show a fictional Doc converted by the real adapter, using the documentation-only requester.
7. **Read the metrics — CLI.** Show a fictional Sheet converted by the real adapter through that requester.
8. **Read the message — CLI.** Show a fictional Gmail message body through that requester. These showcase commands are fixture-only, not installed plugin commands.

The existing plan already covers these useful behaviors, so it is preserved below. The UI scenes are genuine Core or plugin UI; the CLI scenes are labeled as terminal output, not presented as feature screens.

## Fictional fixtures and presentation

`docs/screenshot_fixture.py` supplies a temporary fictional profile, an inert selected executable, canned Google responses, example people and launch data, and a `DemoGws` transport that refuses sign-in and does not start Google. It uses the real adapters and adds documentation-only `showcase` operations. Its calendar includes a current-time anchor as well as fixed October 2026 events; actual captures must confirm that each scene contains the intended meeting.

Normal presentation fictionalization must be explicit: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript.

## Privacy pitfalls

Inspect paths, hostnames, account names, addresses, tokens, executable identities, document contents, browser chrome and terminal transcripts. The fixture’s example addresses and names are fictional, but fixture isolation alone does not prove that every rendered surface is free of real data. Apply only the verified mappings above; do not guess at or conceal unknown identities. The source review digest demonstrates byte continuity, not publisher authentication. Do not portray a local health check as a live connection or imply that canned responses prove Google filtering, consent or writes.

## Source-bound UI surface inventory

- **Declared entrypoints:** `pyproject.toml` declares both `heinzel.modules` and `heinzel.connected_sources` as `google = "heinzel_google"`. `src/heinzel_google/__init__.py` exposes `module`, defined as `Module("google", ...)` in `src/heinzel_google/_module.py`. The connected-source declaration points to the same package; conditional registration of `GoogleConnectedReadService`, `GoogleDocumentWrites` and `GoogleDraftAppends` depends on host APIs and captured-source activation in `__init__.py`. The docstring in `src/heinzel_google/_connected_calendar.py` calls its service unregistered, while `__init__.py` conditionally registers it: availability depends on that actual loading path and remains to be verified for the capture host.
- **Plugin feature UI:** `src/heinzel_google/__init__.py` declares the `Google source review` action navigating to `/?panel=google:source-review`, a `source-review` view, and a private read-only `source_review` operation with CLI and web heads. `src/heinzel_google/views/index.js` renders its configured, loading and unconfigured states. This is a real plugin view, not a route inferred from the plugin name.
- **Core feature UI:** `__init__.py` provides calendar read/write, documents read, and mail read/write capabilities. `docs/screenshot_fixture.py` binds their fictional adapters and specifically supplies calendar events for Core’s agenda and calendar-week UI. The existing plan identifies the footer calendar summary and calendar pane on `/`; capture must verify those controls and their contents. Other capability-driven Core surfaces may exist, but their exact routes and fixture states are not established by these supplied files.
- **Operations and generic surfaces:** `__init__.py` declares `info`, private `files`, setup, system info, local health and live health contributions; `src/heinzel_google/_service.py` implements the information and checks. Core may render operation, setup, information or Doctor surfaces, but these source files do not establish a capture-ready route or exact UI state for each. `files` being private does not prove it is terminal-only. The plan uses its genuine CLI invocation without claiming there is no web rendering.
- **Sign-in and approvals:** `src/heinzel_google/_sign_in.py` registers `module.sign_in(grants=GRANTS)(GoogleSignIn)` and describes progress and host-side completion; `README.md` describes a connector command and a later sign-in button. Google’s consent/browser page is external provider UI, not a plugin screen. `src/heinzel_google/_document_write.py` says the host owns approval; the supplied source does not establish a fixture-backed approval screen. Do not invent one or represent source review as approval.
- **Channels and footer:** No plugin channel or footer declaration is present in the inspected package declarations. The calendar footer in the existing plan is a Core-rendered capability surface, not a plugin-declared footer. No separate plugin navigation route is declared beyond the source-review action.
- **Terminal output:** `docs/screenshot_fixture.py` declares the `showcase` operations and Rich renderers for documents, calendar and mail. The selected showcase captures are native CLI results of that fixture, not evidence that the underlying capabilities lack UI. `README.md` documents `hz google files` and its parameters.

## Acceptance criteria

- Capture all eight distinct planned scenes with the existing bootstrap only during an explicitly requested capture. Verify the two calendar states contain the intended fictional event and that light and dark appearances are actually applied.
- Confirm the source-review panel is genuine and its displayed details match the fictional selected executable. Confirm the two file commands have different arguments and label the fixture’s unfiltered replies accurately.
- Preserve the distinction between installed Google commands and fixture-only showcase commands. Reject duplicate captures, caption-only changes, forged HTML and terminal output labeled as feature UI.
- Independently inspect every image and transcript for privacy and accuracy, including the narrowly specified presentation mappings. Fail on unknown identities. Do not claim live account, provider-write, privacy or workflow acceptance from this offline gallery.
- The TOML below has been checked against the supplied field rules by inspection; it has not been parsed, executed or capture-tested because this request prohibits code execution.
