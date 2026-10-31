# Show when the team can work together

The gallery should make someone want to install Clock to answer “Who is at work, and when can I reach them?”
Show its persistent clocks and a useful expanded view. A settings form or an installed-plugin card is supporting
documentation, not a feature screenshot.

## Demonstration profile

Use Berlin, New York and Los Angeles, in that order, each working 09:00–18:00. Berlin is primary. Set the demonstration
moment to Monday **2026-10-26 15:30 UTC** in both the plugin and browser: Berlin 16:30, New York 11:30 and Los Angeles
08:30. The Today card must consequently show **2/3**, with two working zones and Los Angeles starting in 30 minutes.
These are fictional team locations, not a representation of the operator's team.

The public setup and verification commands are:

```sh
hz system config set clock.zones '[{"name":"Europe/Berlin","hours":[9,18]},{"name":"America/New_York","hours":[9,18]},{"name":"America/Los_Angeles","hours":[9,18]}]'
hz system ui show clock:zones-ticker --slot sidebar
hz system ui show clock:primary-zone --slot footer
hz clock --at 2026-10-26T15:30:00Z
```

`clock --at` fixes only that CLI result. UI capture must also align the source operation, its detail calculations and
browser `Date`; `tests/browser/mobile.mjs` demonstrates Playwright's `page.clock.install`. A capture fixture can
control this plugin's `datetime` references before invoking the installed `hz` entry point. Never change runtime
clock behavior to make a screenshot. Explicitly enable the sidebar ticker: its declared default slot is not enabled.

## Scenes to publish

| Scene | Action and visible proof | Caption |
| --- | --- | --- |
| `team-overview` | At `/`, keep the expanded left sidebar, its city ticker, the footer's primary clock and Today’s **Zones at work now: 2/3** visible together. No settings dialog. | “See your team's working hours at a glance, with live clocks in the sidebar and footer.” |
| `world-clock` | Open `/?panel=clock:world-clock` or the **World clock** action. Wait for region **World clock** and a painted map. Keep Today, the left ticker, primary footer clock and right workspace pane in frame. The pane shows all three city names, times, **Primary**, working-state indicators and countdowns. | “Find overlap across Berlin, New York and Los Angeles without leaving Today.” |
| `footer-detail` | From `/`, click the footer button whose accessible name starts with **Berlin**, then wait for its detail region. Show all three cities, primary designation, clocks and workday information above the still-visible footer trigger. | “Inspect every configured time zone from the compact footer clock.” |
| `phone-world-clock` | At 390×844, use the **World clock** action. The panel follows Today in the shared scroll area. Enable no reduced-motion preference and wait for an actually painted WebGL globe. Bring the World clock region into view without clicking a city; all three clocks, Berlin’s Primary badge and working-state labels must remain visible. Move away from city links before saving so hover styling is not mistaken for state. | “Check the team's local times on your phone.” |
| `cli-times` | Execute `hz clock --at 2026-10-26T15:30:00Z` and capture the actual table. Columns must include zone, time, working hours and working state; Berlin is primary, with `yes`, `yes`, `no`. | “The same team time zones and working hours in the CLI.” |

The **World clock** region has accessible **Rotate globe left**, **Rotate globe right** and city-marker buttons;
**Edit time zones** is a settings shortcut. Use these names rather than coordinates or CSS selectors. A clock ticker
button has an accessible name starting `World clock: Berlin` and naming the remaining cities. Footer names contain
a ticking time, so match the city prefix within the footer landmark rather than hard-coding seconds.

## Acceptance and privacy

The capture controller currently requests reduced motion, which makes the plugin display its static map. To call
an image a **globe**, capture with no reduced-motion preference and wait for an actually painted WebGL frame, as in
`tests/browser/globe.mjs`; a blank canvas is a failure. A static-map capture is valid only with a matching caption.
Ticker scrolling, live ticking, hover pause and reduced-motion behavior need the existing browser checks; a still
image does not prove animation. Check Chromium and WebKit phone layouts without claiming physical iPhone coverage.

Stage drafts privately. An agent must inspect every full-size image and transcript for clipped city rows, empty
panes, loading states, mismatched times and private data before publishing. Only fictional profile identity, the
three declared cities and demonstration time may appear. Remove unrelated profile/setup prompts by completing the
isolated profile; do not conceal a real Clock failure or present unrelated health warnings as a feature.

## Phone presentation correction

The phone scene intentionally uses the real WebGL globe, not the valid reduced-motion flat-map fallback. Its painted-frame wait is mandatory. A city is not selected just to position the viewport; a neutral region hover can bring the pane into view without leaving a city underline. The yellow sun is the renderer’s light source, not a fourth configured city; do not describe it as a city. Los Angeles at 08:30 remains outside the configured 09:00–18:00 hours, so its off-duty indication is correct. This capture change does not change those runtime semantics.

The Today widget becoming ready does not prove lazy sidebar/footer contributions have mounted. The team-overview scene must wait for the actual `World clock: Berlin…` ticker and footer `Berlin…` buttons before capture, then place the pointer over the neutral Today heading. Keep the chat collapsed so all three Clock surfaces remain the subject.
