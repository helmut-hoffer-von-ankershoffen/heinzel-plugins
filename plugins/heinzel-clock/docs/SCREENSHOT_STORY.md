## Audience and outcome

For a distributed team deciding whether World Clock makes coordination easier: see who is within working hours, inspect local time and the next transition, and preview a different moment from the command line. The plugin is included in the standard app according to `README.md`; the captures should show actual rendered behavior, not imply a separate provider account or a people-tracking service.

## Scenes

1. **World clock, light:** The real World clock panel shows the globe and three local clocks at the fictional fixed time. Its markers represent time-zone names, not people (`web/src/ClockPanel.tsx`, `web/src/messages.ts`).
2. **Team overview, dark:** The Today metric, sidebar ticker and primary footer clock put the same fictional team’s availability in context. The declared widget, ticker and footer are separate Core-rendered contributions (`src/heinzel_clock/__init__.py`: `at_work`, `zones_ticker`, `primary_zone`).
3. **Footer detail:** Open the primary clock to inspect all three zones and their countdowns. This is a meaningful expanded state of the actual footer contribution.
4. **Phone world clock:** Show the real panel at a narrow viewport, including the globe and clocks. Keep this only if the resulting composition is useful and distinct from the desktop capture.
5. **CLI times:** Show the rendered `hz clock --at` table as a standalone CLI result, including the primary zone, hours and working status (`_render` and `clock` in `src/heinzel_clock/__init__.py`).
6. **Native terminal, current:** Run the same operation at 15:30 UTC inside the app terminal: Berlin and New York are working; Los Angeles starts in 30 minutes.
7. **Native terminal, overlap:** Run it at 16:30 UTC: all three fictional zones are working. These two terminal scenes demonstrate different parameters of the single operation; they are terminal results, not feature UI scenes.

## Fictional fixtures

`docs/screenshot_fixture.py` is the existing capture bootstrap. It fixes the plugin clock at 2026-10-26 15:30 UTC, configures Berlin, New York and Los Angeles with 09:00–18:00 working hours, and enables the sidebar and footer contributions. `browser_time` aligns the browser clock. The `--at` arguments independently select moments for the two command results. The fixture is run only during explicit capture, not as part of preparing this response.

## Privacy pitfalls

Use an isolated fictional profile without connected accounts, as described in `docs/SCREENSHOTS.md`. Normal presentation fictionalization is limited to replacing verified owning-interpreter paths with `/demo-profile/.venv`, and replacing only the verified whole hostname detail in the genuine Doctor row with `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript for identities, paths, tokens and other private data before publication.

## Acceptance criteria

- Capture genuine product surfaces with the existing bootstrap; no forged HTML or invented screens. The light panel and dark overview must actually apply their stated appearances.
- Confirm the globe or its legitimate fallback, three configured zones, primary designation, working states and countdowns are legible and consistent with the selected time. At 15:30 UTC the Today metric should show 2/3; at 16:30 UTC the CLI should show all three working. Do not represent a static fallback as an interactive globe.
- Confirm the footer detail is opened and meaningful; verify the host-dependent primary badge/icon presentation rather than assuming it. Keep the phone scene only if readable and compositionally distinct. Reject duplicate captures and caption-only changes.
- Capture both terminal parameter cases after their commands finish, plus the standalone CLI result. Do not present terminal output as feature UI or add brittle waits for individual table cells.
- Independently inspect every image and transcript, apply only the explicitly permitted verified mappings, and reject unknown identities. Review the contact sheet and actual results before publishing; the plan alone does not prove capture, privacy, or runtime success.

## Source-bound UI surface inventory

- **Entrypoint and feature view:** `pyproject.toml` declares `[project.entry-points."heinzel.modules"] clock = "heinzel_clock"`. `src/heinzel_clock/__init__.py` declares `module.nav` with `/?panel=clock:world-clock` and `module.view(name="world-clock", source="clock", abi=1, refresh=60)` pointing to `views`; `web/src/index.ts` exports the ABI-checked `WorldClock` component. `web/src/ClockPanel.tsx` supplies the labelled panel, local-time list, globe controls and static fallback. The packaged `src/heinzel_clock/views/index.js` is the declared built view.
- **Core-rendered feature UI:** The same module declares `primary_zone` in the footer, `zones_ticker` in the sidebar, the `team-clock` header action with a working-count badge, and `at_work` as a Today metric. Their navigation effects lead to the declared panel. `ClockSettings` and `module.nav` also contribute a preferences section; `setup` contributes an optional setup flow and `zones` contributes Doctor checks. Exact host presentation and availability require capture verification; the detail badge has an explicit older-host fallback in `_detail`.
- **Operation and interfaces:** `@module.operation(render=_render, audience="everyday") clock` supplies time-zone results. `README.md` identifies the CLI, MCP tool and REST endpoint. The supplied plugin declares no separate operation page, channel, approval, info or external-provider UI; Core may render generic surfaces for supported contributions, but their exact presentation is not established by these files. The app terminal is a Core surface displaying a command result, not a clock feature view.
- **Evidence limits and contradiction:** The module docstring describes three web-app views and a header action, while the actual declarations also include a plugin view, footer and sidebar status items and a widget. Follow those declarations over the summary. The supplied files do not establish a separate external provider UI or prove that an undeclared generic Core surface is absent. The existing plan already covers useful genuine feature states and both terminal parameters, so it is preserved. TOML structure was inspected against the requested schema; execution-based validation and capture were not performed because the request prohibits code execution.
