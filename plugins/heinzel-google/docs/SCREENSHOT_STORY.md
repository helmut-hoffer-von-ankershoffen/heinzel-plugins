## Audience

Someone considering Google Workspace as a Heinzelmännchen provider who wants to see what appears in everyday use, what can be inspected locally, and how a file query looks before connecting an account.

## Outcome

Follow a fictional launch team from an upcoming meeting to its calendar week, inspect the selected Google Workspace CLI source, and explore fictional Workspace files and content in the native terminal. The gallery demonstrates adapter conversions using fixture replies; it does not demonstrate a real Google connection or write.

## Scenes

1. **Upcoming review — dark UI.** Open the footer calendar summary to see the fictional launch readiness review as the next event.
2. **Calendar week — light UI.** Open the Core calendar pane and see the fictional launch meetings together. These are distinct, useful states of the calendar flow.
3. **Source review — dark UI.** Inspect the fictional selected executable and digest in the actual Google source review panel. The panel explains that a digest is continuity information, not publisher authentication or permission to read.
4. **Launch files as JSON — CLI.** Query three days of fictional replies with a name argument and structured output.
5. **Launch files over a week — CLI.** Run the same actual Google operation with a different time window. The fixture returns fixed files, so this illustrates invocation, not verified filtering.
6. **Launch plan — CLI.** Read a fictional Google Doc through the adapter using a documentation-only requester.
7. **Launch metrics — CLI.** Read a fictional Sheet through that requester.
8. **Launch mail — CLI.** Read a fictional Gmail message body through that requester.

The existing plan already covers these useful behaviors, so it is retained. CLI images must be labeled as terminal results, not feature UI. The source review is an additional trust-oriented panel, not a substitute for the two calendar scenes.

## Fictional fixtures

`docs/screenshot_fixture.py` supplies `DemoGws`, fictional launch meetings, files, document and sheet content, and mail. It binds the real adapters to fictional responses and declares the documentation-only `showcase` operations; it explicitly refuses sign-in and does not start a Google process. Its current-day calendar anchor is generated in isolated fixture state, so the existing plan deliberately does not freeze `browser_time`. The fixture's fixed Drive response does not establish that server-side name or date filtering works.

## Source-bound UI surface inventory

- `pyproject.toml` declares both `heinzel.modules` and `heinzel.connected_sources` entry points as `google = "heinzel_google"`. `src/heinzel_google/_module.py` declares the Google module; `src/heinzel_google/__init__.py` registers document, calendar and mail capability providers and their modes. Core's calendar footer and calendar pane are feature UI arising from the calendar capability, as exercised by the existing plan and fixture; they are Core-rendered surfaces, not Google Calendar's external UI. The supplied source does not include Core's rendering implementation, so capture must verify the actual controls and states.
- `src/heinzel_google/__init__.py` declares `source_review` for CLI and web, a `Google source review` action navigating to `/?panel=google:source-review`, and an ABI 1 `source-review` view. `src/heinzel_google/views/index.js` implements its loading, configured and unconfigured states. This is genuine plugin feature UI; the declared action, rather than a guessed plugin route, opens it.
- The same module declares `info`, private read-only `files`, setup, system info, local health and live health. `src/heinzel_google/_setup.py` implements prompted setup; `src/heinzel_google/_service.py` supplies info and checks. These contributions may be rendered by Core; their declarations alone do not prove a particular route or that they are terminal-only. The README documents CLI commands. The two file-query scenes use the native terminal without claiming the operation has no web surface.
- Connected reads and captured writes provide host review data: see `src/heinzel_google/_connected_calendar.py`, `_connected_mail.py`, `_connected_artifact.py`, `_document_write.py` and `_draft_append.py`. `src/heinzel_google/__init__.py` conditionally registers services when the host interfaces and captured-source loader are present. The calendar service file also describes itself as unregistered pending independent review; this wording and the conditional registration need reconciliation against the actual host at capture time. Neither a provider review object nor source inspection proves an available approval screen. No such screen is invented here.
- No plugin channel or footer declaration was found in the supplied plugin source. That does not rule out generic Core surfaces from its capability and operation contributions. Google sign-in and Google's own application screens are external provider UI, not screens supplied by this plugin. The fixture-only `showcase` commands in `docs/screenshot_fixture.py` render useful terminal results; they are not installed plugin operations.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript. Review paths, usernames, hostnames, account identities, tokens, URLs, timestamps and incidental surrounding UI; fixture names and example.com addresses are fictional but do not make other visible data safe. Do not mask unknown identities by guessing or alter a health result.

## Acceptance criteria

- Capture all eight distinct scenes with the existing local bootstrap only during explicit capture; verify the actual Core controls and the selected-source panel. Light and dark appearances must actually be applied.
- Show the two calendar states as real UI, alongside a genuine source-review UI and native CLI results. Reject duplicate captures, caption-only changes, terminal output presented as feature UI, and forged HTML.
- Preserve the demo-data captions, identify fixture-only commands, and do not claim live sign-in, real provider behavior, filtering, approval or writes from this gallery.
- Independently inspect every image and transcript for privacy and truthful status after the narrowly specified fictionalization. Unknown identities fail review.
- The supplied plan is syntactically structured as TOML by inspection; no parser, fixture, capture, source code, network request or import was run. The supplied files do not establish that captures currently pass or that screenshots exist.
