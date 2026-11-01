# Clear now. Bring an umbrella for later.

## Audience
People who want a quick weather check in Heinzelmännchen, with enough detail to plan an outing, plus command-line users who want hourly and daily forecasts.

## Outcome
Show how Weather connects current conditions, an umbrella accessory and the coming days. The product supports keyless Open-Meteo by default; these screenshots use the existing local fake OpenWeather provider. They demonstrate the interface, not live weather or keyless-provider setup.

## Scenes
Preserve the existing five-scene plan: it already demonstrates useful behavior without inventing a Weather page.

1. **today-weather — the glance:** Today shows fictional Berlin weather, approximately 22 °C, the character carrying an umbrella and the near forecast. Clear skies now and an 80% daily rain chance explain the umbrella.
2. **weather-detail — the decision:** Hover over the footer weather status to inspect feels-like temperature, today's range and rain chance. Preserve the existing focused detail capture.
3. **phone-weather — the pocket check:** Show Today at 390 × 844, with the same fictional conditions and coming days readable on a narrow screen.
4. **cli-weather — when will it change?** `hz weather show` renders current conditions, 12 hourly rows, five days and a fictional thunderstorm warning from Example Weather Service. The approaching rain makes the detailed report useful.
5. **cli-forecast — just the days:** `hz weather forecast --days 3` produces a compact three-day table, including today, with lows, highs, rain chances and sky conditions.

## Fictional fixtures
Use only the existing `docs/screenshot_fixture.py`, which serves `src/heinzel_weather/fake.py` on loopback during explicit capture. It configures Berlin, metric units, the OpenWeather adapter and a dummy key. Its canned weather includes 21.5 °C now, feels like 21 °C, rain from the next hour and cooling later. Dates and warning windows follow the server's current hour; they are not frozen historical observations. No additional fixture files are needed.

## Privacy pitfalls
Use the documented temporary fictional profile without connected accounts or real credentials. The bootstrap overrides weather settings but does not itself isolate the entire app. Check Today, sidebar, footer and terminal output for personal names, places, paths or unrelated notices. Keep provider attribution visible and label every image as fictional. The example warning does not demonstrate notice delivery; Open-Meteo does not provide severe-weather alerts.

## Acceptance criteria
- Keep all five existing scenes, routes, captions, commands and interaction targets.
- Today shows matching temperature, umbrella accessory, forecast and provider attribution; the phone view remains readable.
- The detail capture actually includes the hovered status details, with feels-like temperature, daily range and rain chance visible.
- CLI captures show successful rendered results: the detailed report and exactly three forecast days respectively.
- Every caption identifies demo data and stays within 180 characters.
- Use only the existing local bootstrap and supported semantic steps; no external provider requests or invented screens are needed.
- The returned TOML was checked by inspection against the supplied format-1 rules. No imports, fixture execution, captures or runtime locator validation were performed.
