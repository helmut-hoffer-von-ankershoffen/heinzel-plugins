## Audience

Someone deciding whether the standard Heinzelmännchen appearance suits their everyday work and whether its optional soundscapes are useful to them.

## Outcome

Show the theme applied to a real working view in both appearances, then show the available soundscapes and how to discover both themes and sounds from the CLI. The plugin is included in the standard app; the gallery should not imply it must be installed separately.

## Scenes

1. **Warm light:** The fictional Launch review contract shows the light palette on a useful contract view, including its configuration and run commands.
2. **Comfortable dark:** The same contract in dark appearance makes the palette comparison direct.
3. **Optional soundscapes:** Appearance settings show Claude FM, Die Heinzelmännchen and Hyper Focus without starting playback.
4. **Themes in the CLI:** List available themes in the demo profile and identify Heinzelmännchen.
5. **Sounds in the CLI:** List the available soundscapes without starting playback.

## Fictional fixtures

The existing `docs/screenshot_fixture.py` creates an isolated Launch review contract with fictional owners and readiness checks. It explicitly says no report has been generated. Use the existing bootstrap and temporary demo profile; do not substitute real contracts or connected accounts.

## Privacy pitfalls

Keep personal names, paths, credentials, account details and real work out of captures. The soundscapes use YouTube; the source says nothing from YouTube loads until Play is pressed. Leave playback stopped and do not imply that a screenshot demonstrates audio playback.

## Acceptance criteria

- Both contract views visibly apply Heinzelmännchen, with light and dark appearances and the fictional Launch review heading visible.
- The soundscape view shows all three named options without suggesting playback has started.
- Both CLI captures show completed, useful list results from the demo profile.
- Captions identify fictional or demo content and do not claim a report was generated.
- Review the captures for legibility and accidental private data. The plan below preserves the existing scenes and was checked against the supplied format constraints by inspection; no capture or executable validation was run.
