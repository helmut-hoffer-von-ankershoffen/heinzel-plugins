## Audience
A distributed team deciding whether a shared world clock will make it easier to find a respectful time to work together.

## Outcome
Show how the clock makes working-hour overlap visible in the app and how `hz clock --at` can preview another moment. The existing plan already covers these behaviors, so it is preserved.

## Scenes
1. **World clock:** Open the globe alongside Today and see the fictional team’s three zones and current overlap.
2. **Team overview:** See the 2/3 working-now metric, sidebar ticker, and primary footer clock in the context of everyday work.
3. **Footer detail:** Open the primary clock to inspect all configured zones and their workday countdowns.
4. **Phone view:** See the globe and team clocks at a narrow viewport.
5. **CLI result:** Show the zone, local time, working hours, and working status as a text table.
6. **Terminal, current demo time:** Show the 15:30 UTC case in the app’s native terminal: Berlin and New York are working; Los Angeles starts in 30 minutes.
7. **Terminal, overlap preview:** Show the 16:30 UTC case, when all three zones are within their configured working hours. The app’s own demo clock remains at 15:30 UTC.

## Fictional fixtures
The existing `docs/screenshot_fixture.py` configures Berlin, New York, and Los Angeles with 09:00–18:00 working hours and freezes the plugin’s source clock at 2026-10-26 15:30 UTC. The browser uses the same fixed time. Berlin is the primary zone. The second terminal command explicitly previews a later time.

## Privacy pitfalls
Capture only the isolated fictional profile; check the surrounding Today view, terminal, notifications, and browser chrome for real names, projects, paths, credentials, or connected-account data before publication. Do not present the fictional working hours as a real team’s schedule.

## Acceptance criteria
- The globe, Today metric, ticker, footer detail, and phone view are legible and use the fictional three-zone profile.
- At the fixed demo time, the app shows 2/3 zones at work and the footer detail shows Berlin’s 1h 30m countdown.
- The CLI table identifies the primary zone and displays local times, working hours, and working status. The two terminal captures show the distinct 15:30 and 16:30 UTC cases.
- Captions identify demo data or demonstration time; the later preview is distinguishable from the app’s fixed clock.
- The declared plugin route and existing fixture are used. Review actual captures for layout, WebGL rendering, and privacy before publishing. The plan was checked against the provided format and source by inspection; capture was not run.
