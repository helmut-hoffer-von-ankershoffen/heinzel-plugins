### Audience
A distributed team deciding whether World Clock will make it easier to find a good time to collaborate.

### Outcome
Show how a fictional team can see who is working now, inspect local working hours, and compare a later time before scheduling a conversation.

### Scenes
1. **World clock:** The globe and Today view show Berlin, New York and Los Angeles, with two of three zones at work at the fixed demonstration time.
2. **Team overview:** The sidebar ticker and primary footer clock keep local time visible while the user stays on Today.
3. **Footer detail:** Opening the primary clock reveals the configured zones and a workday countdown.
4. **Phone:** The same globe and team clocks fit a narrow viewport.
5. **CLI result:** `hz clock --at` reports the fictional team's times at 15:30 UTC.
6. **Terminal, current:** In the app terminal, inspect the 15:30 UTC case: two zones are within working hours and Los Angeles starts in 30 minutes.
7. **Terminal, overlap:** Compare 16:30 UTC, when all three zones are within their configured working hours. The app's own clock remains fixed at 15:30 UTC.

### Fictional fixtures
Use the existing `docs/screenshot_fixture.py`: Berlin, New York and Los Angeles each have 09:00–18:00 working hours, and the clock is fixed at 2026-10-26 15:30 UTC. The later CLI case is a preview, not a change to the app clock.

### Privacy pitfalls
Capture only the isolated fictional profile, with no connected accounts or real team information. Review the whole frame, including Today, sidebar, footer, terminal and any notifications, for personal data before publishing.

### Acceptance criteria
- The globe, sidebar, footer detail and phone view render actual plugin behavior; the globe is ready before capture.
- Captions identify the example as demonstration data, and the two terminal results visibly support the stated comparison.
- The CLI image is a real result, and the terminal scenes use the same operation with two useful times.
- No real account details or private content appear in any frame.
- The existing plan is preserved: it already covers these behaviors. Its TOML structure was reviewed against the supplied format; parsing and capture were not run because execution was excluded.
