## Audience and outcome

For someone who wants a quick sense of the computer running their Heinzels, show how CPU, memory and load appear at a glance, then how to inspect the same sample in a terminal or consume structured output. The README says the plugin is included in the standard app; `pyproject.toml` also declares the `standard` profile.

## Scenes

1. **Expanded resource monitor:** Open the footer monitor to show the fictional host, CPU, memory, one-minute load and logical cores. This is the most complete feature view.
2. **Today at a glance:** Show the CPU widget in dark appearance, demonstrating the quick summary without opening the monitor.
3. **Phone monitor:** Show the same real monitor flow at a narrow viewport so a prospective user can judge its mobile presentation. This is a different viewport, not a substitute for a second feature state: the Today widget already provides that second state.
4. **CLI resource table:** Show the fictional sample in the command line, including raw load and core count.
5. **App terminal, table:** Run `hz resource` in the native app terminal for an in-app command result.
6. **App terminal, JSON:** Run `hz resource --json` in the same terminal to show the structured form useful to automation. These terminal results are terminal output, not feature UI.

The existing plan already covers the useful behavior, both terminal parameter cases, and light and dark views, so it is preserved. Captures must demonstrate genuinely different views or results; reject duplicates and caption-only variations.

## Fictional fixtures

`docs/screenshot_fixture.py` is the existing local bootstrap. It replaces `ResourceService.sample` for capture with `demo-workstation`, 36% CPU, 62% memory, load 0.65, eight logical cores, a fixed UTC sample time and no problems. These are demonstration values, not measurements of the viewer's machine. The plan's fixed browser time matches the sample. In normal use, `src/heinzel_resource/__init__.py` samples the host and may report unavailable values and explanations.

Normal presentation fictionalization also maps verified owning-interpreter paths to `/demo-profile/.venv`, and maps only the verified whole hostname detail in the genuine Doctor row to `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail and independent review must inspect every image and transcript. The fixture's `demo-workstation` is a separate fictional resource hostname, not permission to rewrite other identities.

## Privacy pitfalls

A real hostname appears in resource detail, CLI output and the plugin health check. Paths, account identifiers and unrelated hostnames may appear in Core UI or transcripts even with a fictional resource sample. Use the isolated fixture and review every image and transcript independently; fail unknown identities rather than guessing replacements. Optional dismissal of Doctor is a capture convenience, not proof that health or privacy checks passed. The provided sources do not establish the actual Doctor row's contents or verify an owning-interpreter path, so any permitted mapping depends on verification during review.

## Source-bound UI surface inventory

- `pyproject.toml` declares the sole `heinzel.modules` entrypoint, `resource = "heinzel_resource"`. Its actual declaration is `module = Module("resource", ...)` in `src/heinzel_resource/__init__.py`.
- The `@module.operation` named `resource` returns a `Resources` sample and supplies a Rich table renderer; the README documents `hz resource` and `--json`. The app terminal is a Core surface for these command results. The provided plugin code does not declare a separate feature page or route for the operation.
- `@module.status(source="resource", name="machine", ..., slots={"footer": True, "sidebar": False})` contributes the Core-rendered footer monitor, including meters and details. Its scaled load meter is distinct from the raw one-minute load displayed in the details and CLI table.
- `@module.widget(source="resource", name="machine", ...)` contributes the Core-rendered Today CPU summary. These footer and widget contributions establish useful feature UI even though no plugin Page or View is declared.
- `@module.health` declares `sampling`, returning a machine-resources check whose status depends on sample problems and whose detail includes the hostname. The provided source does not establish the full Core Doctor presentation or exact row contents.
- The module declares no channel, approval, setup, info, or plugin navigation contribution. No external-provider UI is evidenced. `web/build.py` is a frontend build helper, not a declared product screen; the provided files do not establish a plugin frontend route. The existing `/` captures rely on Core rendering and must be verified during capture.
- `README.md` and `pyproject.toml` describe a resource visualizer, while the supplied implementation proves the footer monitor and Today widget but does not independently establish any additional visualizer screen. Do not invent one.

## Acceptance criteria

- Capture at least the two genuine feature states: the expanded footer monitor and the Today widget, plus a useful CLI result. Treat the two native app-terminal commands as terminal results. Use actual Core-rendered UI and never forged HTML.
- Show applied light and dark appearances; verify that they rendered as intended. The phone capture must show the real monitor flow rather than a duplicate desktop image.
- Confirm the monitor, widget, table and JSON agree with the fictional fixture where their fields overlap; distinguish scaled load from raw load. Confirm both native terminal parameter cases finish successfully.
- Keep captions explicit about demo data. Independently inspect every image and transcript for identities and sensitive material, applying only the narrowly verified presentation mappings above; unknown identities fail review.
- Verify real controls, routes, accessibility names, viewport behavior and image contents at capture time. The supplied plan and declarations are evidence of intent, not evidence that capture or privacy acceptance has already succeeded.
