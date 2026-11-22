## Audience

Someone deciding whether the Heinzelmännchen theme will make their everyday workspace feel welcoming, and whether its optional soundscapes suit their workflow.

## Outcome

Show the actual theme applied to useful work in both light and dark appearances, then show the available soundscapes and their command-line discovery. The same contract in two appearances is an intentional comparison of genuinely different theme states, not a caption-only variation.

## Scenes

1. **A clear start, in light:** The real Core contract view displays the fictional Launch review and its readiness checks with the applied light palette.
2. **The same work, after dark:** The same genuine view and fictional contract show the applied dark palette. Keep the content and viewport comparable so the theme change is visible.
3. **Choose the atmosphere:** Core’s Appearance settings show the four contributed soundscapes in a demo profile, without starting playback.
4. **Find the theme:** The native CLI lists themes in the demo profile.
5. **Find the soundscapes:** The native CLI lists soundscapes in the demo profile without starting playback.

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap. It creates the local Launch review contract with fictional people Mira, Jonas and Priya, readiness checks, and no generated report. It points the isolated profile at that contract. The theme and soundscape definitions themselves remain genuine plugin contributions.

## Source-bound UI surface inventory

- `pyproject.toml`, `[project.entry-points."heinzel.modules"]`, declares the sole entrypoint, `theme = "heinzel_theme"`. Its actual module in `src/heinzel_theme/__init__.py` declares `module.theme(...)` and `module.soundscape(...)`. It declares no plugin Page, View, navigation, operation, channel, approval, setup, info or footer contribution. The absence of a Page or View does not make the feature terminal-only: Core renders the contributed theme and soundscapes.
- `src/heinzel_theme/themes/heinzelmaennchen.toml` declares the actual light and dark palettes and logo references. The existing `docs/screenshots.toml` identifies `/contracts/launch-review` as the Core-rendered contract surface used to demonstrate them; `docs/screenshot_fixture.py` supplies its local contract. The supplied plugin source does not independently declare this Core route, so capture must confirm it resolves to the real contract view.
- `README.md` identifies Core’s Settings → Appearance as the selection surface and describes the pairing and Play behavior. The existing plan uses `/?settings=appearance`; capture must confirm that this opens the genuine Core settings and exposes all four entries. The supplied files do not contain Core’s route or settings implementation.
- `src/heinzel_theme/soundscapes/claude-fm.toml`, `focus.toml`, `hyper-focus.toml` and `singularity.toml` declare four YouTube streams; `focus.toml` pairs Die Heinzelmännchen with the theme. YouTube playback is an external provider surface, not a plugin-owned screen, and is outside these captures. README and the declarations say playback starts only after Play.
- `README.md` documents `hz system theme use` and `hz system sound use`; the existing `docs/screenshots.toml` supplies the `list` discovery commands. Their rendered results are CLI evidence, not feature UI. The supplied source does not implement those Core commands, so capture must verify their real output.
- The existing plan and catalog captions describe only three soundscapes, while the README and four declarations include Singularity. The revised scene calls for all four; if the installed compatible Core does not display one, record that discrepancy rather than fabricating it. Core-version-dependent default behavior described in the README must not be inferred from a screenshot of the list.

## Privacy pitfalls

Capture only the isolated fictional profile and do not connect accounts or press Play. Normal presentation fictionalization is explicitly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript. Do not obscure other details by assumption.

## Acceptance criteria

- Capture the genuine Core contract view in both applied appearances, with the fictional contract readable and the visual difference apparent. Confirm both are useful views of actual work, not duplicated images or caption-only changes.
- Confirm the genuine Appearance surface shows the four declared soundscapes without playback or external provider UI. If an entry or route is unavailable, report the observed discrepancy instead of substituting a screen.
- Capture the two real CLI list results with useful output. Never present terminal output as feature UI or use forged HTML.
- Each caption identifies demo or fictional data. Review all images and transcripts independently for private or unknown identities and apply only the disclosed mappings. Verify the recorded SDK health status and all remaining Doctor detail are unchanged.
- Validate the plan with the actual capture tooling when execution is authorized. This proposed TOML was checked against the supplied field and action rules by inspection only; no code, imports, network calls, or capture were run.
