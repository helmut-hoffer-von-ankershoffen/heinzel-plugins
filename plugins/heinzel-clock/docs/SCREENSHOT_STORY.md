## Audience

A distributed team deciding whether World Clock will make it easier to see colleagues’ local times and working hours without leaving Heinzelmännchen. The plugin is included in the standard app.

## Outcome

A viewer can see the team’s current coverage, inspect individual workday countdowns, and compare a future moment using the command line.

## Scenes

1. **World clock:** Show the globe and three local clocks alongside Today’s 2/3 working-hours metric.
2. **Team overview:** Show the Today metric, sidebar ticker, and primary footer clock in their everyday context.
3. **Footer detail:** Open the primary clock to inspect all configured zones and their countdowns.
4. **Phone world clock:** Show the same globe and team clocks at a phone viewport.
5. **CLI times:** Show the table of zones, local times, working hours, and working status.
6. **Terminal current:** Run the operation in the app terminal at 15:30 UTC, when two zones are working.
7. **Terminal overlap:** Preview 16:30 UTC in the terminal, when all three zones are working, while the app clock remains fixed at 15:30 UTC.

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap and the fixed Monday, 26 October 2026 at 15:30 UTC. The fictional team uses Berlin, New York, and Los Angeles, each with local working hours of 09:00–18:00. Berlin is primary. At 15:30 UTC, Berlin and New York are working and Los Angeles starts in 30 minutes; at 16:30 UTC, all three are within working hours.

## Privacy pitfalls

Capture only in the temporary fictional profile described by the screenshot documentation. Check the whole app frame and terminal for real account names, messages, project data, machine paths, credentials, and other personal information before sharing. The fixture configures clock data and contributions; it does not by itself prove that every surrounding app surface is free of private data.

## Acceptance criteria

- The declared plugin route opens the real World Clock panel; the globe renders and the three demo zones are legible.
- Today shows 2/3 at the fixed moment, and the footer detail shows the configured zones and a Berlin countdown.
- The phone capture remains readable at 390 × 844.
- The CLI result shows all three zones, their local times, 09–18 working hours, and working status. The two native-terminal cases visibly demonstrate the change from two working zones to three.
- Captions identify the data or time as demonstration material. Inspect the resulting captures for privacy and visual accuracy.
- The plan has been checked against the supplied format and source declarations by inspection; capture and runtime behavior have not been executed or verified.
