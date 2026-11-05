## Audience

Someone deciding whether to install System Resources who wants a quick picture of the computer running Heinzel and a way to retrieve the same measurements in a command or automation.

## Outcome

Show how a glance at Today and the footer leads to a useful expanded monitor, then show the underlying sample in the CLI and app terminal. The readings are a fictional demonstration, not a claim about the viewer’s machine.

## Scenes

1. **Expanded resources:** In light appearance, open the footer’s computer-resources status to show CPU, memory, scaled load, hostname, and the explanation of the load bar. This is the central feature view.
2. **Today at a glance:** In dark appearance, show the CPU widget together with the compact footer meters. This is a different useful state of the same Core UI, not a duplicate of the expanded monitor.
3. **Phone monitor:** Open the resources detail at a narrow viewport to show that the same readings can be inspected on a phone. Review the result for meaningful mobile layout; reject it if it merely duplicates the desktop crop.
4. **CLI sample:** Show `hz resource` as a native CLI result, with the fictional hostname, CPU, memory, raw one-minute load, and logical cores.
5. **App terminal table:** Run `hz resource` in the app terminal to show an interactive route to the sample.
6. **App terminal JSON:** Run `hz resource --json` in the app terminal to show the structured form useful for automation. These two terminal captures demonstrate different parameter cases of the single operation; neither is presented as feature UI.

## Fictional fixtures

The existing `docs/screenshot_fixture.py` replaces `ResourceService.sample` during explicit capture with `demo-workstation`, CPU 36%, memory 62%, one-minute load 0.65, eight logical cores, no problems, and a fixed UTC sample time. The scaled load meter is derived from that sample; it is not the raw load value. The plan uses this existing bootstrap and a matching browser time. No fixture file needs to be invented.

Normal presentation fictionalization is explicitly permitted for verified owning-interpreter paths, which become `/demo-profile/.venv`, and for only the verified whole hostname detail in the genuine Doctor row, which becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript.

## Privacy pitfalls

The fixture substitutes resource readings, but other Core surfaces, Doctor output, paths, terminal transcripts, and surrounding profile data can still reveal real identities or machine details. Do not generalize the two permitted mappings to unverified paths, partial hostname matches, other rows, or other identities. Inspect every image and transcript independently before publication; fail on unknown identities. A dismissed Doctor banner is not proof that no sensitive detail remains elsewhere.

## Source-bound UI surface inventory

- `pyproject.toml`, `[project.entry-points."heinzel.modules"]`, declares `resource = "heinzel_resource"`. The actual entrypoint in `src/heinzel_resource/__init__.py` constructs `module = Module("resource", ...)` and registers `ResourceService`.
- `@module.operation(render=render, audience="everyday")` declares the single `resource` operation. `render` produces the CLI table; the README documents `hz resource` and `--json`. The app terminal can invoke this operation, but terminal output is not a resource feature view. No CLI-only status should be inferred from the absence of a Page or View.
- `@module.status(source="resource", name="machine", refresh="2s", ... slots={"footer": True, "sidebar": False})` contributes a Core-rendered footer status with three meters and expandable detail. `@module.widget(source="resource", name="machine", refresh="1m", ...)` contributes the Core-rendered Today metric. These are genuine feature UI and support the first three scenes on the existing `/` route. Different states of that route qualify; no distinct plugin route is needed.
- `@module.health` declares the `sampling` check, which can contribute to Core health/Doctor presentation. It reports degraded when the sample has problems and otherwise up; its hostname and detail must not be rewritten beyond the explicitly permitted verified Doctor-row mapping.
- The declared module contains no plugin Page, View, navigation, channel, approval, setup, or info contribution. No external provider UI is declared. Generic Core operation and health surfaces still exist despite the absence of a Page or View; the supplied source does not establish additional plugin-specific routes or screens.
- `README.md` says readings appear on Today and in the footer; `pyproject.toml` catalog metadata also calls out a resource visualizer. The supplied declarations establish the widget and footer detail, but do not independently declare a separate visualizer page. The plan therefore captures the evidenced Core surfaces. `web/build.py` is a frontend build helper, not a declared UI entrypoint; the supplied file inventory contains no frontend implementation establishing another screen. Catalog and README reference generated images that are not present in the supplied file inventory, so their appearance is not verified here.

## Acceptance criteria

- Capture at least the two distinct genuine feature states: expanded footer detail in light appearance and Today plus footer in dark appearance, along with a useful CLI result. Applied appearance must be visible in the captured views.
- Show the fixture’s values consistently, distinguish scaled load from raw load, and retain genuine Core rendering. Capture the two app-terminal parameter cases as terminal results, not feature views.
- Reject forged HTML, duplicate captures, caption-only differences, invented routes or screens, and mobile captures that add no meaningful information. Captions identify demo data.
- During explicit capture, verify the planned accessible controls and text against the actual running Core UI; the provided source does not prove their runtime accessibility or the resulting crops. Validate the resulting TOML with the capture tooling before use. No project code was executed for this proposal.
- Independently inspect every image and transcript for privacy and factual accuracy, applying only the explicitly permitted verified mappings; unknown identities fail. Preserve health status and all other Doctor detail.
