## Audience and outcome

For someone deciding whether the standard Heinzel app gives them a quick view of the machine running their Heinzels. The gallery shows how to glance at CPU on Today, open the footer monitor for more context, and retrieve the same sample for terminal or automation use. The plugin is included in the standard app, according to `README.md`.

## Scenes

1. **Expanded resource monitor, light:** Open the real footer contribution to see the fictional workstation’s host, CPU, memory, one-minute load and core count. The load meter is scaled; the detail line shows the raw load.
2. **Today, dark:** See the fictional CPU reading in the actual Today widget, illustrating the quickest glanceable view.
3. **Phone monitor:** Open the same footer monitor at a phone viewport to show its useful compact flow. This is a different presentation of the real monitor, not a separate feature.
4. **CLI table:** Show `hz resource` with the fictional sample and its raw measurements.
5. **App terminal, table:** Run `resource` in the native app terminal to show the readable result in context.
6. **App terminal, JSON:** Run `resource --json` in the native app terminal to show the structured result useful for automation.

The two terminal scenes are terminal results, not feature UI. Retain them because the single declared operation has two useful parameter cases. Reject duplicate captures and caption-only variations.

## Fictional fixtures

`docs/screenshot_fixture.py` is the existing capture bootstrap. It replaces `ResourceService.sample` for the capture with `demo-workstation`, CPU 36%, memory 62%, load 0.65, eight logical cores, no problems and a fixed UTC sample time. These are demonstration values, not measurements or a promise of performance. The plan fixes browser time to the sample date. The bootstrap is for explicit capture only.

Normal presentation fictionalization must be disclosed: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail; independent review must inspect every image and transcript. The fixture’s `demo-workstation` resource hostname is a separate fictional sample value and must not be confused with the Doctor-row mapping.

## Privacy pitfalls

Real resource samples include a hostname and machine measurements (`src/heinzel_resource/__init__.py`, `Resources` and `ResourceService.sample`); health details can include the hostname and problem text (`sampling`). The surrounding Core UI and transcripts may contain other paths, identities or account information outside the fixture’s control. Fail on unknown identities rather than assuming the two disclosed mappings cover them. Independently inspect every capture and transcript, including Doctor, terminal output, and any surrounding chrome before publication.

## Source-bound UI surface inventory

- `pyproject.toml`, `[project.entry-points."heinzel.modules"]`, declares the single plugin entrypoint `resource = "heinzel_resource"`; `src/heinzel_resource/__init__.py` declares `module = Module(...)` and registers `ResourceService`.
- `@module.operation(render=render, audience="everyday")` declares `resource`: a Core-exposed operation with a Rich table renderer and structured `Resources` result. `README.md` documents `hz resource` and `--json`. The supplied plan also exercises both cases in the app terminal. This is an operation surface, not evidence for a separate plugin page.
- `@module.status(... slots={"footer": True, "sidebar": False})` declares the genuine Core-rendered footer status, meters and expanded detail. `@module.widget(...)` declares the genuine Core-rendered Today metric widget. These are the two useful feature UI scenes even though both use `/`.
- `@module.health` declares the `machine resources` check and its status/detail. It may appear through Core health/Doctor UI; the supplied files do not specify that UI’s full rendering or identify a separate plugin route. The fixture cannot establish the rest of Doctor’s health or privacy state.
- The supplied entrypoint declares no plugin page, view, navigation, channel, approval, setup, or info contribution, and no external provider UI. Absence of a page does not imply terminal-only behavior: the declared footer and widget are real Core-rendered feature surfaces. `web/build.py` is a generic build helper, not a declared product screen. No additional route is inferred.
- `pyproject.toml` catalog and `README.md` describe existing intended screenshots, including app-terminal captures labeled `ui`; their actual content is terminal output and must be described that way. The referenced image assets are not among the supplied files, so their current appearance and freshness are unverified. `docs/SCREENSHOTS.md` describes a gallery workflow but does not prove a capture succeeded.

## Acceptance criteria

- Capture the genuine expanded footer monitor and Today widget with the fixture values, plus a useful CLI result; light and dark appearances must actually be applied and visible. Verify the phone flow and both native terminal parameter cases if included.
- Confirm values and labels against the fixture and declarations. Preserve unavailable values, problems and health status truthfully; do not fabricate a healthy result or hide remaining detail.
- Use the real app and declared operation only: no forged HTML, invented screens or routes, terminal output presented as feature UI, duplicate images, or caption-only changes.
- Independently review every image and transcript for unknown identities and other private material. Apply only the disclosed verified mappings; they do not themselves constitute privacy acceptance.
- The existing plan already demonstrates the useful footer, Today and terminal behavior, so it is preserved. Its accessibility names, routes, appearance application, bootstrap behavior and resulting images require verification during explicit capture; none was executed or visually verified here.
