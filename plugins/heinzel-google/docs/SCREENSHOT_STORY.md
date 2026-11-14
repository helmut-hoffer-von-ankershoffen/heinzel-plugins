## Audience

People considering a Google Workspace connector who want to see how their calendar and documents become useful inside Heinzelmännchen, and how to inspect the selected Google Workspace CLI before connecting an account.

## Outcome

Show a fictional launch review moving from a compact calendar summary to a fuller week view, then show the selected-source review and real Google file-list operation. The gallery demonstrates an offline adapter fixture; it does not demonstrate a real Google sign-in, live provider access, or a successful write.

## Scenes

1. **Upcoming review, dark:** A fictional launch review appears in Core’s footer calendar summary. Open it to see the next-meeting detail.
2. **Calendar week, light:** Open Core’s calendar pane and see the fictional launch meetings together. This is a second useful state of the calendar flow, not a duplicate caption.
3. **Source review, dark:** Inspect the plugin’s actual selected-source panel. Its digest demonstrates byte continuity, not publisher authentication or permission to read an account.
4. **Launch files as JSON:** Run the actual Google files operation with a three-day window and a name filter against fictional replies.
5. **Launch files for a week:** Run the same operation with a different seven-day parameter case. The fixture returns fixed file replies, so this illustrates invocation rather than proving Google-side filtering.
6. **Launch plan:** Read a fictional Google Doc through the adapter using the documentation-only showcase operation.
7. **Launch metrics:** Read a fictional Sheet through the adapter using the documentation-only showcase operation.
8. **Mail content:** Read a fictional Gmail message through the adapter using the documentation-only showcase operation. The three showcase commands are fixture commands, not installed Google plugin commands.

## Fictional fixtures

`docs/screenshot_fixture.py` supplies an isolated state directory, inert fictional executable identity, fake credentials files, and `DemoGws` responses. It binds the real adapters and registers a documentation-only `showcase` module; its login method refuses sign-in and its transport does not start Google. The calendar fixture also creates a current-day anchor so the Core calendar can display the fictional events. The existing plan in `docs/screenshots.toml` already demonstrates useful behavior and is preserved.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail. An independent reviewer must inspect every image and transcript, including paths, usernames, hostnames, addresses, URLs, hashes, logs, terminal output, and incidental background content, before publication. Fixture addresses and names are examples; do not infer that every incidental identity is fictional. Do not contact Google or capture real accounts for this story.

## Acceptance criteria

- Capture the actual declared Core calendar surfaces and plugin source-review view, with applied dark and light appearances; no forged HTML, terminal output disguised as feature UI, duplicate captures, or caption-only variations.
- Keep the two distinct calendar states, both useful file-operation parameter cases, and the fixture-only labels on showcase commands. Do not claim fixed fixture responses prove filtering.
- Confirm each capture displays the expected fictional content and the intended theme. Terminal actions already wait for completion; do not add exact waits for individual table cells.
- Treat the selected-source digest as continuity information only. Do not portray it as publisher verification, consent, or a read grant.
- Independently review every resulting image and transcript for privacy and truthfulness. The two narrowly specified presentation mappings do not constitute acceptance.
- Validate TOML and run captures only during an explicitly authorized capture workflow. This plan was reviewed as text; no parser, fixture, plugin, browser, or capture was executed here.

## Source-bound UI surface inventory

- **Declared entry points:** `pyproject.toml` declares `heinzel.modules: google = heinzel_google` and `heinzel.connected_sources: google = heinzel_google`. `src/heinzel_google/__init__.py` imports `module` from `src/heinzel_google/_module.py`, which declares the Google module. The supplied files do not establish how the connected-sources loader resolves the package, so its precise host surface remains unresolved.
- **Plugin feature UI:** `src/heinzel_google/__init__.py` declares the private, read-only web/CLI `source_review` operation, the `source-review` action navigating to `/?panel=google:source-review`, and the ABI 1 `source-review` view. `src/heinzel_google/views/index.js` renders command, native executable, digest, wrapper type, and the continuity/permission caveat. The actual panel route is declared; it is not inferred from the plugin name.
- **Core feature UI:** The calendar capability is registered for read and write in `src/heinzel_google/__init__.py`; `docs/screenshot_fixture.py` binds it and supplies event replies. The existing `docs/screenshots.toml` describes Core’s footer summary and calendar pane. These are genuine feature UI states, although the Core implementation itself is not among the supplied files. Their exact rendering and controls require capture-time verification.
- **Other Core-rendered contributions:** `src/heinzel_google/__init__.py` declares `info`, `files`, setup, system info, local health and live health; `src/heinzel_google/_sign_in.py` registers `GoogleSignIn` with grants. These may be surfaced by Core as operation, setup, connector, info, or Doctor interfaces. The supplied files do not establish their complete routes or presentation, so no invented screens are planned. The local health check does not contact Google; the live check does (`src/heinzel_google/_service.py`).
- **Approvals and writes:** Conditional connected-read, captured-write and draft-append service registration appears in `src/heinzel_google/__init__.py`; `src/heinzel_google/_connected_calendar.py` and `src/heinzel_google/_document_write.py` describe host-owned review and approval boundaries. Their concrete Core approval UI is not supplied or demonstrated by this fixture. `README.md` limits the claimed write support and acceptance; no write or approval scene is invented.
- **External provider UI:** Google OAuth consent and account interaction belong to Google, not this plugin or Core. `README.md` describes that journey; the fixture refuses login and cannot establish its appearance or success.
- **CLI and fixture output:** `src/heinzel_google/__init__.py` declares `files` as a private operation and `info` as an operation. The existing plan uses `hz google files`; actual CLI availability must be verified at capture because private-operation exposure depends on Core. `docs/screenshot_fixture.py` separately declares `showcase.notes` and `showcase.message_content` with renderers. These useful terminal results do not imply that the underlying capabilities lack feature UI. No plugin channel, footer contribution, or navigation declaration beyond the cited action and view was found in the supplied plugin declarations; the calendar footer is a Core surface fed by the capability.
