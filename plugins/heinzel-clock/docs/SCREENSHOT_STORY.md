## Audience

A distributed team deciding whether World Clock will make it easier to find a considerate time to collaborate, and an agent or terminal user who needs the same information as structured data.

## Outcome

Show the team at a fixed fictional moment, then preview a later moment when all three working days overlap. The globe, Today metric, sidebar and footer make the answer available in the app; the CLI provides a repeatable preview and JSON output.

## Scenes

1. **World clock, light:** Open the genuine World clock panel to see the globe, primary zone, local times and working-hour context for Berlin, New York and Los Angeles. The moment is fictional and fixed.
2. **Team overview, dark:** Show the Today metric and primary footer clock in their normal app context, with the sidebar ticker available. At the fixture moment, two of three zones are at work.
3. **Footer detail:** Open the primary clock’s genuine detail pane to compare the configured zones and their countdowns. This is a distinct feature state, not a caption variation.
4. **World clock on a phone:** Show the same genuine panel at a narrow viewport so a prospective user can assess its mobile layout. Review it for legibility and meaningful differences from the desktop capture.
5. **CLI at 15:30 UTC:** Show the real `hz clock --at` table for the fictional team: Berlin and New York are working; Los Angeles starts in 30 minutes.
6. **CLI at 16:30 UTC:** Show the second parameter case, when all three fictional zones are within working hours.
7. **CLI JSON:** Show the structured result at the original fixed moment for someone evaluating agent or script integration.

## Fictional fixtures

`docs/screenshot_fixture.py` is the existing bootstrap. It fixes the plugin clock at 2026-10-26 15:30 UTC, supplies three fictional zones with 09:00–18:00 hours, and enables the sidebar ticker and footer contribution. The plan also fixes browser time; the later CLI scene explicitly supplies its own `--at` value. The fixture uses environment configuration and invokes the existing application during explicit capture; it was inspected, not run here.

## Privacy and presentation

For normal presentation fictionalization, verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail; independent review must inspect every image and transcript. Review all other paths, usernames, hostnames, account information and incidental app content before publication; do not infer safety from the fictional clock data or a dismissed Doctor banner.

## Acceptance criteria

- Capture real application surfaces and real CLI output using the existing bootstrap; do not forge HTML, substitute terminal output for feature UI, or invent screens or fixture files.
- Show at least two useful feature UI states and a useful CLI result. Retain both distinct `--at` cases and the JSON result. Reject duplicate captures or changes consisting only of captions.
- Confirm the light and dark appearances are actually applied, the globe has rendered, and the phone view is readable. If WebGL or a host contribution is unavailable, report the observed result rather than claiming the intended scene was captured.
- Verify the displayed times, 2/3 count, countdown and later overlap against the fixed fixture and the captured output. Inspect all images and transcripts independently for privacy, including any unrecognized identity.
- Capture and validate only during an explicitly authorized capture workflow. This plan was reviewed structurally against the requested format; it was not executed or parser-validated in this read-only task.

## Source-bound UI surface inventory

- `pyproject.toml`, `[project.entry-points."heinzel.modules"]`: the sole declared plugin entry point is `clock = "heinzel_clock"`. `src/heinzel_clock/__init__.py` declares the actual module and its contributions.
- Genuine plugin feature UI: `module.nav` points to `/?panel=clock:world-clock`; `module.view` declares `world-clock`, source `clock`, ABI 1 and a 60-second refresh. `web/src/index.ts` supplies `WorldClock`, and `web/src/ClockPanel.tsx` implements the globe, local-time list, working states and settings shortcut. Its static map is a real fallback for reduced motion or failed WebGL; the globe does not contact a map service. `src/heinzel_clock/views/index.js` is the packaged view. The view declaration also supplies a text fallback directing users to `hz clock`; that fallback does not make the feature terminal-only.
- Core-rendered feature contributions: `primary_zone` declares the footer status and zone details; `zones_ticker` declares the sidebar ticker; `module.action("team-clock", ...)` declares a header action with a working-count badge; and `at_work` declares the Today metric. Their effects navigate to the declared panel. The exact host rendering and availability remain capture-time evidence, including the older-host detail badge fallback described in `README.md` and `_detail`.
- Operation and other Core surfaces: `@module.operation` declares one `clock` operation with an optional ISO 8601 `at` parameter and a Rich table renderer; `README.md` identifies CLI, MCP and REST access. `@module.settings`, `@module.health`, and `@module.setup` declare configuration, Doctor checks and an optional setup flow that Core may render. The provided sources do not declare plugin channels, approvals or a separate info contribution; absence of those declarations does not establish what generic Core UI is available. No separate external-provider UI is declared.
- Evidence limits: the module docstring describes three operation views, while the actual declarations additionally include a sidebar ticker and a custom panel; use the declarations as the more specific inventory. `docs/screenshots.toml` documents intended selectors and Core behavior, but the provided Core implementation and capture results are absent, so route rendering, SDK health, accessibility names and final image content remain unverified.
