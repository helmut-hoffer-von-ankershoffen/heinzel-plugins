## Audience

Someone deciding whether the standard Heinzelmännchen theme makes the app a more inviting place to work, and whether its optional soundscapes fit their routine.

## Outcome

Show the theme applied to a useful piece of work in both appearances, then reveal the optional listening choices and their command-line discovery. The story should make clear that the contract is fictional and that browsing soundscapes does not start playback.

## Scenes

1. **A warm place to plan — light.** Show the fictional Launch review contract in the applied light theme, including its configuration and run commands. The contract gives the palette a useful, readable context.
2. **The same work after dark.** Show the same contract in the applied dark theme. This is a meaningful appearance state of the same real view, not a caption-only variation.
3. **Choose a soundtrack.** Show the appearance settings with Claude FM, Die Heinzelmännchen, and Hyper Focus visible. Do not press Play; the screenshot demonstrates discovery, not successful playback.
4. **Find the theme from a terminal.** Show the genuine result of `hz system theme list` in the demo profile.
5. **Find the soundscapes from a terminal.** Show the genuine result of `hz system sound list` in the demo profile, without starting playback.

These are two useful applied feature UI states, an additional settings scene, and two CLI results. The existing plan already covers the useful behavior, so it is preserved.

## Fictional fixtures

`docs/screenshot_fixture.py` creates a local `launch-review` contract under the isolated state directory, sets `HZ_HEINZEL__USER_DIR`, and launches Heinzel. Its fictional owners are Mira, Jonas, and Priya; it explicitly says no report has been generated. Use this existing bootstrap only during explicit capture. `docs/SCREENSHOTS.md` describes a temporary fictional profile without connected accounts.

## Source-bound UI surface inventory

- `pyproject.toml` declares one `heinzel.modules` entry point, `theme = "heinzel_theme"`. Its catalog declares the five existing screenshot subjects.
- `src/heinzel_theme/__init__.py` constructs `Module("theme", ...)` and declares `module.theme(...)` and `module.soundscape(...)`. These are contributions to Core-rendered appearance and soundscape surfaces. The inspected plugin declares no Page, View, navigation panel, operation, channel, approval, setup, info, or footer contribution. That absence alone does not establish that a contribution is terminal-only.
- `src/heinzel_theme/themes/heinzelmaennchen.toml` declares the theme name, light and dark palettes, and logo paths. The supplied file inventory contains no files at those referenced logo paths, so actual logo rendering remains unresolved and must be checked during capture.
- The three files in `src/heinzel_theme/soundscapes/` declare YouTube streams; `focus.toml` pairs Die Heinzelmännchen with `heinzelmaennchen`. The YouTube player and content are external provider UI, distinct from Core's soundscape controls. Source comments say nothing from YouTube loads until Play; this plan does not test playback.
- `README.md` documents Settings → Appearance, theme selection, sound selection, and the soundscape pairing. `docs/screenshots.toml` supplies the existing contract-detail and appearance-settings routes; the supplied source does not independently declare those Core routes or verify their current rendering. Capture must confirm the routes and visible controls rather than substitute invented screens.
- The two CLI list commands are existing plan declarations, while the README explicitly documents `use` commands. Their actual output and availability remain to be verified at capture. CLI output is terminal output, not feature UI.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in a genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript. The fixture's fictional contract does not by itself establish that the surrounding app or terminal is free of personal information.

## Acceptance criteria

- Capture genuine Core-rendered views with the named theme visibly applied in both light and dark appearances; both contract scenes must show useful contract content, not duplicate images or caption-only changes.
- Confirm the soundscape scene shows the three declared choices without starting playback. Do not represent an external YouTube player as a plugin-owned screen or claim playback succeeded.
- Capture genuine completed CLI results for both list commands in the demo profile. Do not present terminal output as feature UI, forge HTML, or invent screens or statuses.
- Confirm routes, controls, logo assets, and CLI results against the actual capture environment; resolve any mismatch before publication. Preserve the fictional contract's statement that no report was generated.
- Independently inspect every image and transcript for identifying information, applying only the stated verified mappings. Fail on unknown identities.
- The returned plan retains the existing five scenes and bootstrap. Its TOML structure has been checked by inspection only; no parser, plugin, fixture, or capture was executed because execution was prohibited.
