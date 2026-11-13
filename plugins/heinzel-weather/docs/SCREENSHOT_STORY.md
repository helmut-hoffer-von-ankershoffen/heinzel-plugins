## Audience

Someone deciding whether Weather will make Heinzelmännchen useful for a quick daily check, a more detailed forecast, and a command-line workflow.

## Outcome

Show a fictional Berlin forecast progressing from a glance on Today to an explanatory footer detail, a full forecast and alert, and two useful CLI results. The forecast is demonstration data, not a live observation or a real warning.

## Scenes

1. **Today, light:** The current temperature, weather-aware character and near forecast make the plugin’s everyday value visible at a glance.
2. **Footer detail:** Hover over the real weather status to inspect the sky, feels-like temperature, daily range and rain chance. This is a meaningful detail state of the status contribution.
3. **Weather page, light:** See current conditions, the hourly outlook and the fictional thunderstorm warning in the actual plugin page.
4. **Today, dark, phone-sized:** See the weather in a compact layout with dark appearance applied. Review the actual capture to ensure it adds useful mobile evidence rather than duplicating scene 1.
5. **CLI report:** `hz weather show` presents current conditions, hours, days and the fictional alert.
6. **CLI forecast:** `hz weather forecast --days 3` demonstrates a concise, parameterized daily outlook.

## Fictional fixtures

`docs/screenshot_fixture.py` starts the existing local fake from `src/heinzel_weather/fake.py`, selects OpenWeather with a dummy key, metric units and Berlin. The fake supplies clear weather now, rain in the next hour and an example thunderstorm warning. Its server data is anchored to the capture hour; `browser_time` controls the browser clock only. This fixture demonstrates the OpenWeather-shaped path, not a live provider response. The default product provider is keyless Open-Meteo, which the README says does not provide severe alerts (`README.md`; `src/heinzel_weather/_module.py`).

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail; independent review must inspect every image and transcript for identities, paths, credentials, location leakage and other private information. Do not manufacture or alter a Doctor row. The fixture key is fictional, but screenshots and transcripts still require review.

## Acceptance criteria

- Capture the declared real application surfaces and actual CLI output with the existing fixture. Keep fictional data apparent in every caption; do not present the example warning as real.
- Verify light and dark appearances are actually applied, and that the phone scene is legible and materially useful. Reject duplicate captures, caption-only changes, terminal output presented as feature UI, and forged HTML.
- Confirm the footer detail is genuinely opened and the Weather page shows its forecast; verify the CLI commands finish and display their respective report and three-day results. Do not add brittle waits for individual table cells.
- Inspect every image and transcript independently for privacy and truthful health/status presentation. Unknown identities fail review. Verify the captures and TOML with the capture tooling during an authorized capture; this response has only been checked against the supplied source text, without execution.

## Source-bound UI surface inventory

- `pyproject.toml` declares the sole `heinzel.modules` entrypoint, `weather = "heinzel_weather"`. `src/heinzel_weather/__init__.py` declares `module.nav` with sidebar navigation to `/plugins/weather/forecast`, and `module.view` named `forecast`, source `page`, slot `page`, at that route. `web/src/index.ts` supplies the ABI-1 view and `web/src/WeatherPage.tsx` renders the actual forecast, alert, attribution and location controls. This is plugin feature UI, not external provider UI.
- The same module declares `current_weather` with footer and sidebar slots, plus `today_weather`, `temperature_today` and `forecast_today` widgets. These are Core-rendered feature surfaces fed by the `ui` operation. The footer’s detail and navigation are declared in `_weather_status`; Today’s graphic, chart and list are declared in `_weather_card`, `_temperature_chart` and `_forecast_card`.
- `module.settings(WeatherSettings)`, the navigation settings section and optional `module.setup` contribute configuration and setup surfaces; `module.health` contributes Doctor checks. `module.credential` in `src/heinzel_weather/_module.py` declares the optional OpenWeather credential. These are Core-mediated surfaces, not evidence of external provider screens. The `watch` job can emit notices through `Notifications`; the supplied declarations do not establish a specific notice route or guarantee a notice in this fixture.
- The `weather`, `show`, `forecast`, `conditions`, `signals`, `observe`, `info`, `ui` and `page` operations are declared in `src/heinzel_weather/__init__.py`. Their existence alone does not establish a dedicated screen for each. `show` and `forecast` have explicit Rich terminal renderers and are useful genuine CLI results; they are not substitutes for the feature UI. The README also documents MCP and REST exposure. No channel or approval contribution is declared in the inspected module.
- External Open-Meteo and OpenWeather services are data providers; no provider website is part of this capture. The source’s separate `web/src/fixture.ts` is a web development fixture with different overcast data; the existing capture bootstrap uses `src/heinzel_weather/fake.py` instead.
- The README describes a status detail including what the character wears, while the actual `_weather_status` detail declares sky, place, feels-like, daily range and rain chance; accessories appear in the Today contributions. Follow the declarations and inspect the rendered result. The source declares the relevant surfaces but cannot prove capture rendering or privacy acceptance without running and reviewing them.
