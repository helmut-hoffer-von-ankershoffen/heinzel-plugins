## Audience

Someone deciding whether Heinzel can give them a quick view of the computer running their Heinzels, and whether they can also use the readings from the command line.

## Outcome

Show a fictional workstation’s CPU, memory and load at a glance, then reveal the fuller resource detail and the same sample in human-readable and structured command output. The plugin is included in the standard app; its measurements describe the machine running `hz`, not necessarily the machine viewing the app (`README.md`; `src/heinzel_resource/__init__.py`, `Resources` and `ResourceService.sample`).

## Scenes

1. **Expanded monitor, light:** Open the footer’s resource control to reveal the host, CPU, memory, one-minute load and logical cores. The meters make the readings easy to scan; the detail explains the load value. (`machine` status declaration.)
2. **Today, dark:** Show the compact CPU widget alongside the footer meters in the normal app context. This is a different useful state of the same Core interface, not a second invented plugin page. (`overview` widget and `machine` status declarations.)
3. **Phone monitor:** Open the same resource detail at a narrow viewport to show that it remains usable on a phone. This is a responsive view, not a claim of different functionality.
4. **CLI:** Show `hz resource` as a native CLI result, with the fictional host, CPU, memory, raw one-minute load and logical cores. (`resource` operation and `render`.)
5. **App terminal, table:** Run `hz resource` in the genuine app terminal so an app user can see the readable table in context.
6. **App terminal, JSON:** Run `hz resource --json` in the genuine app terminal to show the structured form for automation. These two parameter cases are distinct useful results of the one declared CLI operation; neither is presented as feature UI. (`README.md`; `resource` operation.)

## Fictional fixtures and presentation

`docs/screenshot_fixture.py` is the existing capture bootstrap. It replaces the sampler with a fictional `demo-workstation` sample: CPU 36%, memory 62%, one-minute load 0.65, eight logical cores, no problems, sampled at 2026-10-31 10:00 UTC. The footer load meter is scaled against twice the core count, while its detail and CLI show raw load (`machine`; `render`). The fixed browser time matches the sample. This is demonstration data, not a live benchmark or evidence of real machine health.

Normal presentation fictionalization is explicitly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail and independent review must inspect every image and transcript. The fixture’s `demo-workstation` is separately supplied plugin sample data, not permission to substitute arbitrary hostnames.

## Privacy pitfalls

The real sampler calls `gethostname()` and reads local machine metrics. Core chrome, Doctor output, terminal transcripts, paths, account information and unrelated notifications can also expose real information even when the plugin sample is fictional. Review every image and transcript independently, including cropped and mobile captures; reject unknown identities and any unverified substitution. Do not infer privacy acceptance from the fixture, the two narrowly specified presentation mappings, or a clean-looking contact sheet alone.

## Acceptance criteria

- Capture the genuine Core-rendered Today widget and expanded footer detail in applied dark and light appearances, plus the responsive phone view. Confirm the shown values and raw-versus-scaled load distinction against the fixture and declarations.
- Capture the native CLI result and both genuine app-terminal parameter cases. The terminal steps wait for completion; do not add waits for individual table cells.
- Keep each image meaningfully different: reject duplicate captures, caption-only changes, terminal output labeled as feature UI, and forged HTML. Use real app surfaces and the existing fixture only.
- Preserve actual SDK and Doctor health statuses and all other details during the disclosed presentation mappings. Independently inspect every image and transcript for privacy, including unknown identities.
- Check that captions identify demo data and that the plan parses and conforms to the capture format before capture. This plan was reviewed statically; no code or capture was executed.

## Source-bound UI surface inventory

- `pyproject.toml`, `[project.entry-points."heinzel.modules"]`: the sole declared module entrypoint is `resource = "heinzel_resource"`; `[tool.heinzel.plugin]` places it in the standard profile. No plugin navigation entry or custom Page/View is declared in the provided module.
- `src/heinzel_resource/__init__.py`, `@module.widget(... name="machine" ...)` and `overview`: a Core-rendered Today metric labeled “Computer resources” shows CPU and refreshes every minute. This is genuine feature UI.
- The same file, `@module.status(... slots={"footer": True, "sidebar": False})` and `machine`: Core renders footer meters and expandable detail, refreshed every two seconds. This is genuine feature UI; there is no declared sidebar status for it.
- The same file, `@module.operation(render=render, audience="everyday")`, `resource`, and `render`: the operation supplies CLI output and may also be invoked through the Core app terminal. Its table and JSON are command results, not a plugin-owned page. The provided declarations do not establish another generic Core operation screen, so none is invented.
- The same file, `@module.health` and `sampling`: health contributes a genuine Doctor check, with a hostname-bearing detail and UP or DEGRADED status based on sample problems. It may appear in Core Doctor UI; its exact surrounding presentation is not declared here and must be verified during capture.
- No channels, approvals, setup, info, plugin navigation, or external-provider UI contributions are declared in the provided source. Absence of a custom Page/View does not negate the declared Core widget, footer or health surfaces.
- `pyproject.toml` catalog captions and `README.md` describe the expanded monitor, Today, phone, CLI and terminal captures. The existing plan captures those behaviors. Its Today caption mentions only CPU while the catalog also mentions footer meters; the screenshot should be reviewed to confirm the meters are visible. Actual capture rendering and the availability of the referenced Core controls remain unverified from these files alone.
