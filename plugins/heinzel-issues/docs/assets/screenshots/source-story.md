## Audience

People who want to report a problem or request an improvement and follow its progress. Sending requires a configured writable tracker.

## Outcome

Show how to find a report, read its history, and check progress in Issues, Today, or the CLI. The view also exposes status filtering and sorting, so the overview should show both controls.

## Scenes

1. **Issues page, light.** Show the status filter, sort control, three fictional reports with sent dates, and the composer. The fixture represents received, being worked on, and released in 0.9.27.
2. **Report history, light.** Open the fictional weather report. Show its description, attachment name, progress through release, and the report ID and last-updated date when visible in the expanded state.
3. **Today, dark.** Show the two open fictional reports in the Core-rendered widget. The completed weather report should be absent.
4. **CLI list.** Run the real Issues list command against this same fictional tracker and show the reports and their statuses.

## Fictional fixtures

The screenshot fixture supplies three in-memory tasks, the fictional attachment name today-rain.png, and a temporary Git history containing the fictional 0.9.27 release. It does not contact Beads. The fixture refuses submission and does not implement closing reports. These scenes establish presentation and navigation. Successful submission, creator-only closing, and account isolation require separate evidence.

## Privacy checks

Review every full image and transcript. The composer should describe the authenticated workspace identity without rendering its opaque principal ID. Inspect surrounding Core UI and console text for unexpected account names, identifying labels, hostnames, local paths, credentials, notifications, or real report content. Only the existing verified presentation mappings for temporary interpreter paths and the Doctor hostname detail are expected. Check the appearance and all visible content after the optional Doctor dismissal.

## Acceptance criteria

Use the declared route and fixture for the genuine panel, expanded report, Today widget, and CLI. Check the filter and sort controls, the three statuses and release, the opened report details, and exclusion of the completed item from Today. Verify the actual light and dark appearances. Check that each caption identifies fictional data and that the four captures document distinct states or surfaces. Capture approval requires a separate image and transcript review.

## Source-bound UI surface inventory

- The pyproject module entry point loads heinzel_issues. The module registers Issues navigation and the requests view, backed by the list operation and rendered by views/index.js. The renderer also owns the tracker setup form, composer, filter and sort controls, report history, and eligible creator-close action.
- The module registers list, show, submit, close, and connect operations for app and CLI use, with Core operation surfaces where declared. Setup and tracking add Core onboarding and Doctor checks.
- The Today contribution renders open reports. The watcher may deliver local notifications. The plan does not capture notifications or setup and makes no claim about an external tracker interface.
- The Beads connector scopes new reports by authenticated principal, with installation-owner-only legacy reads. Current Core sessions on one installation resolve to the same owner. The fixed in-memory rows do not exercise those access checks or real tracker behavior.
