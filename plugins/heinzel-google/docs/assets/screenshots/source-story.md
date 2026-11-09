## Audience

Someone deciding whether Google Workspace fits into their Heinzel workflows, especially someone who wants to see a calendar in context and inspect a selected executable before connecting an account.

## Outcome

Show a fictional launch week flowing through the Google calendar adapter into Core, followed by a source identity review and concrete document and mail reads. The gallery demonstrates adapter behavior with fabricated Workspace responses; it does not establish a successful Google sign-in, live filtering, provider write, or end-to-end workflow acceptance.

## Scenes

1. **Upcoming review, dark:** The Core footer identifies the fictional next meeting. This makes the calendar connection useful at a glance.
2. **Launch week, light:** Open the actual Core calendar from that footer and wait for the fictional review in the current week. The calendar pane shows the meeting in the context of the week.
3. **Source review, dark mobile:** Open the plugin's actual source-review panel and inspect the fictional selected executable and digest. The panel itself explains that the digest is not publisher authentication or a grant.
4. **Three-day files query:** Show structured output for the actual `google files` operation with a name filter and fictional replies.
5. **Seven-day files query:** Show the same actual operation with a different useful parameter case. The fixed fixture response demonstrates invocation, not server-side filtering.
6. **Launch plan:** Read a fictional Doc through the adapter with the fixture-only `showcase notes` operation.
7. **Launch metrics:** Read a fictional Sheet through that same fixture-only operation, showing a meaningfully different document result.
8. **Launch message:** Read a fictional Gmail message through the adapter with the fixture-only `showcase message-content` operation.

## Fictional fixtures

`docs/screenshot_fixture.py` provides the existing isolated bootstrap, a `DemoGws` transport, fictional event, file, document, sheet and mail data, and the documentation-only `showcase` module. It binds the real adapters to fabricated provider responses and does not sign in or start a Google process. The current-day calendar anchor is created in isolated fixture state; the fixed historical launch week is also present. The file-list response is fixed regardless of query parameters.

The private offline draft uses the toolkit's standard masking of the isolated profile path. Its explicit prepared interpreter has no additional path or hostname mapping authority. Unknown identities fail the capture scan. An independent reviewer still inspects every image and transcript.

## Privacy pitfalls

The source-review panel displays a command path, binary path and SHA-256 digest. Even a fictional executable can expose its real temporary parent path. Calendar attendees, mail addresses, document URLs and source revisions can also appear. Inspect every image and transcript independently for real paths, hostnames, account identities, credentials and unintended content. The inert executable's digest illustrates continuity for the fictional bytes.

## Acceptance criteria

- Capture the actual Core footer and opened calendar as two visibly different, useful UI states, plus the actual plugin source-review panel. Show applied dark and light appearances.
- Capture both real `google files` parameter cases and identify all `showcase` commands as fixture-only. Do not claim the fixed file replies prove filtering.
- Use the existing bootstrap and native capture surfaces. Reject forged HTML, terminal output presented as feature UI, duplicate images, and scenes distinguished only by captions.
- Preserve the SDK's health statuses and details. Inspect every image and transcript independently for private paths, identities and unintended content.
- Keep all data fictional, disclose that no Google account is contacted, and avoid claims of live sign-in, provider writes or accepted workflows.
- Confirm the rendered content, applied themes, legibility and distinct feature states in the private draft.

## Source-bound UI surface inventory

- **Entrypoints:** `pyproject.toml` declares both `heinzel.modules: google = "heinzel_google"` and `heinzel.connected_sources: google = "heinzel_google"`. `src/heinzel_google/_module.py` declares the `google` module; `src/heinzel_google/__init__.py` contains its registrations.
- **Plugin feature UI:** `src/heinzel_google/__init__.py` declares the `source-review` action navigating to `/?panel=google:source-review` and a view backed by `src/heinzel_google/views/index.js`. Its private, read-only `source_review` operation explicitly has CLI and web heads. The view shows the selected command, executable, digest and launcher type, or a configuration prompt.
- **Core feature UI:** The existing plan in `docs/screenshots.toml` identifies the Core footer and calendar flow; `docs/screenshot_fixture.py` supplies calendar events through the registered `calendar` capability. These are genuine Core-rendered feature states, not plugin-owned pages. The source-review panel provides another genuine UI surface.
- **Operations and generic surfaces:** `src/heinzel_google/__init__.py` declares `info`, private read-only `files`, setup, system info, offline health and live health contributions. These can feed host-rendered operation, setup, information or diagnostic surfaces; the provided plugin source does not establish their exact Core routes or rendered controls. Do not infer terminal-only status from the absence of a plugin view. The CLI captures use declared commands, not substitutes for a claimed lack of UI.
- **Capabilities and approval:** The same registration provides documents read, calendar read/write and mail read/write. Conditional captured-read, captured-write and draft-append services depend on host APIs and source-only activation. `src/heinzel_google/_document_write.py` and `README.md` describe host-owned review and approval; the provided source does not establish a capture-ready approval screen or fixture-backed write. No approval scene is invented.
- **External provider UI:** `README.md` describes `gws` setup and Google consent; neither is a plugin or Core screen demonstrated by this fixture. No external provider UI is represented.
- **Unresolved evidence:** `src/heinzel_google/_connected_calendar.py` calls its service unregistered in its module docstring, while `src/heinzel_google/__init__.py` conditionally registers it when the required host APIs and source-only activation are present. Treat registration as conditional, not unconditional. The supplied sources do not establish additional channel or plugin footer declarations, nor the exact host rendering of every contribution.
