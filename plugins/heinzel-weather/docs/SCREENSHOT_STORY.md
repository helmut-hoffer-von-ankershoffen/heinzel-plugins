## Audience and outcome

For someone deciding whether Weather makes Heinzelmännchen more useful during their day: show the forecast at a glance, the detail behind it, and the same useful information at the command line. The gallery should make clear that the conditions and warning are examples, not a live forecast.

## Scenes

1. **Today, light:** the fictional Berlin forecast brings current conditions and the coming days into the ordinary Today view.
2. **Footer detail:** hover the genuine weather status to inspect the fictional place, feels-like temperature and rain chance. This is a close-up of a different interaction, not a duplicate of Today.
3. **Weather page, light:** the actual forecast panel presents current conditions, the hourly outlook and the fictional thunderstorm warning.
4. **Today, dark on a phone-sized viewport:** show the fictional forecast in an applied dark appearance at 390 × 844. Keep this only if the captured layout reveals useful weather content and is meaningfully different from scene 1.
5. **CLI report:** `hz weather show` presents the fictional current conditions, hours, days and warning in the native CLI.
6. **CLI forecast:** `hz weather forecast --days 3` demonstrates the concise, parameterized fictional outlook.

The existing plan already covers these useful behaviors, so it is retained. The light and dark scenes apply appearances; neither claims to demonstrate a separate plugin theme.

## Fictional fixtures

`docs/screenshot_fixture.py` starts the existing local fake, selects OpenWeather, sets fictional Berlin and metric units, and supplies a fixture-only key. `src/heinzel_weather/fake.py` defines clear weather at 21.5 °C, rain beginning the next hour, cooling, and an Example Weather Service thunderstorm warning. The fake anchors its data to the actual capture hour; `browser_time` controls the browser clock only. Therefore, check displayed times for coherence rather than implying that the fixed browser date also freezes the server. The separate `web/src/fixture.ts` describes a different overcast forecast and is not the bootstrap used by this plan.

## Privacy and presentation

Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail; an independent reviewer must inspect every image and transcript. Also inspect locations, usernames, paths, credentials, provider URLs, notifications, terminal history and incidental app content. Use the isolated fictional profile and fixture; never expose the fixture key or substitute fabricated HTML for a product capture.

## Source-bound UI surface inventory

- **Plugin entrypoint and configuration:** `pyproject.toml` declares `heinzel.modules` entrypoint `weather = "heinzel_weather"`. `src/heinzel_weather/_module.py` declares the Weather module and optional OpenWeather credential. `src/heinzel_weather/__init__.py` registers `WeatherSettings`, `WeatherService`, the packaged skill and the optional setup flow; the settings navigation is `/?settings=weather`. Setup, credential and health contributions can produce Core-rendered UI, but their exact presentation is not established by this source alone.
- **Genuine feature UI:** `src/heinzel_weather/__init__.py` declares sidebar navigation to `/?panel=weather:forecast` and `module.view(... name="forecast", source="page")`. `web/src/index.ts` returns `WeatherPage`; `web/src/WeatherPage.tsx` implements ready, needs-location, unavailable, stale and guessed states, attribution, alerts, current conditions, hours and days. The proposed page scene uses the declared panel route.
- **Core-rendered feature UI:** the same Python file declares `module.status` for footer and sidebar, plus graphic, chart and forecast-list `module.widget` contributions on Today. Their data and navigation effects are defined by `_weather_status`, `_weather_card`, `_temperature_chart` and `_forecast_card`. These are genuine UI even though Core renders them. The `watch` job can emit notices; a notice is not guaranteed by the screenshot bootstrap and is not claimed as captured.
- **Operations and generic surfaces:** `src/heinzel_weather/__init__.py` declares `ui`, `page`, `observe`, `weather`, `show`, `forecast`, `signals`, `conditions` and `info` operations, as well as health and setup. Core may expose generic operation, information or setup surfaces, but their exact app routes and presentation are not demonstrated in the provided source. `docs/adr/0002-weather-observations-and-trend-advice.md` assigns scheduling, grants and approval to the engine; no plugin-specific approval screen is established. No plugin channel or approval contribution is declared in the inspected module.
- **CLI and external provider:** `README.md` documents the CLI, MCP and REST entrypoints; `show` and `forecast` have explicit Rich renderers in `src/heinzel_weather/__init__.py`. Their CLI output is labeled as CLI, not feature UI. Open-Meteo and OpenWeather are external data providers; no provider website is part of this gallery.
- **Evidence differences:** `README.md` says the status detail includes what the character wears and provider credit, while `_weather_status` explicitly constructs description, place, feels-like, high/low and rain chance, plus conditional guessed/stale messages; it does not explicitly add accessories or attribution. Do not promise those items in the footer detail without observing them. The README describes the page as contributed as data, while the current declarations also register a custom view; both the actual view and Core-rendered widgets must be considered.

## Acceptance criteria

Capture genuine product surfaces with the existing bootstrap and native CLI. Show at least two useful feature UI scenes and one useful CLI result; this plan has four UI scenes and two CLI cases. Verify light and dark appearances are applied, the forecast and warning match the fictional fixture, attribution remains visible where the actual UI provides it, and labels do not imply live weather. Reject duplicate images, caption-only variations, terminal output presented as feature UI, forged HTML, clipped or unreadable content, and any image or transcript with an unknown identity. Independently review every resulting image and transcript before publication. The TOML below was checked against the requested field and action rules by inspection; no parser or capture was run because execution was prohibited.
