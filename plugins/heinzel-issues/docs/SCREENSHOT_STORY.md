## Audience

Someone deciding whether Issues will make it easier to report a problem and follow its progress without learning a tracker’s workflow.

## Outcome

Show a small, believable journey: three fictional reports in plain language, the two still open on Today, and the same status information available from the CLI. The existing plan already tells that story with two useful feature UI scenes and a CLI result, so it is preserved.

## Scenes

1. **Issues page, light:** Three fictional reports span Received, Being worked on, and Released in 0.9.27. The genuine composer makes the next action visible. Do not imply that the fixture successfully sends a report.
2. **Today, dark:** The fictional open reports appear in the Today widget; the completed report is absent. This is a different, useful surface and state, not a duplicate caption.
3. **CLI list:** The native `hz issues list` result presents the fictional reports, plain statuses, and sent dates as a useful terminal result.

## Fictional fixtures

`docs/screenshot_fixture.py` supplies an in-memory tracker with three fictional tasks and creates a temporary fictional release clone whose fix ships in version 0.9.27 on 7 Nov 2026. It configures the tracker and release source for capture. Its `Demo.submit` refuses sending; the Beads write capability also follows a separate path, so this fixture does not establish a successful submission. `docs/SCREENSHOTS.md` describes a temporary fictional profile without connected accounts and says no Beads database is touched. The bootstrap is used only during an explicit capture.

Normal presentation fictionalization is disclosed: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail and independent review must inspect every image and transcript.

## Source-bound UI surface inventory

- **Plugin feature UI:** `pyproject.toml` declares the `heinzel.modules` entry point `issues = "heinzel_issues"`. `src/heinzel_issues/__init__.py` declares the Issues navigation and action, plus the `requests` view sourced from `list`; `src/heinzel_issues/_service.py` defines its actual route as `/?panel=issues:requests`. `src/heinzel_issues/views/index.js` renders the list, states, composer, loading/error and setup states. The view’s `send` action invokes the private write operation through Core confirmation; on older SDKs it offers a terminal-opening fallback instead. The confirmation is Core feature UI, not an external tracker screen.
- **Core-rendered feature UI:** `src/heinzel_issues/__init__.py` declares the `today` `ListWidget`, populated from `list` with non-done reports and navigation to the Issues route. Its health check contributes a tracker status to Core’s health/Doctor presentation; `setup` supplies an interactive configuration flow. `watch` can emit local notices through Core notifications (`src/heinzel_issues/_service.py`, `_notify`). Their exact Core layouts are not declared in the supplied source, and no screenshot should invent them. No channel, info, footer, or additional page contribution is declared in the supplied plugin module.
- **Operations and terminal:** `src/heinzel_issues/__init__.py` declares `list`, `submit`, and `show`, including their renderers; `README.md` documents CLI use and JSON details. The list command is a real CLI result, not a substitute for feature UI. Setup and the older-SDK report fallback can open terminal flows; this does not make the report feature terminal-only.
- **External provider:** `src/heinzel_issues/_beads.py` implements a local Beads connector and tracker capability; `docs/CONTRACT.md` defines other connector entry points. No external provider UI is declared or needed for these scenes.
- **Evidence limits:** The supplied sources do not include Core’s rendering implementation or capture runner, so actual layout, applied appearance, SDK availability, and capture success remain to be observed. `README.md` describes a confirmation before sending, while the fixture disables its connector’s submit and the Beads capability writes separately; a successful send must not be inferred from the composer. The documentation’s gallery references are intended outputs, not proof that current captures exist or pass review.

## Privacy pitfalls

Inspect every image and transcript independently for real names, usernames, paths, hostnames, account details, notifications, tracker data, attachment names, and terminal history. Only apply the narrowly verified presentation mappings above; any unknown identity fails review. The fictional tracker does not by itself sanitize Core chrome, Doctor details, or terminal output. Avoid exposing real report text: `src/heinzel_issues/_service.py` records the login name as the Beads actor on actual writes, and tracker errors may contain sensitive details.

## Acceptance criteria

- Capture the declared real Issues view in applied light appearance and the genuine Today widget in applied dark appearance, with legible fictional report titles and states. Confirm the released item is visible on Issues and absent from the open-only Today widget.
- Capture the real CLI list result with the same fictional reports and useful status/date columns. Do not present terminal output as feature UI.
- Retain the genuine view and Core rendering; reject forged HTML, duplicate images, and caption-only variations. Do not claim a successful send or a notice based on the fixture.
- Verify the actual capture environment supports the declared route, view and appearances; inspect every image and transcript independently for privacy and fidelity. Unrecognized identities fail, even after the disclosed mappings. No screenshot capture or runtime validation was performed for this proposal.
