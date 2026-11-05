## Audience

People deciding whether Google Workspace can supply documents, calendar events and mail to their Heinzelmännchen workflows, and who want to see both the app experience and the shape of useful command output.

## Outcome

Follow a fictional launch from a calendar week in the app to its plan, metrics and messages in the terminal. The gallery shows real Core and plugin surfaces backed by an isolated demonstration provider. It does not demonstrate a Google account connection, a live Google write, a standing grant or acceptance of a complete Turing workflow.

## Scenes

1. **Calendar week, light desktop.** Open the Core footer’s meeting control and see the fictional launch events in the actual week view. The Google calendar adapter supplies the events; the fixture supplies their contents.
2. **Google source review, dark phone.** From the workspace, activate **Google source review** and inspect the selected command, native executable and complete SHA-256 digest. The digest demonstrates byte continuity, not publisher authentication, account access or a read grant.
3. **Launch files as JSON.** Query three days with the name `Launch` and inspect structured fictional Drive results.
4. **Launch files for a week.** Query seven days without a name filter. The fixture returns the same fictional files, so this illustrates the parameter case, not verified server-side filtering.
5. **Launch plan.** Read the fictional Doc as formatted, workflow-ready text.
6. **Launch metrics.** Read the fictional Sheet as a table.
7. **Launch week.** Read the fixed October 2026 fictional calendar events and attendees in the terminal.
8. **Launch message.** Read the fictional Gmail message and its next actions.

## Fictional fixtures and boundaries

`docs/screenshot_fixture.py` is the existing bootstrap. Its `DemoGws` supplies fictional vendor responses to the real adapters; `showcase.notes`, `showcase.week` and `showcase.message_content` are documentation-only requesters, not shipped plugin commands. The calendar has fixed October examples and a separate stable current-window fictional dataset shared across queries. The source-review identity is a deterministic inert Mach-O-header fixture whose displayed digest is calculated from its actual bytes. `DemoGws.login` and unknown vendor commands refuse execution. No real `gws`, authentication, credential export or Google account is used.

Normal presentation fictionalization maps verified owning-interpreter paths to `/demo-profile/.venv`, and maps only the verified whole hostname detail in the genuine Doctor row to `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities must fail. Preserve every actual health warning; an offline Doctor exit code alone does not mean every check is healthy.

## Source-bound UI surface inventory

- **Plugin entrypoints and capabilities:** `pyproject.toml` declares both `heinzel.modules: google = heinzel_google` and `heinzel.connected_sources: google = heinzel_google`. Their target, `src/heinzel_google/__init__.py`, registers settings, services and the documents, calendar and mail providers. Captured read and write services are conditional on host SDK support and source-only loading; registration is not a grant. See `src/heinzel_google/_connected_calendar.py`, `src/heinzel_google/_document_write.py` and `src/heinzel_google/_draft_append.py` for their boundaries.
- **Genuine plugin feature UI:** `src/heinzel_google/__init__.py` declares the `source_review` web operation, the `Google source review` action navigating to `/?panel=google:source-review`, and the `source-review` view. `src/heinzel_google/views/index.js` renders the selected paths, digest and continuity disclaimer. The capture uses the actual action from `/`: on the phone viewport a direct deep link can leave the region below the visible workspace, so DOM presence alone is insufficient evidence of a useful image. This plan does not claim that deep-link behavior is fixed.
- **Genuine Core feature UI:** the published SDK’s [`org` declarations](https://github.com/helmut-hoffer-von-ankershoffen/heinzel/blob/v0.9.16/src/heinzel/modules/org/__init__.py) expose the `agenda` and `calendar` web operations and the `meeting` status contribution; [`_agenda.py`](https://github.com/helmut-hoffer-von-ankershoffen/heinzel/blob/v0.9.16/src/heinzel/modules/org/_agenda.py) reads the bound calendar for the footer and week. This is Core UI consuming Google’s adapter, not Google’s external website.
- **Other Core-rendered surfaces:** `src/heinzel_google/__init__.py` declares `info`, `files`, setup, system info and health contributions; Core may render operations, setup and health information. Setup uses prompts and offers opt-in permissions (`src/heinzel_google/_setup.py`); conditional connected-read and write services involve separate host review and approval boundaries. Their existence does not establish a particular uninspected approval screen. No plugin channel or additional plugin navigation declaration appears in the inspected module. External Google consent/provider UI belongs to Google and is not part of this offline gallery.
- **Terminal examples:** the two `google files` cases invoke the actual plugin operation; the four `showcase` examples invoke fixture-only operations through real capability adapters. These are CLI results, not feature UI. The existing `pyproject.toml` catalog labels several app-terminal captures as `ui`; that metadata conflicts with treating terminal output as genuine feature UI and should be reconciled when publishing. The declared Google view and Core calendar provide the two actual UI scenes.

## Privacy pitfalls and acceptance criteria

- Capture the real calendar week and the real source-review panel as two visibly useful, distinct feature scenes; keep the 1280×900 light and 390×844 dark views and their 30-second limits. The phone image must show the panel and its full 64-character digest in frame. Apply the appearances, rather than merely naming them.
- Capture all six distinct CLI results with the indicated arguments and visibly fictional data. Do not substitute terminal output for feature UI, forge HTML, or publish duplicate images or caption-only variations.
- Preserve the actual warnings and all details apart from the two narrowly specified presentation mappings. Unknown paths, hostnames, account identities, tokens, private content or other unrecognized identifiers fail review instead of being silently generalized.
- An independent reviewer must inspect every new image and transcript for privacy, legibility, factual captions and truthful health status before publication. Source selection and its digest are continuity evidence; they are separate from screenshot privacy approval and from any actual read grant. All screenshots still require new independent review.
- Confirm the eight captures match this plan and the native workflow. The existing plan is preserved because it already contains the useful scenes and corrected button activation. Structural review here is not an executed TOML parser or capture validation.
