## Audience

Someone choosing an everyday appearance for Heinzelmännchen who wants to see the theme in real work, compare light and dark, and understand the optional soundscapes before installing.

## Outcome

Show the warm light palette and dark palette applied to the same useful contract, then show the three soundscape choices and the corresponding discovery commands. The contract is a fictional example; no launch review or report is claimed to have been completed.

## Scenes

1. **Light at work:** The fictional Launch review contract in the applied light theme, with its goal and readiness checks visible.
2. **Dark at work:** The same real contract view in the applied dark theme. This is a meaningful appearance comparison, not a duplicate with a different caption.
3. **Soundscape choices:** The Core Appearance settings surface lists Claude FM, Die Heinzelmännchen and Hyper Focus in the demo profile. Do not start playback.
4. **Theme discovery:** Native CLI output for `hz system theme list` identifies the available theme in the demo profile.
5. **Soundscape discovery:** Native CLI output for `hz system sound list` shows the available soundscapes without starting playback.

## Fictional fixtures

`docs/screenshot_fixture.py` creates a local `launch-review` contract in the isolated state directory and sets the user contract directory. Its people, readiness checks and project are fictional; it explicitly says no report has been generated. Use this existing bootstrap only during explicit capture. The theme and soundscape definitions themselves are real plugin data.

## Privacy pitfalls

Normal presentation fictionalization is explicitly permitted: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail; independent review must inspect every image and transcript. Use the temporary profile without connected accounts described in `docs/SCREENSHOTS.md`. Inspect paths, hostnames, account names and other identifying content, including any incidental terminal output. Do not press Play: the soundscape files describe external YouTube streams and state that YouTube loads only after Play.

## Acceptance criteria

- Capture genuine Core-rendered views with the declared theme actually applied in both light and dark; make the fictional contract content legible. The two appearance states must visibly differ.
- Show the three soundscape names in the real Appearance interface without playback or provider UI. Do not imply that audio was tested.
- Capture actual CLI results for both listed commands; preserve their real output and health information. Do not substitute terminal output for a feature UI.
- Reject duplicate captures, caption-only changes, fabricated HTML, invented screens and unknown identities. Independently review every image and transcript, including any approved presentation substitutions.
- Confirm the contract route, Appearance query route, accessible waits, theme application and visible results against the compatible Core at capture time. The supplied sources contain an existing plan, but no Core implementation or capture evidence proving these routes and controls. Review the generated contact sheet and manifest as described in `docs/SCREENSHOTS.md`.

## Source-bound UI surface inventory

- `pyproject.toml`, `[project.entry-points."heinzel.modules"]`: the sole declared plugin entrypoint is `theme = "heinzel_theme"`. `src/heinzel_theme/__init__.py` declares `Module("theme", ...)`, `module.theme(...)` and `module.soundscape(...)`. It declares no plugin Page, View, navigation, operation, channel, approval, setup, info or footer contribution. This absence alone does not establish that the plugin lacks UI: Core renders the declared appearance and soundscape choices.
- `src/heinzel_theme/themes/heinzelmaennchen.toml` declares the named theme, light and dark palettes, and logo paths. The supplied file inventory does not include the referenced logo files, so their availability and rendering remain unresolved.
- `src/heinzel_theme/soundscapes/claude-fm.toml`, `focus.toml` and `hyper-focus.toml` declare three YouTube streams; `focus.toml` pairs Die Heinzelmännchen with the theme. YouTube playback is external provider UI, not a plugin screen, and is outside these captures.
- `README.md` describes Core Settings → Appearance, theme selection, soundscape selection, pairing and CLI commands. `docs/screenshots.toml` supplies the existing `/contracts/launch-review` and `/?settings=appearance` capture routes; their actual Core declarations are not among the provided sources. The contract is Core feature UI and the Appearance screen is Core configuration UI. The two CLI list scenes are genuine terminal results, not evidence that these features are terminal-only.
- `pyproject.toml` catalog screenshot declarations and `README.md` describe the same five-scene gallery, but the referenced generated images are absent from the supplied inventory. Their captions and plan are intent, not proof that captures succeeded.
