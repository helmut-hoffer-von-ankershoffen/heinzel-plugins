## Audience
People deciding whether to add weather to their Heinzelmännchen dashboard or use its forecasts from the command line.

## Outcome
Show how a quick glance answers “What is it like now, and what is coming?” before offering a closer look at conditions and a forecast suited to planning ahead.

## Scenes
1. **Today weather:** The Today view brings current conditions, the weather-dressed mascot, and the coming days together.
2. **Weather detail:** Hover over the footer status for the place, feels-like temperature, rain chance, and attribution.
3. **Phone weather:** See the same useful Today view at phone size.
4. **CLI weather:** `hz weather show` presents current conditions, hourly weather, days, and alerts.
5. **CLI forecast:** `hz weather forecast --days 3` narrows the outlook to three days.

## Fictional fixtures
The existing bootstrap serves the plugin’s fake OpenWeather data on localhost and configures fictional Berlin weather in metric units. It supplies clear weather now, rain in the next hour, cooling, and an example thunderstorm warning. This demonstrates the OpenWeather provider; the plugin also supports keyless Open-Meteo. The browser clock is fixed, while the fixture anchors weather timestamps to the actual capture hour, so apparent dates and times need review.

## Privacy pitfalls
Capture only the isolated fictional profile. Check for real locations, account details, credentials, request URLs, notifications, and unrelated terminal history before sharing. The fixture key is a dummy; neither real keys nor personal weather locations belong in images or manifests. Label the forecast and warning as fictional, and do not imply they are live advice.

## Acceptance criteria
- Each image visibly supports its caption, keeps the relevant weather legible, and identifies the data as fictional through its caption.
- Today and the hover detail show actual plugin contributions; the phone view remains readable without clipped essential content.
- Both CLI results complete and show useful weather output, including attribution where provided.
- The example warning is recognizable as fixture data, not a real alert. No personal data or secrets appear.
- Review the captures for date or time inconsistencies caused by the different browser and fixture clocks. The existing plan was reviewed statically; capture and runtime validation were not performed because execution was excluded.
