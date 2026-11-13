## Audience
People coordinating across time zones who want to see when colleagues may be available, plus users who need the same information in scripts or agents.

## Outcome
Show how a fictional three-city team can find working-hour overlap at a glance, inspect the primary clock’s details, and query another moment from the command line. The map locates time-zone names, not people, and its daylight shading is approximate (`web/src/messages.ts`, `web/src/ClockPanel.tsx`).

## Scenes
1. **World clock, light:** the genuine globe and city list at the fixed demo time, with two of three zones working.
2. **Team overview, dark:** the Core Today metric and primary footer clock in their surrounding app context.
3. **Footer detail:** open the primary clock to compare all three zones and their countdowns. This is a distinct interaction and detail state.
4. **Phone world clock:** the same real view at a narrow viewport, demonstrating its mobile presentation. Retain it only if the capture meaningfully shows that layout.
5. **CLI, current demo moment:** the native terminal table at 15:30 UTC.
6. **CLI, later overlap:** the same operation at 16:30 UTC, when all three fictional zones are working.
7. **CLI, JSON:** the structured result for the original moment, useful to automation.

## Fictional fixtures
`docs/screenshot_fixture.py` fixes the plugin clock at 2026-10-26 15:30 UTC, configures Berlin, New York and Los Angeles for 09:00–18:00, and enables the sidebar ticker and footer contribution. The plan also fixes browser time for the live frontend. The two `--at` CLI cases intentionally query different moments. No fixture execution or capture was performed here.

## Source-bound UI surface inventory
- **Plugin entrypoint:** `pyproject.toml` declares `heinzel.modules` entry `clock = "heinzel_clock"`; its actual declarations are in `src/heinzel_clock/__init__.py`.
- **Genuine feature view:** `module.nav` and `module.view(name="world-clock", source="clock")` declare `/?panel=clock:world-clock`. `web/src/index.ts` exports the ABI-1 view; `web/src/ClockPanel.tsx` implements the globe, city list, work states, rotation, fallback map, and settings shortcut. The declared packaged view is `src/heinzel_clock/views/index.js`. A missing WebGL context or reduced motion produces a static map, so verify the requested globe rather than assuming it rendered.
- **Core-rendered feature contributions:** `@module.status` declares the primary footer and sidebar ticker; `module.action("team-clock")` declares a header action with a working-count badge; `@module.widget` declares the Today metric. These are genuine plugin behavior rendered by Core, and their navigation targets the same panel (`src/heinzel_clock/__init__.py`).
- **Other Core surfaces:** `@module.settings`, `@module.setup`, and `@module.health` supply settings, optional setup, and Doctor checks. The operation declaration supplies a rendered table and data for Core integrations; `README.md` documents CLI, MCP and REST access. Their actual generic host presentation is not established by the provided Core source, so do not invent a separate operation screen or infer that these behaviors are terminal-only. No channel, approval, or info contribution is declared in the plugin module.
- **External provider UI:** none is declared; the globe source says it does not contact a map service (`web/src/ClockPanel.tsx`).
- **Evidence discrepancy:** `pyproject.toml` and `README.md` describe the two terminal examples as UI captures in an app terminal, whereas `docs/screenshots.toml` declares them as CLI scenes. The plan preserves the useful native CLI cases and does not count terminal output as feature UI. Reconcile catalog metadata with actual captures separately; no source edits are made here.

## Privacy pitfalls
Use only the isolated fictional profile and inspect every image and transcript independently for names, paths, hostnames, accounts and other identifying material. Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail and independent review must inspect every image and transcript.

## Acceptance criteria
Capture genuine app UI and native CLI output using the existing bootstrap only during explicit capture. Confirm the light and dark appearances are actually applied, the first two UI scenes show useful clock behavior, the footer detail is opened, and both CLI parameter cases have their expected distinct results. Confirm demo captions and time-zone data agree with each capture; reject duplicate captures, caption-only changes, terminal output presented as feature UI, and forged HTML. Independently review every image and transcript for privacy. The TOML below preserves the existing seven-scene plan and has been checked structurally against the supplied format by inspection; it has not been parser-validated or executed because code execution was prohibited.
