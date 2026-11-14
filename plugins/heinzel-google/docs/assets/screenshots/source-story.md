## Audience

Someone deciding whether Google Workspace can supply useful context to Heinzel: upcoming meetings, recently changed files, document and spreadsheet content, and Gmail content.

## Outcome

A fictional launch story shows a meeting approaching, the surrounding calendar, the selected local Google CLI source, and actual adapter results for launch files, a document, a spreadsheet, and a message. It demonstrates the shape of the integration without implying a real Google sign-in or live provider acceptance.

## Scenes

1. **Upcoming review — dark UI.** The Core footer calendar summary opens on the fictional launch readiness review. It makes the next meeting immediately useful.
2. **Calendar week — light UI.** The Core calendar pane shows the fictional launch-day meetings, providing scheduling context in a second meaningful state of the calendar flow.
3. **Source review — dark UI.** The plugin’s actual source-review panel shows the fictional selected executable and digest, including the panel’s explanation that a digest does not authenticate a publisher.
4. **Launch files, filtered JSON — CLI.** The real `google files` operation requests a three-day window and a name filter, returning fictional Workspace replies.
5. **Launch files, seven days — CLI.** A second parameter case demonstrates the default-style table result. The fixture returns a fixed list, so neither file scene proves Google’s server-side filtering.
6. **Launch plan — CLI.** A documentation-only requester reads the fictional Doc through the Google documents adapter.
7. **Launch metrics — CLI.** The same fixture requester reads a fictional Sheet through that adapter, showing the different returned content.
8. **Mail content — CLI.** A documentation-only requester reads a fictional Gmail message through the mail adapter.

The last three commands belong to the fixture, not to the installed plugin’s public command set. The CLI captures are CLI results, not substitutes presented as feature UI.

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap. Its `DemoGws` returns fictional vendor responses, refuses login, binds the real adapters to an isolated state directory, and supplies the documentation-only `showcase` operations. Its calendar data includes a stable, dynamically anchored upcoming set as well as a fixed fictional launch week. The executable identity is inert fictional bytes; its displayed digest is a digest of those bytes. No Google account is contacted by this fixture. Captures must use the bootstrap as provided, with no invented fixture files.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript.

Review paths, executable names and hashes, hostnames, account identities, email addresses, calendar attendees, document text, message content, timestamps, environment details and terminal scrollback. Only the fixture’s known example identities and content may appear as such. Do not infer that a clean contact sheet or a successful capture proves privacy. The source-review digest is not publisher authentication, and offline results do not establish real sign-in, live reads, writes, approval behavior, or provider filtering.

## Acceptance criteria

- Capture the actual Core calendar footer and calendar pane as distinct useful states, with dark and light appearance applied respectively; capture the real plugin source-review panel. No forged HTML, duplicate captures, or caption-only variants.
- Capture both `google files` parameter cases and the three useful fixture-only adapter results as native CLI output. Captions identify fictional data and fixture-only commands where applicable.
- Verify the images show the expected content and applied appearances, and independently inspect every image and transcript for unknown identities and sensitive data. Apply only the disclosed, verified presentation mappings; otherwise fail review.
- Preserve the source-review panel’s qualification about digest authentication. Do not claim real-account, write, consent or filtering acceptance from these offline captures.
- Retain the existing eight-scene plan: it already covers two genuine feature UI states, a real plugin panel, both useful cases of the files operation, and distinct adapter outputs.

## Source-bound UI surface inventory

- `pyproject.toml` declares both `heinzel.modules` and `heinzel.connected_sources` entry points as `google = "heinzel_google"`. `src/heinzel_google/_module.py` declares `Module("google", ...)`; `src/heinzel_google/__init__.py` registers the documents, calendar and mail capabilities and conditionally registers connected-read, captured-write and draft-append services when the host contracts and captured-source loader are available. These service declarations do not themselves prove a particular visible screen.
- `src/heinzel_google/__init__.py` declares the `source_review` operation with CLI and web heads, the `Google source review` action navigating to `/?panel=google:source-review`, and the `source-review` view. `src/heinzel_google/views/index.js` implements the actual panel and its loading, configured and unconfigured states. This is a genuine plugin UI, though it is source inspection rather than the main Workspace workflow.
- The same `__init__.py` declares `info` and `files` operations, setup, system-info, ordinary health and live health contributions. Core may render generic operation, setup, information or health surfaces; the supplied plugin source alone does not establish their routes or exact presentation. Do not infer terminal-only status from the absence of a plugin Page declaration. The existing plan uses the documented CLI invocations for files and the declared plugin panel, without inventing a generic operation screen.
- `docs/screenshot_fixture.py` supplies fictional calendar data through the registered Google calendar adapter. `docs/screenshots.toml` and `README.md` identify the Core footer calendar summary and Core calendar pane used by the existing plan. These are Core feature UI consuming the adapter, not Google’s external Calendar UI. Their exact availability and labels require capture verification against the actual Core build.
- `src/heinzel_google/_setup.py` and `src/heinzel_google/_sign_in.py`, together with the setup and health declarations, describe setup and sign-in contributions; `README.md` describes Google’s browser consent and a possible later Heinzel sign-in button. The provider consent screen is external Google UI, and the future button is not evidence of a current plugin screen. The fixture deliberately cannot demonstrate sign-in.
- `src/heinzel_google/_connected_calendar.py`, `_connected_mail.py`, `_connected_artifact.py`, `_document_write.py`, and `_draft_append.py` contain review/capture or write services. Core-rendered review and approval surfaces may arise from host workflows, but their exact UI and routes are not established in the supplied source; the fixture does not demonstrate those workflows. No plugin channel or footer contribution is declared in `src/heinzel_google/__init__.py`; the calendar footer is a Core surface consuming the calendar capability.
- `docs/screenshot_fixture.py` declares `showcase.notes`, `showcase.week`, `showcase.inbox`, and `showcase.message_content` with custom terminal renderers. The plan uses three of these fixture-only CLI outputs. Their generic Core web rendering, if any, is unresolved; they are not evidence of installed Google-plugin screens.
- `README.md` describes Docs, Sheets, Slides, Drive, Calendar and Gmail capabilities and reviewed writes, while also stating that offline provider models and fixture captures do not prove real-account or end-to-end write acceptance. The plan’s fictional reads must retain that distinction.
