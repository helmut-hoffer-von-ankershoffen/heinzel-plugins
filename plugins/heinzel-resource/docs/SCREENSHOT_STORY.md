## Audience and outcome

For someone deciding whether to install System Resources: see at a glance whether the machine running Heinzel is busy, open the footer monitor for context, and retrieve the same sample in a terminal or as JSON. The README says the plugin is included in the standard app (`README.md`; `pyproject.toml`, `[tool.heinzel.plugin]`).

## Scenes

1. **Expanded monitor, light:** open the genuine footer contribution to see fictional CPU and memory percentages, one-minute load and logical cores together. The load meter is scaled; the detail line reports raw load.
2. **Today and footer, dark:** show the fictional CPU summary in the Today widget alongside the three footer meters, demonstrating the useful at-a-glance state.
3. **Phone monitor:** show the same genuine monitor at a narrow viewport, including its fictional host and measurements. This demonstrates the responsive flow rather than claiming another feature.
4. **Native terminal table:** run `hz resource` to show the fictional hostname, CPU, memory, raw one-minute load and logical cores.
5. **Native terminal JSON:** run `hz resource --json` to show the structured fictional sample for automation. This is a second parameter case of the same operation.

## Fictional fixtures

The existing `docs/screenshot_fixture.py` replaces `ResourceService.sample` during explicit capture with a fictional `demo-workstation`: CPU 36%, memory 62%, one-minute load 0.65, eight logical cores, no problems, and a fixed UTC sample time. It launches the actual Heinzel entrypoint. The plan retains that bootstrap and fixed browser time; it does not introduce fixture files.

## Source-bound UI surface inventory

- `pyproject.toml`, `[project.entry-points."heinzel.modules"]`, declares `resource = "heinzel_resource"`; `src/heinzel_resource/__init__.py` defines its actual `module = Module(...)`. This is the only declared Heinzel module entrypoint in the provided project.
- `@module.operation(render=render, audience="everyday")` declares the `resource` operation and its Rich table. The README documents `hz resource` and `--json`. Core may expose operations through generic surfaces, including its app terminal; the table and JSON are genuine terminal results, not invented plugin pages.
- `@module.status(... slots={"footer": True, "sidebar": False})` contributes the footer item, meters and expandable detail. `@module.widget(...)` contributes the Today metric. These are genuine Core-rendered feature UI, even though this module declares no Page or View. The source supplies their content; exact Core layout and interaction must be confirmed during capture.
- `@module.health` declares a machine-resources Doctor check. It is a health contribution, not a separate plugin feature screen. Core may display it in Doctor; the provided source does not establish its complete presentation.
- The complete module declares no channels, approvals, setup flows, info contributions, plugin navigation routes, or external provider UI. No plugin-specific route is assumed. `/` is the supplied generic Core route used by the existing plan.
- `pyproject.toml` catalog captions describe an expanded monitor with scaled load, while the existing plan's expanded caption emphasizes one-minute load and cores; the source supports both the scaled meter and raw detail. The catalog calls the CLI screenshot the same measurements, but the actual table also includes hostname and cores. `web/build.py` is a build helper, not a declared product UI entrypoint. The provided sources do not prove that any existing screenshot files are present or current.

## Privacy pitfalls

The fixture replaces plugin samples, but Core and other installed components may still expose real paths, hostnames, accounts, timestamps or other identity. Normal presentation fictionalization maps verified owning-interpreter paths to `/demo-profile/.venv`, and maps only the verified whole hostname detail in the genuine Doctor row to `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail. Independent review must inspect every image and transcript, including cropped and mobile captures, before publication.

## Acceptance criteria

- Capture the real Today widget and footer monitor in at least two useful feature UI scenes, with applied light and dark appearances, plus the phone state and both native terminal parameter cases. Confirm the expected UI interactions and responsive layout against the running Core before accepting captures.
- Verify fixture values and distinguish scaled load from the raw 0.65 load; retain actual unavailable or health information if the capture differs rather than inventing a healthy result.
- Reject duplicate captures, caption-only variations, terminal output represented as feature UI, and forged HTML. The phone capture must demonstrate a useful narrow-screen state.
- Independently inspect every image and transcript for privacy and factual accuracy. Apply only the stated verified mappings; fail on unknown identities.
- The TOML below was checked against the supplied field and action rules by inspection. Capture, runtime route behavior, and parser validation were not executed under the read-only, no-code-execution constraint.
