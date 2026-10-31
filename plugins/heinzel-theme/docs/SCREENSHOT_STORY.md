# A warm workspace, with sound on your terms

**Audience**
People choosing a comfortable appearance and optional background sound for Heinzelmännchen. The standard app already installs and enables this plugin automatically; these screenshots help people decide whether to use its appearance and soundscapes.

**Outcome**
Compare the cream and terracotta light palette with the forest and peach dark palette on the same useful contract view. Discover three optional soundscapes and see how to list available choices from the CLI.

**Scenes**
1. **theme-light:** The fictional Launch review makes the applied light theme tangible through readable contract content and a readiness checklist.
2. **theme-dark:** The identical contract in dark appearance makes the palette comparison easy and fair.
3. **theme-soundscapes:** Show Claude FM, Die Heinzelmännchen and Hyper Focus in the existing appearance settings. Explain that playback requires Play; Die Heinzelmännchen is paired with this theme when Follow my theme is enabled.
4. **theme-cli:** Show the actual theme list, helping viewers find the theme identifier without claiming this command displays palette details.
5. **soundscapes-cli:** Show the actual soundscape list without starting playback.

**Fictional fixtures**
Reuse the existing `docs/screenshot_fixture.py` during explicit capture only. It creates the Launch review contract beneath the isolated state directory, with fictional owners Mira, Jonas and Priya and three unchecked readiness items. The contract explicitly says no report has been generated. Do not add fixture files or execute the contract.

**Privacy pitfalls**
Capture only the temporary fictional profile without connected accounts. Keep personal paths, accounts and unrelated terminal history out of frame. Leave Play untouched: these soundscapes use YouTube, and the provided definitions describe player loading only after Play. A screenshot of the choices does not establish stream availability or successful playback.

**Acceptance criteria**
- Preserve the existing five scenes and bootstrap; add only a fixed browser time.
- Both contract scenes display the applied `heinzelmaennchen` theme in their specified light or dark appearance, with the same fictional content visible.
- The soundscape scene shows all three supplied choices without playback.
- Both CLI scenes contain completed, readable command results from the isolated profile, without invented output.
- Every caption identifies demo data or the demo profile and stays within 180 characters.
- Static validation covers TOML structure, unique lowercase scene names, local routes without fragments, supported steps, argument arrays and the existing relative bootstrap path. Runtime validation and captures were not performed.
