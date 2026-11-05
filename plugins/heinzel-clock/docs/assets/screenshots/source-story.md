## Audience and outcome

For a distributed team choosing when to meet, World Clock makes local time and working-hour overlap visible in the app and available to scripts. This plan preserves the existing gallery’s useful views and adds explicit light and dark appearances. It does not claim the plugin has been installed or the screenshots captured.

## Scenes

1. **World clock, light:** Open the actual World Clock panel alongside Today. The globe, city list and 2/3 working metric introduce the fictional team’s current overlap.
2. **Team overview, dark:** Show the Today metric, sidebar ticker and primary footer clock together, illustrating how the clock remains useful while working elsewhere in the app.
3. **Footer detail:** Open the primary clock’s detail to inspect all configured cities and their workday countdowns.
4. **Phone:** Show the same real panel at a narrow viewport, with the globe and city list visible. This is a responsive use case, not a separate feature.
5. **CLI:** Show `hz clock --at` at the fixture’s fixed time, including zones, working hours and working status.
6. **App terminal, current time:** Run the same operation for 15:30 UTC in the native terminal: Berlin and New York are working, and Los Angeles begins in 30 minutes.
7. **App terminal, later time:** Run it for 16:30 UTC to show the three-zone overlap. The app clock remains at the fixture time; `--at` affects the command result.

The two terminal examples are parameter cases of the one declared operation. They supplement, rather than replace, the genuine feature UI scenes. Reject duplicate captures and caption-only differences; if the phone or overview does not communicate its stated use, revise or omit it during review.

## Fictional fixtures and presentation

`docs/screenshot_fixture.py` is the existing capture bootstrap. It fixes plugin time at 2026-10-26 15:30 UTC, configures fictional Berlin, New York and Los Angeles zones with 09:00–18:00 hours, and enables the sidebar and footer contributions. `browser_time` aligns browser-rendered clocks with that moment. The second terminal command deliberately previews a different moment.

Normal presentation fictionalization is explicitly limited: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail and independent review must inspect every image and transcript. Apply either mapping only after its source and full value have been verified.

## Source-bound UI surface inventory

- **Plugin entrypoint:** `pyproject.toml`, `[project.entry-points."heinzel.modules"]`, declares `clock = "heinzel_clock"`; its actual declaration is `module = Module("clock", ...)` in `src/heinzel_clock/__init__.py`.
- **Genuine plugin feature UI:** `module.nav(... sidebar=Navigate(path="/?panel=clock:world-clock"))` and `module.view(... name="world-clock", source="clock", ...)` declare the panel and its actual route. `web/src/index.ts` returns `WorldClock`; `web/src/ClockPanel.tsx` implements the globe or static fallback, zone list, local clocks, work status, primary marker and settings shortcut. `src/heinzel_clock/views/index.js` is the declared built view directory’s entry artifact; its presence does not by itself verify a capture.
- **Core-rendered feature contributions:** `primary_zone` declares a footer status with detailed clocks and navigation; `zones_ticker` declares the sidebar ticker; `module.action("team-clock", ...)` declares a header action and working count; and `at_work` declares the Today metric. All are sourced from the `clock` operation in `src/heinzel_clock/__init__.py`. The plan uses the observed declarations rather than treating the panel as the only UI.
- **Operation and terminal:** `@module.operation(render=_render, audience="everyday")` declares one operation, with optional ISO 8601 `at`, a Rich table renderer and structured zone results. README documents CLI, MCP and REST exposure. The two app-terminal scenes are terminal output inside Core, not plugin feature UI; the standalone CLI scene is also terminal output.
- **Setup, settings and health:** `ClockSettings`, `@module.setup` and `@module.health` in `src/heinzel_clock/__init__.py` declare configuration, an interactive setup flow and Doctor checks. Core may render generic setup, settings and health surfaces from these declarations; their exact presentation is not established by this source alone. Legacy `working_hours` is read but reported degraded, and unknown zone names produce a down check and an operation error. Do not present either as healthy.
- **External provider UI:** No external provider UI is declared in the provided source. `ClockPanel.tsx` says its globe does not contact a map service. MCP and REST are interfaces, not evidence of an external provider screen.
- **Other declared surfaces and uncertainty:** The module docstring describes a status item, header action and Today widget, while the actual declarations also include a sidebar ticker and World Clock view. The catalog in `pyproject.toml` describes a “World Clock page,” but the declaration specifies a panel route; use that route and do not invent a separate page. No channel, approval, or info contribution is declared in the provided module. The supplied source does not establish other Core routes or their rendered contents.

## Privacy pitfalls and acceptance criteria

Capture only with the isolated fictional profile and existing bootstrap. Inspect every image and transcript independently for names, account identifiers, hostnames, paths, tokens and unrelated app data; unknown identities fail review. Do not mask a health status or alter details beyond the narrowly verified mappings above.

Accept only real application or terminal captures with no forged HTML. Verify the applied light and dark appearances, readable UI at desktop and phone sizes, the actual panel and footer detail, and the distinct 15:30 and 16:30 command results. Ensure the globe has rendered before accepting globe scenes, and confirm that the fixed browser and plugin times agree. If a scene cannot be reproduced from these declarations and fixture, report it rather than inventing a screen. The TOML below has been checked by inspection against the requested structure; capture, rendering, privacy review and runtime validation remain outstanding because code execution is prohibited.
