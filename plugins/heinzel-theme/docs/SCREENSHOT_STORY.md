## Audience
People choosing an appearance for everyday Heinzelmännchen work, with optional background sound. This theme is already included in the standard app; the story should help viewers decide whether to use it.

## Outcome
Show how the applied light and dark palettes frame a real contract view, then introduce the three optional soundscapes. Finish with useful CLI listings. Preserve the existing five-scene plan: it already demonstrates these behaviors without inventing screens.

## Scenes
1. **A clear launch review, in light.** Show the fictional Launch review contract with its goal, readiness checklist and available configuration or run controls. The warm accent belongs to the applied theme; the checklist is sample content.
2. **The same work, after dark.** Keep the contract, viewport and framing identical so viewers can compare readability and contrast directly.
3. **Choose a soundtrack.** Use the existing Appearance settings view to show Claude FM, Die Heinzelmännchen and Hyper Focus. Leave playback stopped. The `focus` soundscape pairs with this theme when Follow my theme is enabled; this scene does not claim to demonstrate that transition.
4. **Find the theme from the CLI.** Capture the real result of `hz system theme list` in the demo profile. Describe availability only; do not promise palette details that the command may not print.
5. **Find the soundscapes from the CLI.** Capture `hz system sound list`, showing the available choices without starting playback.

## Fictional fixtures
Use the existing `docs/screenshot_fixture.py` only during explicit capture. It creates the Launch review contract in isolated state: Mira checks the export boundary, Jonas checks the API notes, and Priya reviews phone screenshots. These are fictional, unchecked tasks. The fixture explicitly says no report has been generated. No additional fixture files are needed.

## Privacy pitfalls
Capture with the documented temporary profile and no connected accounts. Keep personal contracts, account details and terminal history out of frame. Do not press Play: these soundscapes use YouTube, and the supplied definitions describe external loading as beginning only after Play. A still image cannot establish stream availability, audio quality or successful playback.

## Acceptance criteria
- Both contract scenes resolve `/contracts/launch-review` and show the Launch review heading with useful contract content.
- Heinzelmännchen is applied in both light and dark appearance, using matching framing at 1440 × 1000 with reduced motion.
- All three soundscape titles are visible in the Appearance scene, with playback stopped.
- Both CLI commands finish successfully and show genuine listings containing the relevant theme or soundscapes; no output is fabricated.
- Every caption identifies fictional or demo content and stays within 180 characters.
- Retain the five existing scene names and bootstrap. No invented routes, selectors, assets or fixtures are introduced.
- The TOML below was manually checked against the requested structure. Bootstrap execution, runtime capture and CLI results remain unverified.
