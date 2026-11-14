## Audience

A distributed team deciding whether World Clock makes it easier to find a good time to collaborate, and someone who wants the same information in scripts or an agent.

## Outcome

Show how three fictional team time zones make working-hour overlap visible at a glance, in the World Clock panel and in the surrounding app, then show two moments and structured output in the CLI. The existing seven-scene plan already demonstrates these behaviors, so it is preserved.

## Scenes

1. **World clock, light:** the globe and zone list introduce the fictional Berlin, New York and Los Angeles team at a fixed time. The Today metric shows two of three zones at work.
2. **Team overview, dark:** the Core-rendered Today contribution and primary footer clock show the information in the normal app context.
3. **Footer detail:** open the primary clock to inspect all configured zones and their workday countdowns.
4. **Phone world clock:** show the same genuine panel at a narrow viewport, with its globe and zone list. This is a responsive-use scene, not a caption-only duplicate of the desktop scene.
5. **Current CLI:** at 15:30 UTC, Berlin and New York are working and Los Angeles starts in 30 minutes.
6. **Overlap CLI:** at 16:30 UTC, all three zones are within their fictional working hours.
7. **JSON CLI:** show the operation's structured result for the fixed demonstration time.

## Fictional fixtures

`docs/screenshot_fixture.py` is the existing capture bootstrap. It fixes the plugin clock at 2026-10-26 15:30 UTC, configures Berlin, New York and Los Angeles with 09:00–18:00 working hours, and enables the sidebar ticker and footer contribution. `browser_time` aligns browser clocks with that moment; the CLI's explicit `--at` supplies each requested moment. These are example team settings, not claims about real people. The bootstrap runs only during explicit capture.

Normal presentation fictionalization is explicitly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail and independent review must inspect every image and transcript.

## Source-bound UI surface inventory

- `pyproject.toml`, `[project.entry-points."heinzel.modules"]`: the declared plugin entry point is `clock = "heinzel_clock"`. Its actual declarations are in `src/heinzel_clock/__init__.py`.
- **Plugin feature UI:** `module.view(name="world-clock", source="clock", ...)` registers the view, and `module.nav(... sidebar=Navigate(path="/?panel=clock:world-clock"))` declares its actual panel route. `web/src/index.ts` exports the ABI-1 view factory; `web/src/ClockPanel.tsx` implements the globe, daylight shading, zone list, working states, rotation controls and settings shortcut. Reduced motion or WebGL failure produces a static map. `src/heinzel_clock/views/index.js` is the declared packaged view asset directory's entry file. The plugin calls its map local and says markers represent time-zone names, not people (`web/src/ClockPanel.tsx`, `web/src/messages.ts`).
- **Core-rendered feature UI:** `@module.status` declares the primary-zone footer and zones-ticker sidebar; `module.action("team-clock", ...)` declares a header action; `@module.widget` declares the Today count. These are real feature contributions, not terminal substitutes. The footer detail's badge and icon depend on host support; older hosts retain primary as text (`src/heinzel_clock/__init__.py`, `README.md`).
- **Core-generated operational surfaces:** `@module.operation(render=_render, audience="everyday")` declares the clock operation and table renderer. `README.md` identifies CLI, MCP and REST access. `@module.settings`, `@module.health` and `@module.setup` declare configuration, Doctor checks and a setup flow that Core may render. The provided source does not establish an exact Core operations, setup or Doctor UI route or appearance, so this story makes no invented capture claim for them. Unknown zones produce a down health check and an operation error; legacy `working_hours` produces a degraded check.
- **Terminal-only evidence in this plan:** the CLI table and JSON are genuine CLI results, captured as CLI scenes. The existence of the feature panel and Core contributions rules out presenting terminal output as feature UI. No external provider UI, channel, approval or info contribution is declared in the inspected plugin module. MCP and REST are interfaces, not evidence of an external provider screen.
- **Evidence boundary:** the module docstring mentions three views while the actual declarations include a registered view plus status, action and widget contributions; the declarations above govern the inventory. The provided source does not prove how every Core version renders each contribution, whether a specific browser will have WebGL, or whether the retained plan currently captures successfully. `README.md` also describes host-dependent footer presentation. Capture and review must resolve those runtime details.

## Privacy pitfalls and acceptance criteria

- Capture only with the isolated fictional profile; review every image and transcript independently for account names, machine names, paths, notifications and other identities. Unknown identities fail review. Apply only the disclosed, verified presentation mappings; do not alter health status or other Doctor detail.
- Verify the actual light and dark appearances are applied, the genuine panel and footer detail are visible and useful, the mobile layout remains legible, and the globe is rendered when the planned WebGL wait succeeds. If a host instead displays the documented static fallback, report that observation and reassess the scene rather than fabricating a globe.
- Verify the two CLI moments and JSON against the fictional fixture, including primary designation and working states. Captures must be distinct in information or use; reject duplicates, caption-only changes, terminal output portrayed as feature UI, and forged HTML.
- The TOML below has been checked against the requested field and scene constraints by inspection. No code, bootstrap, capture or runtime validation was executed; successful capture and privacy acceptance remain open.
