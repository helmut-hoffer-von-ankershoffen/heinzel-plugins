## Audience

Someone considering Google Workspace as a Heinzelmännchen provider who wants to see what everyday calendar and document access looks like before connecting an account.

## Outcome

Follow a fictional launch team from its next meeting into the Core calendar, inspect the selected Google CLI source, and explore fictional Drive files, a document, a sheet and a message. The gallery demonstrates adapter behavior with offline replies; it does not demonstrate a real Google connection, filtering by Google's servers, or permission to read or write an account.

## Scenes

1. **Next up:** The dark Core footer calendar summary opens a fictional launch review. It makes the immediate value of the calendar connection visible.
2. **The week ahead:** The light Core calendar pane shows the fictional launch meetings together, giving the upcoming event context. This is a different useful state of the calendar flow, not a duplicate or caption-only change.
3. **Know the source:** The dark Google source review panel displays the fixture's selected command, native executable and digest. Its own explanation says the digest checks byte continuity, not publisher authenticity or permission to read.
4. **Find launch files:** The actual `google files` operation returns a fictional three-day named query as JSON.
5. **Broaden the search:** A seven-day `google files` query demonstrates a second parameter case. The fixture returns canned files, so the image must not claim server-side filtering was verified.
6. **Read the plan:** A documentation-only showcase operation renders a fictional Google Doc through the documents adapter.
7. **Read the metrics:** The same fixture operation renders the fictional Sheet, showing a materially different structured result.
8. **Read the message:** A documentation-only showcase operation renders fictional Gmail content through the mail adapter.

The CLI results are terminal captures, not feature UI. The showcase commands are fixture-only requesters and must be identified as such; they are not advertised as shipped plugin commands. No terminal substitute establishes that documents or mail lack a Core UI.

## Fictional fixtures and presentation

`docs/screenshot_fixture.py` binds the real adapters to `DemoGws`, supplies fictional vendor responses and creates isolated fixture state. It supplies launch meetings, example.com participants, a plan, a metrics sheet and messages. Its calendar also creates a current-day anchor for the Core agenda; its Drive list is canned. It neither signs in nor starts a Google process.

Normal presentation fictionalization is explicit: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript.

## Privacy pitfalls

Source review intentionally displays executable paths and a digest; terminal and surrounding Core chrome may expose profile paths, hostnames, account identifiers or other environment details. Only the two verified mappings above are permitted. Do not conceal an unknown identity by inventing another mapping. Treat example addresses, titles and fixture IDs as fictional, and check that no real account, credential, personal path or unrelated application content appears. A source digest is not publisher authentication, and captured-read or write review is not itself approval.

## Source-bound UI surface inventory

- `pyproject.toml` declares both `heinzel.modules: google = heinzel_google` and `heinzel.connected_sources: google = heinzel_google`. Their shared target is `src/heinzel_google/__init__.py`; `src/heinzel_google/_module.py` declares `Module("google", ...)`.
- The plugin-owned view is declared in `src/heinzel_google/__init__.py` by `module.action("source-review", ... Navigate(path="/?panel=google:source-review"))` and `module.view(... name="source-review", source="source-review", ...)`. `src/heinzel_google/views/index.js` implements the actual review panel and its privacy and authenticity explanation. The plan opens it from `/` using the declared action, not a route guessed from the plugin name.
- `src/heinzel_google/__init__.py` declares `info`, private read-only `files`, and private read-only `source_review` operations; the latter explicitly has CLI and web heads. Generic Core operation rendering may provide additional surfaces, but their exact controls and routes are not established by the supplied plugin source. Do not infer terminal-only status for `files` or `info`.
- The same initializer declares `module.setup`, `module.info`, local `module.health`, and `module.health(live=True)`. `src/heinzel_google/_setup.py` supplies setup prompts; `src/heinzel_google/_service.py` supplies info and checks. Core may render these contributions in setup, info or Doctor surfaces; their exact UI is not supplied here. Local health and the separately invoked live Google check must not be conflated.
- `module.provides` in `src/heinzel_google/__init__.py` registers documents read, calendar read/write and mail read/write. The existing `docs/screenshots.toml` identifies the Core footer calendar summary and calendar pane as real surfaces, and `docs/screenshot_fixture.py` explicitly supplies data for them. Their Core implementations are outside the supplied files, so actual capture must verify controls and results. No plugin footer, channel or approval UI is separately declared in the supplied initializer; that absence does not rule out generic Core surfaces.
- Captured-read and reviewed-write services are conditionally registered in `src/heinzel_google/__init__.py` when host APIs and the captured-source loader are available. `src/heinzel_google/_connected_calendar.py`, `_connected_mail.py`, `_connected_artifact.py`, `_document_write.py` and `_draft_append.py` describe review and lease behavior, while the host owns approval. Their exact Core approval screens and fixture support are unresolved, so the plan does not invent them. The `_connected_calendar.py` module and class still describe the service as unregistered, whereas the initializer conditionally registers it; the actual host conditions determine availability.
- Google sign-in and Workspace are external provider experiences, not plugin or Core screenshots. `README.md` and `src/heinzel_google/_setup.py` describe the setup boundary. The supplied fixture deliberately does not exercise those experiences.
- `docs/screenshot_fixture.py` declares the documentation-only `showcase` operations and Rich terminal renderers. Their terminal output is useful evidence of adapter conversions, but does not establish the absence of a feature UI elsewhere.

## Acceptance criteria

- Capture the actual Core and plugin views with the existing bootstrap, including applied dark and light appearances; show at least the two useful calendar states and a useful CLI result. Reject duplicate captures, caption-only changes, terminal output presented as feature UI, and forged HTML.
- Preserve the eight distinct existing scenes and the two `google files` parameter cases. Captions must identify demo data and fixture-only commands accurately; do not imply canned responses prove Google-side filtering.
- Confirm each named control and resulting state during capture. If Core controls, fixture timing or source-review selection differ, report the evidence and revise the plan rather than inventing a screen.
- Independently inspect every image and transcript for unknown identities and secrets. Apply only the disclosed verified presentation mappings; any unknown identity fails review. Verify that no health status or other Doctor detail was changed.
- Treat the TOML below as structurally reviewed against the requested schema, not as an executed capture or runtime validation. The source was read only; no fixture, product code, imports or network calls were run.
