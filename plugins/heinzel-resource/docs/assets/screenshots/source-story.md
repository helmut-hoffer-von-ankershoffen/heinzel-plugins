## Audience
People deciding whether the standard Heinzel app gives them a quick, useful view of the machine running their Heinzels, and whether they can also use those measurements from the command line.

## Outcome
Show a fictional workstation at a glance on Today, open its footer monitor for more detail, and demonstrate the same sample in human-readable and structured command output. The load meter is scaled; the expanded detail and CLI show the raw one-minute load.

## Scenes
1. **Expanded monitor, light:** Open the Computer resources footer item to show the fictional host, CPU, memory, one-minute load and core count.
2. **Today, dark:** Show the fictional CPU summary in its everyday context.
3. **Phone:** Open the same monitor at a narrow viewport to show how its detail can be read on a phone. This is a responsive view of the same feature, not a separate feature.
4. **CLI:** Show the human-readable resource table for the same fictional sample.
5. **App terminal:** Show the human-readable command in the native terminal.
6. **App terminal, JSON:** Show the structured result for automation. These two terminal scenes demonstrate distinct parameter cases of the single operation; neither substitutes for feature UI.

## Fictional fixtures and presentation
`docs/screenshot_fixture.py` supplies a deterministic sample: `demo-workstation`, CPU 36%, memory 62%, one-minute load 0.65, eight logical cores and no problems. It is an existing capture bootstrap, not a production measurement. Captions identify the values as demo data.

For normal presentation fictionalization, verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail and independent review must inspect every image and transcript.

## Privacy pitfalls
Hostnames, interpreter paths, account information and other environment-specific details may appear outside the resource fixture, including in Core surfaces or transcripts. Do not infer that dismissal of Doctor or the two permitted mappings removes all identifying information. Reject unknown identities and independently inspect every image and transcript before publication.

## Source-bound UI surface inventory
- `pyproject.toml`, `[project.entry-points."heinzel.modules"]`: the sole declared module entrypoint is `resource = "heinzel_resource"`. Its actual declarations are in `src/heinzel_resource/__init__.py`.
- `@module.status(...)` declares the Core-rendered footer item, its CPU, memory and scaled-load meters, and expanded detail. This is genuine feature UI; the declaration explicitly disables its sidebar slot.
- `@module.widget(...)` declares the Core-rendered Today metric widget, showing CPU. The light expanded monitor and dark Today scene are useful feature UI states; no plugin Page or View is needed to establish them.
- `@module.operation(render=render, audience="everyday")` declares the `resource` operation and its Rich table. The README documents `hz resource` and `--json`. The app-terminal scenes are terminal output within Core, while the CLI scene is a standalone terminal capture. No separate operation-specific Core screen is established by the supplied source.
- `@module.health` declares the machine-resources health check, which can contribute to Core Doctor. It is not a dedicated plugin screen. Its status depends on sampling problems; fictionalization must not alter it.
- The module source declares no channel, approval, setup, info, plugin navigation, Page or View contribution. No external provider UI is declared. Generic Core routes exist, but the supplied declarations do not connect this plugin to a separate route; the plan uses `/` for its actual widget, footer and app terminal.
- `pyproject.toml` calls the feature a “Resource visualizer,” while the supplied module declares a metric widget and status meters rather than a separate visualizer page. The existing screenshot plan supplies the accessible names and interactions for those Core surfaces, but their live rendering and exact selectors remain capture-time evidence to verify.

## Acceptance criteria
- Capture the actual Core-rendered widget and expanded footer monitor, with applied dark and light appearances respectively, plus the useful CLI result. Confirm each image shows the named state and fictional sample.
- Verify phone layout and both native-terminal parameter cases; terminal output must remain visibly terminal output. Reject duplicate captures, caption-only differences and forged HTML.
- Confirm the raw load is not described as the scaled meter value, and the fictional healthy sample is not presented as evidence of a real machine’s health.
- Use the existing bootstrap only during explicit capture. Independently inspect every image and transcript for identities and other private data; unknown identities fail review. The permitted presentation mappings do not constitute privacy acceptance.
- Capture and freshness checks remain to be run: this response is based solely on reading the supplied files, with no plugin execution or visual verification.
