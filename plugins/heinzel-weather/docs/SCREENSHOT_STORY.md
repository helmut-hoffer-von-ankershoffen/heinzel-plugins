## Audience

Someone deciding whether to add weather to their everyday Heinzelmännchen workspace, and whether the same forecast is useful from the command line.

## Outcome

Show how a glance at Today answers “What is it like now and what is coming?”, then reveal the extra detail available on hover and the forecast available in a terminal. The existing plan already covers these behaviors, so it is preserved.

## Scenes

1. **Today weather:** The fictional Berlin forecast alongside the Today graphic and coming days.
2. **Weather detail:** Hover over the footer status for conditions and feels-like detail, with a focused crop.
3. **Phone weather:** The same Today experience at a phone-sized viewport.
4. **CLI weather:** `hz weather show` presents current conditions and the hourly outlook.
5. **CLI forecast:** `hz weather forecast --days 3` presents a concise multi-day outlook.

## Fictional fixtures

The existing `docs/screenshot_fixture.py` starts the plugin’s local fake OpenWeather service during capture and configures a fictional Berlin profile with metric units. Its canned forecast is clear at 21.5 °C now, with rain in the following hours and a fictional thunderstorm warning. The server anchors its data to the capture hour; `browser_time` controls only the browser clock.

## Privacy pitfalls

Capture only the isolated fictional profile, with no connected accounts or real locations. Do not expose real credentials, request URLs, personal notifications, or unrelated workspace content. The fixture key is explicitly fake. Preserve visible provider attribution and label the forecast as fictional; do not present the simulated warning as a real alert.

## Acceptance criteria

- The Today view shows recognizable current weather and upcoming days, and the detail view shows the status item’s additional information.
- The phone view remains legible and useful without clipping the weather content.
- Both CLI scenes show completed, readable results for their stated commands, with attribution where returned.
- Every caption identifies the data as fictional; no screenshot implies a live forecast or real warning.
- Review the captures for privacy, attribution, layout, and actual displayed values. The plan has been inspected for the requested structure but has not been executed or capture-validated.
