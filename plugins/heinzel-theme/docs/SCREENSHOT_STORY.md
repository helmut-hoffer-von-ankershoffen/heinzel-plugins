## Audience

Someone deciding whether the standard Heinzelmännchen appearance and its optional soundscapes suit their daily work.

## Outcome

Show the theme applied to a useful, fictional contract in both light and dark appearances, then show the available soundscapes and the CLI discovery commands. The same contract makes the two palettes easy to compare.

## Scenes

1. **Light:** A fictional Launch review contract shows the warm light palette in a working view.
2. **Dark:** The same contract shows the dark palette with the same content and layout.
3. **Soundscapes:** Appearance settings show Claude FM, Die Heinzelmännchen and Hyper Focus as optional choices.
4. **Themes CLI:** List available themes and identify Heinzelmännchen in a demo profile.
5. **Soundscapes CLI:** List the three soundscapes in a demo profile without starting playback.

## Fictional fixtures

The existing `docs/screenshot_fixture.py` creates a local Launch review contract with fictional owners and readiness checks in the isolated state directory. It explicitly says no report has been generated. Use the existing bootstrap during an explicit capture; do not create additional fixture files.

## Privacy pitfalls

Use the temporary demo profile without connected accounts. Inspect captures for real names, paths, tokens, account details and unrelated local state. Do not press Play: the soundscapes use YouTube streams, and playback is a separate action. Avoid suggesting that a report was generated or that audio was played.

## Acceptance criteria

- Both contract captures visibly apply Heinzelmännchen, one light and one dark, with the fictional Launch review legible.
- The soundscapes view shows all three named choices without implying playback.
- Both CLI captures show useful results from the stated commands in the demo profile.
- Captions identify fictional or demo content, and no capture exposes private data.
- The existing plan is retained: it already covers the useful behavior. The TOML below has been checked against the requested structure by inspection; capture and runtime behavior remain unverified because execution was prohibited.
