## Audience

Someone deciding whether the standard Heinzel app’s resource monitor gives them a useful, at-a-glance picture of the computer running their Heinzels, as well as a script-friendly sample.

## Outcome

Show the path from a quiet Today summary to a detailed explanation of CPU, memory and load, then show the same fictional sample in human-readable and structured command output. The monitor is included in the standard app, according to `README.md` and the `standard` profile in `pyproject.toml`.

## Scenes

1. **Expanded monitor, light:** Open the footer’s Computer resources item and focus its detail region. The fictional workstation shows CPU, memory, scaled load, host and core context. The detail explains that the load bar reaches 100% at twice the logical core count.
2. **Today and footer, dark:** Show the fictional CPU summary alongside the compact footer meters. This is a distinct overview state of the actual feature, and complements the expanded light view.
3. **Phone monitor:** Open the same detail on a narrow viewport, using the overflow control if present. This demonstrates the actual mobile layout rather than another caption on the desktop capture.
4. **CLI table:** Show `hz resource` with the fictional hostname, CPU, memory, raw one-minute load and logical core count.
5. **App terminal, table:** Run `hz resource` in the native app terminal so a user can see the human-readable result in context.
6. **App terminal, JSON:** Run `hz resource --json` in the native app terminal to show the structured sample useful for automation. These terminal scenes are command results, not feature UI substitutes.

The existing plan already expresses these useful states, including two parameter cases for the single operation, so it is preserved below. Successful capture and visual appearance have not been verified here.

## Fictional fixtures

`docs/screenshot_fixture.py` supplies the existing isolated capture bootstrap: `demo-workstation`, timestamp `2026-10-31T10:00:00Z`, CPU 36%, memory 62%, one-minute load 0.65, eight logical cores and no reported problems. The plan fixes browser time to the same instant. These are presentation examples, not measured performance or a promise of normal usage. The displayed load meter is scaled from raw load, while the CLI table reports the raw value (`src/heinzel_resource/__init__.py`, `machine` and `render`).

Normal presentation fictionalization must be explicitly disclosed: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail and independent review must inspect every image and transcript.

## Source-bound UI surface inventory

- **Plugin entrypoint:** `pyproject.toml` declares `heinzel.modules` entry `resource = "heinzel_resource"`; `src/heinzel_resource/__init__.py` declares `module = Module("resource", ...)` and registers `ResourceService`.
- **Core feature UI:** `@module.status(source="resource", name="machine", refresh="2s", order=600, slots={"footer": True, "sidebar": False})` contributes footer meters and expandable detail. `@module.widget(source="resource", name="machine", refresh="1m", order=600)` contributes the Today CPU metric. These are genuine feature surfaces even though this plugin declares no Page or View. The plan uses the supplied generic Core route `/`; the exact accessible controls and layout remain capture-time evidence to verify.
- **Operation and CLI:** `@module.operation(render=render, audience="everyday")` declares `resource`; `render` builds the human-readable resource table. `README.md` documents `hz resource` and `--json`. The operation can also appear in Core-rendered contexts; its app-terminal output must be identified as terminal output.
- **Health:** `@module.health` declares `sampling`, returning a machine-resources check whose status depends on sampling problems and whose detail contains the hostname. A genuine Doctor row may expose that detail; the supplied source does not establish the complete Core Doctor layout or an SDK health row’s contents. Preserve observed status and other details.
- **Other contributions:** The inspected module contains no declared plugin navigation, Page, View, channel, approval, setup, or info contribution. No external provider UI is declared. This is a finding about the supplied plugin declarations, not proof that Core has no generic operation or health surfaces. `web/build.py` is a frontend build helper, not evidence of an additional screen; no frontend entrypoint is declared in the supplied `pyproject.toml`.
- **Evidence limits:** `README.md` and the existing plan describe captures, but do not prove that the current Core version renders the named controls or that existing images are fresh. The monitor’s footer refresh and Today widget refresh differ, and the fixture fixes their sample; capture should verify the actual rendered result rather than infer it from captions.

## Privacy pitfalls

The real sampler uses the machine hostname and current measurements, and the health check includes that hostname in its detail. Core or the terminal may also expose paths or other identifying context. Use the existing fictional bootstrap, apply only the narrowly verified presentation mappings above, and fail on unknown identities rather than guessing replacements. Independently inspect every image and transcript, including surrounding Core chrome, Doctor details and terminal output; a fixture or mapping alone is not privacy acceptance.

## Acceptance criteria

- Capture at least the two genuine feature states: expanded resource detail and Today/footer overview, with light and dark appearances actually applied. Retain the useful phone, CLI table and two native-terminal parameter cases where they render as planned.
- Show fixture values consistently; distinguish scaled load from raw load and preserve the genuine health status and all unmapped details.
- Confirm the actual route, accessible controls, optional Doctor dismissal and mobile overflow behavior against the rendered Core UI. Resolve any discrepancy from source or capture evidence instead of inventing a route, screen, selector or HTML.
- Reject duplicate captures, caption-only differences, terminal output labeled as feature UI, and forged HTML. Review each image and transcript independently for identities and other private context.
- Treat the plan as statically checked against the requested field and action shapes; TOML parsing, bootstrap execution, capture, and visual or privacy acceptance were not run.
