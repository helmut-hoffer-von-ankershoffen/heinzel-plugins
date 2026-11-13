## Audience and outcome

A distributed team choosing a meeting time can see who is within working hours, inspect each zone’s countdown, and preview a different moment from the command line. The clock’s markers represent time-zone names, not people; daylight is approximate (`web/src/messages.ts`, `web/src/ClockPanel.tsx`).

## Scenes

1. **World clock, light:** The genuine World clock panel shows the globe and fictional Berlin, New York, and Los Angeles clocks at the fixed demonstration time. Berlin is primary; two of three zones are at work.
2. **Team overview, dark:** Core’s Today contribution and primary footer clock put the fictional team’s availability in the surrounding app. The sidebar ticker provides another route to the clock.
3. **Footer detail:** Open the actual primary-clock detail to inspect all three fictional zones and their working-day countdowns.
4. **Phone world clock:** Show the same genuine panel at a phone viewport, with its globe and fictional zone list. This demonstrates responsive use, not a new feature.
5. **CLI current:** At 15:30 UTC, the fictional Berlin and New York zones are within working hours; Los Angeles starts in 30 minutes.
6. **CLI overlap:** At 16:30 UTC, all three fictional zones are within working hours. This is a different `--at` case of the same operation.
7. **CLI JSON:** Show the operation’s structured result for the fictional team at the fixed demonstration time.

## Fictional fixtures and presentation

The existing `docs/screenshot_fixture.py` fixes the plugin clock at 2026-10-26 15:30 UTC, supplies the three example zones with 09–18 hours, and enables the sidebar and footer contributions. The plan also fixes browser time. Captures must use an isolated temporary profile without connected accounts (`docs/SCREENSHOTS.md`).

Normal presentation fictionalization is explicitly limited to these mappings: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail and independent review must inspect every image and transcript.

## Privacy pitfalls

A temporary profile alone does not prove a capture safe. Check the whole image and transcript for account names, paths, hostnames, tokens, unrelated Core content, notifications, and other identifying data. Do not mask an unknown identity by guessing that it matches an approved mapping. Do not alter health statuses or other Doctor details. If a surface exposes information that cannot be verified and safely presented under the stated mappings, reject the capture.

## Source-bound UI surface inventory

- `pyproject.toml` declares the sole `heinzel.modules` entry point, `clock = "heinzel_clock"`. Its catalog describes the World Clock page, Today contribution, sidebar, footer, header and ticker; these claims are supported by declarations below.
- `src/heinzel_clock/__init__.py` declares `module.nav` with sidebar path `/?panel=clock:world-clock`, and `module.view` named `world-clock` with source `clock`, ABI 1, a 60-second refresh and a text-view fallback. `web/src/index.ts` exports the ABI-1 `WorldClock`; `web/src/ClockPanel.tsx` implements the real globe or static fallback, zone list, work states, navigation controls and settings shortcut. A panel is therefore genuine feature UI, not an inferred route.
- The same Python module declares `@module.status` contributions `primary-zone` in the footer and `zones-ticker` in the sidebar; `module.action("team-clock", ...)` supplies a header action and working-count badge; `@module.widget` supplies the Today metric. These are Core-rendered feature surfaces sourced from the clock operation, not separate plugin pages. Footer badge and icon detail varies with host support; the source explicitly retains a textual primary fallback on older hosts.
- `@module.operation` declares one everyday `clock` operation with an optional ISO-8601 `at` parameter, a Rich table renderer and structured zone results. The README identifies its CLI, MCP and REST exposures. The CLI captures are native terminal results, not feature UI; MCP and REST are interfaces, not evidence of additional screens.
- `@module.settings`, `@module.health`, and `@module.setup` contribute settings, Doctor checks and an optional setup flow rendered by Core. Unknown zones produce a down health check; legacy `working_hours` produces a degraded check. Setup is interactive. No plugin-specific channel, approval, external-provider UI, or separate info contribution is declared in the inspected module. Core may have generic surfaces, but their existence or exact presentation beyond these declarations is not established by this source.
- `README.md` calls the plugin included in the standard app, while the view fallback says to run `hz clock` if the panel is unavailable; neither guarantees the panel or WebGL works in a particular host. `web/src/ClockPanel.tsx` explicitly uses a static map when motion is reduced or WebGL fails. The plan requests WebGL for globe scenes, so capture must verify the actual rendered result rather than infer success from the plan.

## Acceptance criteria

- Capture the existing seven distinct scenes using the declared fixture and real app/CLI surfaces. Preserve the two useful `--at` cases and the JSON result; do not substitute a terminal capture for feature UI, forge HTML, or accept duplicate images or caption-only differences.
- Verify that light and dark appearances are actually applied, the phone viewport is legible, the footer detail is open, and globe scenes render as intended. If WebGL or a host contribution is unavailable, report the observed limitation rather than representing it as present.
- Confirm the displayed times and working states match the fixed instant and configured hours, including the primary designation. Verify the CLI overlap case separately.
- Independently inspect every image and transcript for accuracy and privacy under the limited mappings above. Unknown identities fail review.
- The existing plan is retained because it already demonstrates the useful behavior. Its TOML structure was inspected against the supplied format requirements; no parser or capture was run because code execution was prohibited.
