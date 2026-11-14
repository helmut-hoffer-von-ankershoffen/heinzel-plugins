## Audience

Someone considering Google Workspace integration who wants to see how calendar information appears in Heinzelmännchen and what document and mail reads look like before connecting an account.

## Outcome

Follow a fictional launch from an upcoming meeting to the calendar week, then inspect the selected Google CLI source and explore fictional Workspace results. The gallery demonstrates adapter behavior with offline replies; it does not establish a successful Google sign-in, live provider access, write approval, or a complete workflow.

## Scenes

1. **Upcoming review, dark:** The Core footer and its calendar summary make the fictional launch review immediately useful at a glance.
2. **Calendar week, light:** Open the real Core calendar pane to see the fictional review alongside the week's other meetings. This is a distinct, useful state of the calendar flow, not a caption variation.
3. **Source review, dark:** Inspect the plugin's real source-review panel and its fictional selected executable. The digest demonstrates byte continuity, not publisher authentication or permission to read an account.
4. **Launch files, JSON:** Show the actual Google files operation with a three-day window and name argument using fictional replies.
5. **Launch files, seven days:** Show a second parameter case. The fixture returns the same file list regardless of the query, so do not claim that the screenshot proves server-side filtering.
6. **Launch plan:** Show a fictional Doc converted by the adapter through the fixture-only showcase requester.
7. **Launch metrics:** Show a fictional Sheet converted into a readable table through that requester.
8. **Mail content:** Show a fictional message body through the fixture-only requester and real Gmail adapter conversion.

The existing plan already captures these useful behaviors, so it is retained. The two calendar scenes are genuine Core feature UI; the terminal scenes are identified as terminal results, never presented as feature UI. Light and dark appearances are requested on actual UI scenes.

## Fictional fixtures

`docs/screenshot_fixture.py` supplies `DemoGws`, an inert fictional executable identity, fabricated launch files, calendar events and messages, and a documentation-only `showcase` module. Its `login` refuses sign-in and its `run` supplies fictional vendor replies. The fixture dynamically anchors current calendar events; it does not establish live Google behavior. Showcase commands are fixture-only, not installed Google plugin commands.

Normal presentation fictionalization is explicitly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail and independent review must inspect every image and transcript.

## Source-bound UI surface inventory

- `pyproject.toml` declares both `heinzel.modules` and `heinzel.connected_sources` entry points as `heinzel_google`. `src/heinzel_google/__init__.py` contains the module's actual registrations: documents read, calendar read/write and mail read/write; `info`, private web/CLI `source_review`, and private `files` operations; setup, system info, local health and live connector health. `src/heinzel_google/_module.py` declares the Google module.
- `src/heinzel_google/__init__.py` declares the “Google source review” action with `Navigate(path="/?panel=google:source-review")` and the `source-review` view. `src/heinzel_google/views/index.js` implements the actual panel, including command, executable, digest, launcher type and its account-access disclaimer. This is plugin feature UI, although the present story uses it as supporting context rather than a substitute for calendar use.
- The calendar footer and week pane are Core-rendered feature UI fed by the calendar capability; their existing capture steps are documented in `docs/screenshots.toml`, and the fictional events and capability binding are in `docs/screenshot_fixture.py`. The Core implementation is not among the provided sources, so the precise Core declarations and capture success remain to be verified during capture. The existence of the plugin view is not the basis for inferring those surfaces.
- Generic Core surfaces may also render the registered operations, setup, info, health and host-owned approval flows. `src/heinzel_google/_setup.py` contains setup prompts; `src/heinzel_google/_service.py` supplies local and live checks. Their exact Core routes and presentation are not established by these sources, so no additional screen is invented. The live connector check contacts Google and is excluded from the offline story.
- Conditional captured-source service registration is in `src/heinzel_google/__init__.py`; `src/heinzel_google/_connected_calendar.py` dispatches calendar, document and mail read leases, while `src/heinzel_google/_document_write.py` and `src/heinzel_google/_draft_append.py` declare supported captured write operations. Host review and approval are separate from provider capture. These declarations do not establish a capturable approval screen or a completed write in this fixture. README describes offline-model limits and unaccepted live workflows.
- Google sign-in and provider interfaces are external Google/gws UI, not plugin or Core screenshots. The `google files` and fixture-only `showcase` results are captured as CLI output; this classification does not claim that all capability behavior is terminal-only. No channel or plugin footer contribution is declared in the inspected module; the calendar footer is a generic Core capability surface.

## Privacy pitfalls and acceptance

Capture only with the existing isolated fixture and fictional data. Check every image and transcript independently for real account names, email addresses, paths, hostnames, tokens, credentials and other identifying content; unknown identities fail review. The narrow path and Doctor hostname mappings above are presentation changes, not a privacy pass. Preserve health status and all other Doctor detail. Verify that the source-review executable and digest belong to the inert fixture, and do not describe the digest as authentication.

Accept only if all eight captures come from the real app or native terminal, both calendar states contain useful distinct content, the requested light and dark appearances are actually applied, CLI results accurately reflect the fixture, and captions identify demo data and fixture-only commands. Reject duplicate images, caption-only differences, forged HTML, terminal output labeled as feature UI, unverified filtering or live-account claims, and captures with unresolved privacy findings. Inspect every image and transcript independently before publication. The TOML below is structurally checked against the requested fields by inspection; capture and runtime validation have not been performed.
