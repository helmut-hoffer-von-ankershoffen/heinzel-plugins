## Audience

Distributed teams considering a quick way to see colleagues’ local times and find working-hour overlap.

## Outcome

Show how World Clock makes a three-city team’s availability visible in the app and lets someone preview another moment from the terminal. The plugin is included in the standard app.

## Scenes

1. **World clock:** The globe and team clocks put Berlin, New York, and Los Angeles in context alongside Today’s 2/3 working indicator.
2. **Team overview:** The Today widget, sidebar ticker, and primary footer clock show how the information fits into the rest of the app.
3. **Footer detail:** Open the primary clock to inspect all configured zones and their workday countdowns.
4. **Phone view:** Show the globe and team clocks at a narrow viewport.
5. **CLI result:** Show the zone names, local times, working hours, and working status for the fixed moment.
6. **Terminal, current example:** At 15:30 UTC, Berlin and New York are working and Los Angeles starts in 30 minutes.
7. **Terminal, overlap preview:** At 16:30 UTC, all three zones are within working hours; the app clock remains at the fixture’s 15:30 UTC.

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py`: it sets Berlin, New York, and Los Angeles to 09:00–18:00 working hours, enables the sidebar and footer contributions, and fixes the plugin clock at 2026-10-26 15:30 UTC. The browser uses the same fixed time. These are example team settings, not real people or accounts.

## Privacy pitfalls

Capture only in the isolated fictional profile described in the screenshot documentation. Check the app, terminal, and surrounding chrome for real names, messages, paths, account details, or other unrelated data before publishing. Captions should retain the demonstration-data context.

## Acceptance criteria

- The globe, Today metric, sidebar ticker, footer detail, and phone view render as actual app views; the globe finishes loading.
- The fixed-time views show 2/3 zones working, and the footer detail shows Berlin’s 1h 30m countdown.
- Both terminal commands complete and show the expected change in working status without suggesting that `--at` changes the app clock.
- Captions identify the demonstration data, and no private information appears.
- Review the generated gallery before publication. The plan below preserves the existing seven scenes; its TOML structure was reviewed against the requested format, but capture and runtime validation were not performed.
