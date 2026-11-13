## Audience

Someone deciding whether to connect Google Workspace to Heinzelmännchen, especially someone who wants to see useful calendar and document results before considering setup and permissions.

## Outcome

Show a fictional launch week in the real Core calendar, then show what the Google adapter returns for files, a document, a sheet and a message. The gallery demonstrates offline adapter behavior; it does not demonstrate a real Google sign-in, live Google access, approved writes or provider-side filtering.

## Scenes

1. **Upcoming review, dark:** The Core footer shows the next fictional launch review. This is a useful at-a-glance calendar state supplied through the Google adapter.
2. **Calendar week, light:** Open the same real Core calendar flow to see the fictional launch week. This is a distinct, expanded state of the calendar, not a caption-only variation of scene 1.
3. **Source review, dark:** Open the actual Google source-review panel to inspect the fictional selected executable and its digest. The panel explicitly says the digest establishes byte continuity, not publisher authenticity or permission to read an account.
4. **Three-day file query:** Run the actual `google files` operation with a name filter and JSON output against fictional replies.
5. **Seven-day file query:** Show a second parameter case for that operation. The fixture returns the same static file list, so this demonstrates invocation, not server-side filtering.
6. **Launch plan:** Read a fictional Google Doc through the adapter using the documentation-only `showcase notes` operation.
7. **Launch metrics:** Read a fictional Sheet through the same fixture-only operation, showing the resulting table.
8. **Mail content:** Read a fictional Gmail message through the adapter with the fixture-only `showcase message-content` operation.

The last six scenes are CLI results, not representations of feature UI. The two calendar states are genuine, useful Core feature UI; the source-review panel is additional plugin UI. Light and dark appearances are specified for actual UI captures.

## Fictional fixtures

`docs/screenshot_fixture.py` is the existing bootstrap. It creates isolated fictional `gws` state, binds a `DemoGws` transport that returns fabricated Workspace replies and never starts a Google process, and registers the documentation-only `showcase` module. Its current-day calendar anchor supplies upcoming fictional events; its fixed examples supply the launch plan, metrics and mail. The fixture-only commands must be identified as such, and the synthetic sign-in files must not be presented as evidence of an authenticated account.

Normal presentation fictionalization is explicitly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail and independent review must inspect every image and transcript. The source-review executable path and digest are separate identity details and must also be reviewed rather than assumed safe.

## Source-bound UI surface inventory

- `pyproject.toml` declares both `heinzel.modules` and `heinzel.connected_sources` entry points as `google = "heinzel_google"`. Both resolve to `src/heinzel_google/__init__.py`; the latter does not, by itself, declare another screen. That module conditionally registers connected-read and captured-write services when host contracts and source loading permit them. The service implementations in `src/heinzel_google/_connected_calendar.py`, `src/heinzel_google/_connected_artifact.py`, `src/heinzel_google/_connected_mail.py` and `src/heinzel_google/_document_write.py` describe review or approval boundaries, but the provided source does not establish an executable gallery flow for a Core approval screen.
- `src/heinzel_google/__init__.py` declares the `source_review` operation for CLI and web, a `Google source review` action navigating to `/?panel=google:source-review`, and the corresponding view. `src/heinzel_google/views/index.js` renders its actual configured and unconfigured states. This is plugin feature UI, not external Google UI.
- The same module declares `info`, private `files`, setup, system-info, local health and live health contributions. Generic Core operation, setup, information and Doctor surfaces may render these contributions; the provided plugin source alone does not establish their precise routes or all rendered controls. In particular, `files` has no explicit CLI-only declaration, so its CLI scenes do not imply that it cannot appear in Core UI. `src/heinzel_google/_service.py` distinguishes local checks from the explicitly invoked live Google check.
- `src/heinzel_google/__init__.py` provides the calendar capability; `docs/screenshot_fixture.py` binds it and supplies events. The existing plan exercises the Core footer and expanded calendar at `/`. These are Core feature UI, not Google Calendar's external website. The supplied files do not contain the Core calendar renderer itself, so successful rendering remains capture-time evidence to verify.
- `src/heinzel_google/_setup.py` uses prompts and may open a browser for Google consent. That external provider UI is distinct from Core setup and is not included in the offline gallery. No plugin channel, footer, approval, page or navigation declaration beyond the source-review action and view was found in the provided plugin declarations; Core may nevertheless render capability and contribution surfaces.
- `docs/screenshot_fixture.py` declares `showcase.notes`, `showcase.week`, `showcase.inbox` and `showcase.message_content` as fixture operations. The plan uses their native CLI output where selected; their declarations do not establish that they are terminal-only.
- `README.md` and `pyproject.toml` describe the source-review screenshot as a phone view, while the existing `docs/screenshots.toml` specifies a 1280 × 900 viewport. Treat the plan's desktop viewport as authoritative for this proposed capture and correct the published description if capture confirms it. The README's broad description of confirmed writes does not establish a completed live write or the source-only captured-write workflow's acceptance.

## Privacy pitfalls

Review every image and transcript for real account names, addresses, document content, local paths, hostnames, tokens and other unexpected identities. The fixture includes example names and `example.com` addresses, but temporary paths, SDK diagnostics and environment-dependent Core chrome can still reveal local information. Apply only the verified presentation mappings above; an unknown identity is a failure, not an invitation to guess or redact away an unexplained result. Do not run setup, live connector testing or Google consent during capture.

## Acceptance criteria

- Capture the eight existing, meaningfully different scenes with the existing bootstrap; verify the footer and expanded calendar actually contain the fictional events and that the source-review panel is the declared view.
- Verify applied dark and light appearances, legibility, and the absence of duplicate or caption-only captures. Never substitute forged HTML or terminal output for feature UI.
- Confirm both `google files` parameter cases finish with useful fictional output, without claiming the static fixture verifies filtering. Clearly label the three `showcase` outputs as fixture-only commands.
- Independently inspect every image and transcript for privacy and truthful labels. Preserve all SDK health statuses and remaining Doctor details when applying the explicitly permitted mappings.
- Treat failed loading, unavailable routes, unexpected identities, missing fixture data or a real-account prompt as a failed capture. Do not claim live sign-in, real writes, publication or privacy acceptance from this plan.
- The existing plan is retained because it already demonstrates useful source-supported behavior. Its TOML and fields were checked against the supplied format by inspection; no parser, capture or code was executed, so runtime validation remains outstanding.
