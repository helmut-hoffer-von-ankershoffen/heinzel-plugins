## Audience

Distributed teams deciding whether World Clock belongs in their Heinzelmännchen workspace. The README says it is included in the standard app.

## Outcome

Answer a small, useful question: “When do our three cities overlap?” See configured working hours beside Today, inspect the footer clock, and preview an hour ahead in the native terminal. Working hours indicate configured schedules, not detected attendance.

## Scenes

Preserve the existing five scenes and append two terminal cases to cover the single clock operation:

1. **world-clock** — The globe and city clocks explain the fictional team's current overlap without leaving Today. Daylight is approximate; markers represent time zones.
2. **team-overview** — Show the Today metric, sidebar ticker and primary footer clock together: useful context while doing other work.
3. **footer-detail** — Expand the compact clock to inspect all three zones and Berlin's remaining workday.
4. **phone-world-clock** — Keep the existing 390 × 844 view to demonstrate the globe and readable city list on a narrow screen.
5. **cli-times** — Preserve the standalone CLI table for the same fixed demonstration moment.
6. **terminal-current** — Run the clock operation in the app terminal at 15:30 UTC: Berlin and New York are within working hours; Los Angeles starts in 30 minutes.
7. **terminal-overlap** — Query 16:30 UTC with the same operation. All three zones are now within their configured hours. This previews another moment; it does not advance the app clock.

## Fictional fixtures

Use only the existing `docs/screenshot_fixture.py`, unchanged, during explicit capture in the documented temporary profile without connected accounts. It configures Europe/Berlin, America/New_York and America/Los_Angeles with 09–18 working hours, Berlin first, and enables the sidebar/footer contributions. It fixes the source clock at `2026-10-26T15:30:00Z`; `browser_time` fixes the browser to match. No fixture files or product screens are invented.

## Privacy pitfalls

Configured cities and hours can reveal team routines. Keep the fictional profile and inspect Today, chat, notifications and terminal prompts for personal information before publishing. The bootstrap sets clock data and contributions; it is not a general redaction tool. Do not imply person tracking, actual availability or precise astronomical daylight. Footer badges and work-state icons depend on host support; older hosts retain the primary designation as text.

## Acceptance criteria

- Seven scenes preserve the existing useful views and CLI capture, adding two parameter cases in the native terminal.
- At the fixed moment, clocks read approximately 16:30 in Berlin, 11:30 in New York and 08:30 in Los Angeles; Today shows 2/3. Berlin's footer detail says “Ends in 1h 30m”.
- The 16:30 UTC terminal query returns 17:30, 12:30 and 09:30 respectively, with all three Working values set to yes. The app remains frozen at its original moment.
- Desktop and phone captures show legible clocks and workday information. Globe captures wait for WebGL; the footer crop includes every configured zone.
- Every caption identifies demonstration data or time. No screenshot claims attendance or displays private host data.
- Manual static validation checks TOML structure, permitted fields/actions, seven unique lowercase names, captions under 180 characters, local routes, argument arrays and existing fixture references. No parser, imports, bootstrap, application, tests, network calls or captures were run; runtime capture validation remains outstanding.
