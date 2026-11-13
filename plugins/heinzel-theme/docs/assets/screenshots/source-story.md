## Audience
People deciding whether the standard Heinzelmännchen appearance and its optional soundscapes fit their daily work.

## Outcome
Show the theme applied to a useful, fictional contract in both light and dark appearances, then show the available soundscapes and their command-line discovery. The same contract in both appearances makes the palette comparison meaningful; the soundscape view adds a different capability.

## Scenes
1. **theme-light:** The fictional Launch review contract in the applied light theme, with its configuration and run commands visible.
2. **theme-dark:** The same contract in the applied dark theme, enabling a direct comparison of legibility and character.
3. **theme-soundscapes:** The demo profile's appearance settings, showing Claude FM, Die Heinzelmännchen and Hyper Focus before playback.
4. **theme-cli:** List available themes and identify Heinzelmännchen in the CLI.
5. **soundscapes-cli:** List the three soundscapes in the CLI without starting playback.

## Fictional fixtures
Use the existing `docs/screenshot_fixture.py` bootstrap. It writes a fictional Launch review contract into the isolated `HZ_STATE_DIR` and supplies it as the user contract directory. Mira, Jonas and Priya, their checks, and the launch review are demonstration content; the fixture explicitly says no report has been generated. The gallery documentation describes a temporary fictional profile with no connected accounts (`docs/SCREENSHOTS.md`).

For normal presentation fictionalization, verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript.

## Privacy pitfalls
Inspect every capture and transcript for real names, hostnames, paths, tokens, connected accounts and other identifying details; do not assume the bootstrap or the two permitted mappings removes them. Do not start a soundscape during capture: the soundscape declarations say the streams use YouTube and that nothing from YouTube loads until Play. The provider's player is external UI, not a plugin screen. Preserve any actual health status and remaining Doctor details.

## Source-bound UI surface inventory
- `pyproject.toml` declares the sole `heinzel.modules` entrypoint, `theme = "heinzel_theme"`. Its catalog declares the five existing screenshot subjects. `src/heinzel_theme/__init__.py` actually registers `module.theme(Path(__file__).parent / "themes")` and `module.soundscape(Path(__file__).parent / "soundscapes")`; it declares no plugin page, navigation, operation, channel, approval, setup, info or footer contribution. That absence alone does not rule out Core-rendered UI.
- `src/heinzel_theme/themes/heinzelmaennchen.toml` declares the theme, light and dark palettes, priority and logo references. The actual feature UI is Core's applied theme across its interface. The contract detail route and heading are specified by `docs/screenshots.toml`, with content supplied by `docs/screenshot_fixture.py`; the provided sources do not include Core's route implementation, so capture must verify that the route and controls render as expected.
- `README.md` identifies Core's Settings → Appearance and describes theme selection, soundscape selection, pairing and playback. `docs/screenshots.toml` specifies `/?settings=appearance` and the three expected titles. These are Core-rendered feature controls, not a plugin-owned route; their implementation is not included in the provided sources. `src/heinzel_theme/soundscapes/focus.toml` declares the pairing, while all three soundscape TOMLs declare YouTube streams. Playback and provider UI are outside this capture plan.
- `README.md` documents theme and sound commands; `docs/screenshots.toml` supplies the two list commands. The provided sources do not establish that these features are terminal-only: the same features also have Core UI. The CLI scenes supplement the UI rather than substitute for it.
- The theme declares logo paths, but the referenced SVG files are absent from the provided file inventory. Verify their availability in the capture environment; do not manufacture artwork. The README and catalog describe the soundscape behavior and screenshot subjects, but Core implementation and actual generated images are not provided, so those claims and routes remain unverified by this read-only inspection.

## Acceptance criteria
- Capture genuine rendered Core UI with the declared theme applied in both light and dark, plus the distinct soundscape settings state and both useful CLI results. Confirm the contract shows useful content and that its two appearance captures visibly differ beyond captions.
- Confirm all three soundscape titles and the CLI results match actual output. Do not claim playback was tested or initiated. Reject duplicate captures, caption-only changes, terminal output presented as feature UI, and forged HTML.
- Independently inspect every image and transcript for privacy and truthful status details, applying only the expressly described verified mappings. Unknown identities fail review.
- Verify the route, accessible names, theme application, referenced artwork and capture results in the actual compatible Core environment. The existing plan is preserved; its TOML was inspected as text, but neither a parser nor capture was run under the no-code-execution constraint.
