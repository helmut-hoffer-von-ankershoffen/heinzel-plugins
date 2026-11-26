# Google connector gallery source story

## Audience and scope

Show prospective Heinzel users the real, offline behavior of the Google connector: fictional Calendar data in Core, the selected `gws` source review, and representative document, spreadsheet, mail, and file adapter output. This gallery is fixture-backed. It does not prove Google sign-in, that the user granted any OAuth scopes, live provider access, writes, or a complete connector workflow.

The staged product change makes the default setup request broad read/write access, including all Drive files and Gmail `gmail.modify`; Google still presents the consent decision in the browser. Custom setup remains available. App sign-in also reports progress, verifies a Calendar grant where requested, and may open a validated Google consent URL from terminal login. Do not imply Heinzel silently authorizes this access or performs writes without confirmation. Do not capture a real Google consent page or treat the fixture as evidence of user consent.

## Current plan assessment

Keep the eight existing scenes for this capture. Their claims remain supported by the fixture and plugin declarations, and they retain the required two useful UI scenes plus a CLI scene. They illustrate connector value without implying the new broad default is safe, granted, or exercised. No added sign-in scene is source-justified from this plugin worktree alone: the Google consent UI is external, and the Core host's grant-selection/progress screen and a safe fixture route are not established here. If the product owner wants permission onboarding represented, inspect the exact Core route and fixture support in a later source pass before changing the plan.

## Scene story

1. **Upcoming meeting, dark UI.** Open Core's footer Calendar summary and show the fictional Launch readiness review. This is a Core capability surface backed by the Google calendar adapter and the fixture's current-time anchor.
2. **Calendar week, light UI.** Open Core's calendar pane and show the fictional launch meetings. This is a second useful state of the same Calendar flow; verify the expected event and applied appearance during capture.
3. **Selected source, dark UI.** Open the plugin's declared Google source review action/view. Show only the fictional selected executable and digest. A digest establishes byte continuity, not publisher identity, account access, or safety.
4. **Recent files, JSON CLI.** Run the declared `google files` operation for three days and a Launch name filter. The fixture replies are canned and do not prove Drive filtering.
5. **Wider file window, CLI.** Run the same operation for seven days. The fixture returns the same canned files; caption it as invocation behavior, not server-side filtering.
6. **Launch plan, CLI.** Use the fixture-only `showcase notes launch-plan` requester to pass a fictional Doc through the real adapter. Do not present `showcase` as an installed Google command.
7. **Launch metrics, CLI.** Use `showcase notes launch-metrics` for fictional Sheet content through the real adapter. It is fixture-only.
8. **Launch message, CLI.** Use `showcase message-content` to render fictional Gmail content through the real adapter. It is fixture-only and does not establish Gmail consent or mail access.

## Fixture and review constraints

`docs/screenshot_fixture.py` uses a temporary fictional profile, inert selected executable, canned Workspace responses, and a `DemoGws` that refuses sign-in and never starts Google. It adds documentation-only showcase operations. Its stable current-day Calendar anchor and fixed October 2026 examples serve different windows; capture must verify the intended scene content. Keep only the already verified mappings in the maintained story (owning interpreter to `/demo-profile/.venv`; the verified whole hostname detail to `demo-host`). Unknown paths, identities, hostnames, browser chrome, tokens, document contents, or transcript data are a failure; do not guess mappings.

A later independent reviewer must inspect every PNG and transcript against the exact generated bundle, confirm all captions and the two Calendar UI states, and reject any claim of live access, scope consent, write acceptance, or filtering unsupported by the fixture. This source story is not visual approval or a privacy receipt.

# Google Calendar week scene: source review

## Verdict

Affirm the corrected source-defined scene. Removing the initial `wait` for `Ask about it` is correct for Core v0.9.55. That control is not rendered by the tagged Home/TopBar calendar surface. The supported entry point on this version is the `Open calendar` button; after opening, the CalendarPanel contains an enabled `Previous week` action and renders the agenda content. The plan still needs the later capture to confirm that the fixture-backed event actually appears in the captured panel. This review is not visual approval.

## Evidence checked

- Core release tag `v0.9.55` resolves to commit `c51a98c649fae65516ac0b26bef8fc3c11476419`.
- `web/src/layout/TopBar.tsx:247-258` defines the header button with accessible name `Open calendar`; the tools menu exposes the same action at lines 326-335. The tagged source has no `Ask about it` text in `TopBar.tsx`.
- `web/src/layout/CalendarPanel.tsx:138-152` renders the Calendar panel header; lines 175-189 render the agenda when data is available; lines 205-212 define Today/Previous week/Next week, with Previous week enabled at offset zero.
- `web/src/layout/CalendarSummary.tsx:158-190` confirms the footer summary may also contain an `Open calendar` action. The corrected scene's initial wait now proceeds to the expected available control; capture still must disambiguate the intended header/footer target by the actual page state and verify it opens the panel.
- Owner fixture `plugins/heinzel-google/docs/screenshot_fixture.py:135-187` supplies fictional `Launch readiness review` events and a current-day anchor 15 minutes ahead, with later events staggered 45 minutes apart. The Calendar response filters against the requested window. This supports an intended Calendar display, but does not prove which event or layout appears in a screenshot.
- Current plan diff removes only the `wait` for `Ask about it`; the remaining steps wait/click `Open calendar`, wait for `Previous week`, and wait for `Launch readiness review`.

## Scope and limits

This is a source-only acceptance of the corrected interaction sequence against Core v0.9.55 plus the owner fixture. It does not inspect rendered pixels, confirm the planned light appearance, establish that the original run reached a particular screen beyond the parent's report, or approve the gallery bundle. If capture still fails, inspect the actual accessible names and whether duplicate `Open calendar` controls are present before changing the plan again.

## Verified synthetic executable path

The path `/demo-profile/state_dir/fictional-gws/gws` identifies the inert executable created by the owner fixture in the isolated capture state directory. The fixture sets the selected executable under `HZ_STATE_DIR/fictional-gws` and writes only fictional executable and credential bytes (`docs/screenshot_fixture.py:257–267`). The pinned capture sets that state directory under its temporary work directory and rewrites the temporary work prefix to `/demo-profile` before saving the image and transcript (`capture.py:607–608,740–750,1068,1239–1248`). Source verification does not approve the image.
