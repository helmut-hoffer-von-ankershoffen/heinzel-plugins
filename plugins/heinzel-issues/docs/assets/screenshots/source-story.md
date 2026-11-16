## Audience
People who want a simple way to report a problem or request an improvement and follow it through to a release, provided they have access to a writable Beads database.

## Outcome
Show how Issues turns a report into a small, understandable journey: received, being worked on, done, and released. Make the writable tracker prerequisite clear, and show that the same reports are available in the app and CLI.

## Scenes
1. **Issues page, light:** Three fictional reports span the three states; the released report and the composer make both follow-up and reporting visible.
2. **Report history, light:** Open the fictional weather report to show its description, attachment name, and progress through release. This is a meaningful expanded state of the same view, not a duplicate capture.
3. **Today, dark:** Show the two open fictional reports in the Core-rendered widget; the completed report is absent.
4. **CLI list:** Show the same fictional reports and plain-language statuses using the actual `issues list` operation.

The existing plan already tells this story, so its scenes and bootstrap are retained. The light and dark appearances must actually be applied during capture.

## Fictional fixtures
`docs/screenshot_fixture.py` supplies an in-memory tracker with three fictional tasks, a fictional attachment name and a temporary release clone containing the fictional 0.9.27 release. It does not use a Beads database. Its `Demo.submit` deliberately refuses sends, so captures must not claim that a report was submitted successfully. The fixture creates its temporary clone only during explicit capture; it was not run for this plan.

## Privacy pitfalls
Normal presentation fictionalization maps verified owning-interpreter paths to `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row to `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript.

The composer displays the local login and configured labels (`src/heinzel_issues/views/index.js`, `sentAs`; `src/heinzel_issues/_service.py`, `overview`). Treat an unexpected sender, label, path, hostname, account, notification, or other identifying detail as a capture failure; do not assume the fictional task data sanitizes surrounding Core UI. Dismiss Doctor only where the existing optional step finds it, and inspect any remaining content. Never use forged HTML or recast terminal output as feature UI.

## Acceptance criteria
- Capture the genuine Issues view and its expanded report, the genuine Today widget, and the real CLI result using the declared route and fixture. Reject duplicate captures and caption-only variations.
- Verify all three statuses and the fictional release in the Issues view; verify the opened report's body, attachment name and history; verify Today contains open reports and excludes the done report.
- Verify the CLI result reflects the fixture, with no claim that a real tracker was contacted. Each caption identifies demo or fictional data.
- Verify light and dark appearances visually, and independently inspect every image and transcript for privacy before publication. Unknown identities fail review.
- The editable TOML below has been checked against the supplied field and action rules by inspection; no parser, product code, capture, or network call was run, so runtime capture and parser validation remain outstanding.

## Source-bound UI surface inventory
- `pyproject.toml`, `[project.entry-points."heinzel.modules"]`: the declared plugin entry point is `issues = "heinzel_issues"`. `src/heinzel_issues/_contract.py`, `ENTRY_POINTS` and connector loading, also define an extension group for external tracker connectors; no external provider interface is supplied here.
- `src/heinzel_issues/__init__.py`, `module.nav`, `module.action` and `module.view`: the genuine Issues feature view is `requests`, backed by `list`; `src/heinzel_issues/_service.py`, `ROUTE`, declares `/?panel=issues:requests`. `src/heinzel_issues/views/index.js` implements the list, expanded history, composer and unconfigured setup form. `connect` and `send` invoke declared operations through Core confirmation; the provided fixture cannot demonstrate a successful send.
- `src/heinzel_issues/__init__.py`, `today`: Core renders a Today list widget for up to eight open reports, with navigation to the Issues view. The `watch` job can produce local notifications; the supplied fixture and plan do not establish a captured notification state.
- `src/heinzel_issues/__init__.py`, `list`, `submit`, `connect`, and `show`: operations expose CLI results and may also contribute Core operation and confirmation surfaces. `setup` contributes a Core setup flow and `tracking` contributes health/Doctor checks. These are not evidence that Issues is terminal-only. No channel, info, or footer contribution is declared in the supplied module.
- The Beads connector invokes a local provider (`src/heinzel_issues/_beads.py`); no external provider UI is declared. `docs/CONTRACT.md` describes possible third-party connectors, not screens available in this source.
- `README.md` says normal app sending works after setup, while the screenshot fixture expressly disables sending. It also says reports are limited to the local login; the in-memory fixture returns its fixed tasks directly and does not prove that privacy boundary. These differences must remain visible in review, rather than being treated as acceptance evidence.
