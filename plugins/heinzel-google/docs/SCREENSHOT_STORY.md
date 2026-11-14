## Audience
People considering Google Workspace as the documents, calendar and optional mail provider for Heinzelmännchen, especially those who want to see useful work before connecting an account.

## Outcome
Show a small, believable launch-review day: a meeting appears where work is happening, the calendar provides context, and real adapter calls turn fictional Workspace replies into useful file, document, spreadsheet and mail results. The gallery demonstrates an offline integration, not a successful Google sign-in or live provider acceptance.

## Scenes
1. **Next up, at a glance** — In the dark Core interface, open the footer calendar summary for the fictional launch readiness review. It shows the immediate value of connecting a calendar.
2. **See the week** — In the light Core calendar pane, open the calendar and see the fictional review alongside the other launch-day meetings. This is a different, useful state of the calendar flow, not a second caption on the same capture.
3. **Know what was selected** — In the dark Google source review panel, inspect the fictional selected executable and its digest. The panel itself explains that byte continuity is not publisher authentication and that review does not access an account or grant a read.
4. **Find recent files as JSON** — Run the actual Google files operation with a three-day window, a name and JSON output against fictional replies.
5. **Try another file window** — Run the same operation for seven days. The fixture returns the same canned file list, so this demonstrates the invocation, not verified server-side filtering.
6. **Read the launch plan** — Show the fictional Doc rendered through the adapter by a documentation-only showcase operation.
7. **Review launch metrics** — Show the fictional Sheet converted to a readable table through the same fixture-only showcase operation.
8. **Read the launch message** — Show a fictional Gmail message body through the fixture-only showcase operation.

## Fictional fixtures
`docs/screenshot_fixture.py` is the existing isolated bootstrap. Its `DemoGws` supplies fictional Drive, Docs, Sheets, Calendar and Gmail responses and refuses login; it binds the real Google adapters and adds a documentation-only `showcase` module. The calendar fixture creates a stable near-current anchor, so no fixed browser time is asserted. Names, email addresses, meetings, file contents and metrics are examples. The fixture's inert executable is an identity sample, not a runnable Google CLI. The showcase commands are documentation helpers, not commands shipped by the plugin.

## Source-bound UI surface inventory
- **Declared entrypoints:** `pyproject.toml` registers `heinzel_google` under both `heinzel.modules` and `heinzel.connected_sources`. Both resolve to `src/heinzel_google/__init__.py`; its conditional connected-service registrations depend on host APIs and captured-source activation. `src/heinzel_google/_connected_calendar.py` describes its service as unregistered in isolation, while `__init__.py` conditionally registers it: host conditions matter.
- **Plugin-owned feature view:** `src/heinzel_google/__init__.py` declares the `source-review` action, navigation to `/?panel=google:source-review`, and ABI-1 view. `src/heinzel_google/views/index.js` renders the selected command, binary, digest and continuity caveat. This is a real view, not a generic plugin card.
- **Core feature UI:** `__init__.py` provides the calendar capability and `docs/screenshot_fixture.py` binds it to fictional event replies. The existing plan identifies the footer summary and calendar pane as Core-rendered surfaces; the supplied source does not itself declare those Core controls or prove their current rendering. Capture must verify both states in the actual host. The plugin declares no footer contribution itself.
- **Operations and generic surfaces:** `__init__.py` declares `info`, private `files`, and private `source_review` operations; `source_review` explicitly has CLI and web heads. The other operation declarations do not establish that their output is terminal-only, and the supplied sources do not resolve every generic Core operation presentation. The CLI scenes are useful command results, not substitutes claimed to be feature UI. The fixture declares the separate `notes`, `week`, `inbox` and `message_content` showcase operations.
- **Setup, information and health:** `__init__.py` declares setup, system-info, local health and live health contributions; `_sign_in.py` registers sign-in grants. Core may render these generically, but the supplied plugin source does not establish their exact UI routes or controls. Local health avoids a Google request; live health explicitly contacts Google. No live test or approval screen is represented by this plan.
- **Approvals and channels:** `README.md` and `_document_write.py` describe host-reviewed, confirmed writes; `__init__.py` conditionally registers captured-write and draft-append services. These declarations do not establish a capture-ready approval screen in the supplied material. No plugin channel declaration was found. Do not infer absence of generic Core UI from the absence of a plugin page or channel.
- **External provider UI:** Google sign-in and consent belong to Google, outside the fictional offline gallery. The source review is Heinzel UI, not a Google consent screen. `README.md` also says sign-in needs real consent and that the captured-write and rolling-document workflows remain unaccepted.

## Privacy pitfalls
Treat every image and transcript as potentially sensitive, including footer text, paths, hostnames, URLs, identities, digests, environment details and terminal history. Normal presentation fictionalization is explicitly limited to these mappings: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and an independent reviewer must inspect every image and transcript. Never replace an unverified identity, alter a health result, or present a fixture credential as real.

## Acceptance criteria
- Capture the existing eight distinct scenes with the existing bootstrap; verify that the two calendar states and the source review are genuine rendered UI, and that the terminal results complete successfully.
- Confirm both light and dark appearances are actually applied. Reject duplicate captures, caption-only changes, terminal output represented as feature UI, and forged HTML.
- Confirm captions identify demo data, fixture-only commands remain clearly labeled, and file-query captions make no unsupported filtering claim.
- Independently inspect every image and transcript for unknown identities and sensitive details; apply only the disclosed verified mappings and fail closed on unknowns.
- Do not claim real account connection, provider write, consent, privacy acceptance, or end-to-end workflow acceptance from these offline captures.
- The returned plan preserves `docs/screenshots.toml`; its structure has been checked against the supplied format requirements by inspection. Capture, runtime behavior and automatic TOML parsing were not executed because this request prohibits code execution.
