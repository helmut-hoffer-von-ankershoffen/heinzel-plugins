## Audience and outcome

For someone deciding whether the included System Resources plugin makes a quick machine check convenient: see a glanceable CPU summary, open the footer monitor for CPU, memory and load, and compare that with the command-line and structured results. The fixture is illustrative; it does not claim to measure the viewer’s machine.

## Scenes

1. **Expanded monitor, light:** Open the footer resource item and inspect its three meters and explanatory detail. The load bar is scaled against twice the logical core count; the detail also shows the raw one-minute load.
2. **Today, dark:** Show the CPU widget alongside the compact footer meters in a genuinely different, collapsed state.
3. **Phone:** Open the same monitor at a narrow viewport to show how the detail can be read on a phone. This is a responsive view, not a separate feature.
4. **CLI:** Show `hz resource` with hostname, CPU, memory, raw one-minute load and logical cores.
5. **App terminal, table:** Run the same operation in the native app terminal.
6. **App terminal, JSON:** Run `hz resource --json` to show the structured result useful for automation. The terminal scenes show two parameter cases of the single operation; they are not feature UI substitutes.

The existing plan already covers these useful states, so the plan below retains it and adds explicit light and dark appearances. Each capture must show the stated state; a repeated image or a changed caption alone does not satisfy a scene.

## Fictional fixtures and presentation

`docs/screenshot_fixture.py` supplies an isolated fictional `demo-workstation` sample: CPU 36%, memory 62%, one-minute load 0.65, eight logical cores, no problems, and a fixed UTC sample time. It substitutes the resource service only when explicitly used for capture. `docs/SCREENSHOTS.md` describes a temporary fictional profile without connected accounts.

Normal presentation fictionalization maps verified owning-interpreter paths to `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row to `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript. The fixture’s `demo-workstation` is separate example data and must not be represented as a real host.

## Source-bound UI surface inventory

- `pyproject.toml`, `[project.entry-points."heinzel.modules"]`: `resource = "heinzel_resource"` is the declared plugin entrypoint. Its actual declarations are in `src/heinzel_resource/__init__.py`.
- `@module.operation(render=render, audience="everyday")` declares the `resource` operation. `render` creates the CLI table, and README.md documents `hz resource` and `--json`. The existing plan also exercises Core’s app terminal. The supplied source does not establish a separate operation form or route; inspect any actual Core-rendered operation surface during capture rather than inventing one.
- `@module.status(... slots={"footer": True, "sidebar": False})` declares the Core footer contribution. Its expandable detail and meters provide the genuine resource feature UI; no sidebar contribution is declared. `@module.widget(...)` supplies the Core Today metric widget. The plan’s `/` route and accessible controls are supported by the existing capture plan, but their successful rendering remains to be verified.
- `@module.health` declares the `sampling` check, which reports `UP` or `DEGRADED` and includes a hostname in its detail. A genuine Core Doctor row may expose it; its exact presentation is not declared in the supplied plugin source. Do not fabricate or alter its status or detail.
- No plugin Page, View, navigation, channel, approval, setup, or info contribution is declared in the inspected entrypoint. That absence does not by itself rule out Core-rendered surfaces from the declared operation, widget, status, or health check. No external provider UI is declared. `web/build.py` is a build helper, not evidence of another product screen.
- The README and catalog include app-terminal scenes classified as `ui`; their content is terminal output, not resource feature UI. The expanded monitor and Today/footer states supply the required two useful feature UI scenes.

## Privacy pitfalls and acceptance criteria

- Capture only with the existing fixture and fictional profile; verify sample values and the intended state in every image and transcript. Never invent a fixture file or forge HTML.
- Independently inspect every image and transcript for real hostnames, interpreter paths, account identifiers, and other identities. Apply only the explicitly permitted verified mappings above; unknown identities fail review. Dismissing Doctor where the existing plan requests it does not replace privacy review.
- Verify that light and dark appearances are actually applied, that the phone view remains readable, and that the monitor detail explains scaled versus raw load. Reject blank, duplicate, caption-only, or terminal-as-feature-UI captures.
- Verify the CLI table and both native-terminal parameter cases complete and show the fixture data. The terminal action already waits for completion; no individual table-cell waits are needed.
- Confirm routes, controls, and any additional Core-generated surfaces against the running product before accepting captures. The provided declarations and existing plan do not prove that the captures currently render successfully.
