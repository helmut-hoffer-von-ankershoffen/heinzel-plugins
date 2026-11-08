## Audience
A distributed team deciding whether World Clock makes it easier to find a good time to work together, and whether its data is useful in scripts.

## Outcome
Show the same fictional team across a globe, the app’s everyday overview and footer, and command-line results. At the fixed demonstration moment, Berlin and New York are working and Los Angeles starts in 30 minutes; an hour later all three are working.

## Scenes
1. **World clock:** In light appearance, show the genuine globe and zone list for the three fictional cities, with the Today count visible. Wait for the real view and WebGL rather than substituting a mockup.
2. **Team overview:** In dark appearance, show the Core-rendered Today metric, sidebar ticker and primary footer clock together. This is a distinct everyday use of the same underlying clock data.
3. **Footer detail:** Open the primary clock’s genuine detail pane and crop to its zone list and workday countdowns.
4. **Phone world clock:** Show the real panel at phone width, with its globe and zone list. This demonstrates responsive use, not a different feature.
5. **Current terminal result:** In the native app terminal, run the clock operation at 15:30 UTC to show the table and current working states.
6. **Overlap terminal result:** Run the same operation at 16:30 UTC to show the changed working states. These two app-terminal scenes are terminal output, not feature UI.
7. **CLI JSON:** Capture the structured result for the same fictional team at 15:30 UTC, showing its usefulness to scripts and agents.

## Fictional fixtures
Use the existing `docs/screenshot_fixture.py`: it fixes the plugin clock at 2026-10-26 15:30 UTC, configures Berlin, New York and Los Angeles with 09:00–18:00 hours, and enables the sidebar and footer contributions. `browser_time` aligns the browser with that moment. The two explicit `--at` arguments demonstrate different moments without claiming the live clock itself has changed. No additional fixture file is assumed.

Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript.

## Privacy pitfalls
Capture only in the isolated fictional profile; check the entire frame, terminal output and transcripts for real names, hostnames, paths, accounts, tokens and unrelated notifications. Dismissing a Doctor banner does not prove the rest of a capture is private. Do not replace unknown identities with invented ones or alter health results. Independently review every image and transcript before publication.

## Acceptance criteria
- Capture the actual plugin view and Core contributions, with readable fictional data and consistent times. The light World Clock and dark overview must have their appearances applied and visible.
- Show at least two useful genuine feature UI scenes plus a CLI result. The overview and footer detail are meaningful Core-rendered feature states; the two terminal scenes do not count as feature UI.
- The two terminal tables must reflect their respective `--at` values; the JSON capture must be genuine operation output. Terminal actions wait for completion without per-cell exact-text waits.
- Reject duplicate captures, caption-only differences, terminal output presented as feature UI, forged HTML, missing or blank globe rendering, misleading status changes, and unreviewed personal data. Check the phone capture for usable content rather than assuming responsive success.
- Confirm the footer detail’s Primary presentation matches the installed host: the source supports a badge on newer hosts and text on older ones. Treat a failed or unavailable surface as unresolved evidence, not permission to invent a replacement.
- The plan below preserves the existing useful scenes and bootstrap. It is structurally reviewed against the supplied scene rules, but capture, runtime behavior and parser validation have not been executed.

## Source-bound UI surface inventory
- `pyproject.toml`, `[project.entry-points."heinzel.modules"]`: the sole declared module entrypoint is `clock = "heinzel_clock"`. `src/heinzel_clock/__init__.py`, `module.nav` and `module.view`: the actual World Clock panel route is `/?panel=clock:world-clock`; its ABI 1 view consumes the `clock` operation. `web/src/index.ts`, `createView`, and `web/src/ClockPanel.tsx`, `WorldClock`, establish the genuine globe, zone list, work states, clock controls and settings shortcut. Reduced motion or WebGL failure uses a local static map; there is no external map UI or map-service request.
- `src/heinzel_clock/__init__.py`, `@module.operation` on `clock` and `_render`: one operation yields zone, local time, hours, working state and primary designation; the CLI renders a table, while `README.md` documents `--json`, MCP and REST. MCP and REST are interfaces, not evidence of separate product screens. The two app-terminal scenes are useful parameter cases of that operation.
- The same source’s `@module.status` declarations `primary-zone` and `zones-ticker`, `module.action("team-clock", ...)`, and `@module.widget` `at_work` contribute a footer detail, sidebar ticker, header action and Today metric to Core. These are genuine Core-rendered feature surfaces, not separate plugin routes. The fixture explicitly enables the two status slots.
- `@module.settings` and `module.nav(... settings=NavSettings(...))` declare Core settings; `@module.setup` declares an interactive setup flow; `@module.health` declares Doctor checks for zones and deprecated configuration. These are supporting Core surfaces, not the principal story. The exact Doctor host row and owning-interpreter paths are not declared by this plugin; only verified occurrences qualify for the disclosed mappings.
- No channel, approval or info contribution is declared in `src/heinzel_clock/__init__.py`; no external provider UI is evidenced by the supplied source. The module docstring describes three views but the actual declarations also include the separately registered World Clock view and two status items; declarations govern this inventory.
- `pyproject.toml` and `README.md` list a catalog screenshot named `cli-times.png`, while the existing plan names the CLI scene `cli-json`; the supplied files do not establish whether generated artifacts currently agree. Verify generated catalog references during capture rather than claiming freshness. `docs/SCREENSHOTS.md` references a repository-level author guide outside the supplied files, so its additional requirements remain unresolved.
