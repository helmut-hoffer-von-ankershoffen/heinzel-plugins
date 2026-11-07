## Audience

Someone deciding whether Weather gives them a useful at-a-glance forecast in Heinzelmännchen and a practical command-line option.

## Outcome

Show a fictional Berlin forecast progressing from a friendly Today overview to a detailed forecast and useful command output. The gallery should make clear that the warning and forecast are demonstration data, not live weather or a safety guarantee.

## Scenes

1. **Today weather:** The light Today view combines the current temperature and weather-dressed character with the coming days. This is a genuine Core-rendered feature surface contributed by `today_weather` and `forecast_today` in `src/heinzel_weather/__init__.py`.
2. **Weather detail:** Hover over the footer weather item to inspect the place, conditions, feels-like temperature and rain chance. This is a distinct interaction with the `current_weather` status contribution, not a duplicate caption on the Today capture.
3. **Weather page:** The actual `/?panel=weather:forecast` view shows current conditions, hourly and daily forecasts, and the fictional thunderstorm warning. Its route and `module.view` declaration are in `src/heinzel_weather/__init__.py`; rendering is in `web/src/WeatherPage.tsx`.
4. **Phone weather:** The dark, phone-sized Today view shows the same useful weather contributions in a materially different viewport and applied appearance.
5. **CLI weather:** `hz weather show` presents the fictional current conditions, hourly outlook, days and warning using the real report renderer.
6. **CLI forecast:** `hz weather forecast --days 3` provides a shorter, parameterized outlook using the real forecast renderer. Both CLI operations and renderers are declared in `src/heinzel_weather/__init__.py`.

## Fictional fixtures

`docs/screenshot_fixture.py` is the existing capture bootstrap. It starts the local fake from `src/heinzel_weather/fake.py`, selects OpenWeather, metric units and Berlin, and supplies a dummy key. The fake describes clear conditions at 21.5 °C, rain from the next hour and an example thunderstorm warning; its times are anchored to the capture hour. `browser_time` controls the browser clock, not the fake server clock. The separate `web/src/fixture.ts` describes an overcast Open-Meteo example and is not the bootstrap used by this plan. Do not imply that the fake warning comes from Open-Meteo: `README.md` says Open-Meteo supplies no severe alerts.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and an independent reviewer must inspect every image and transcript. Check for real locations, account identifiers, credentials, paths, hostnames, URLs and unrelated notifications; the fixture key is dummy data. Do not dismiss or alter a genuine health result to make a capture look successful.

## Acceptance criteria

- Capture the real application and native CLI using the existing bootstrap; no forged HTML, invented screens or terminal output presented as feature UI.
- Each scene visibly supports its caption, uses demo data, and is meaningfully distinct. Reject duplicates and caption-only changes.
- Confirm the light and dark appearances are actually applied, and the phone layout remains readable. Verify that the footer hover exposes genuine weather detail and that the forecast page shows its hourly heading and fictional warning.
- Preserve provider attribution where the actual surfaces render it. Review every image and transcript independently for privacy and factual accuracy before publication.
- The existing plan already covers the useful behavior, so it is preserved below. Its TOML structure was checked by inspection only: the requested prohibition on code execution prevents parser validation or capture verification in this turn.

## Source-bound UI surface inventory

- **Entry point and plugin view:** `pyproject.toml` declares the sole `heinzel.modules` entry point, `weather = "heinzel_weather"`. `src/heinzel_weather/__init__.py` declares settings, service, skill, the `weather` navigation item, the `forecast` view sourced from `page`, and route `/?panel=weather:forecast`. `web/src/index.ts` supplies the SDK ABI 1 view and `web/src/WeatherPage.tsx` implements ready, missing-location, unavailable and stale states, attribution, settings shortcut, forecast and alerts. `src/heinzel_weather/views/index.js` is the declared packaged view asset; actual browser rendering has not been verified here.
- **Core-rendered feature UI:** The same Python module declares `current_weather` for footer and sidebar, plus `today_weather` and `forecast_today` widgets. Their status detail, navigation action, graphic and list are constructed by `_weather_status`, `_weather_card` and `_forecast_card`. The settings navigation is `/?settings=weather`. `README.md` describes the page, status, Today and notices. The source declarations establish contributions; the supplied sources do not establish every Core layout or interaction at runtime.
- **Operations and generic surfaces:** `src/heinzel_weather/__init__.py` declares `ui`, `page`, `observe`, `weather`, `show`, `forecast`, `signals`, `conditions` and `info`; `README.md` documents corresponding CLI, MCP and REST uses where applicable. Operations may also be exposed by generic Core UI; the supplied plugin source does not establish a particular generic operation screen or route, so none is invented. The two planned CLI scenes are real CLI results, not substitutes for feature UI.
- **Setup, health, notices and approvals:** `module.setup`, `module.health`, `module.job` and `module.credential` declare setup, Doctor checks, the watch job and an optional provider credential. Their Core-rendered settings, health or notification surfaces may exist, but exact presentation is not established by these files. No channel or approval contribution is declared in the inspected plugin module. `docs/adr/0002-weather-observations-and-trend-advice.md` describes grants and approval as separate engine responsibilities, not an installed plugin approval screen. The checked `weather-trend` skill is advice, not evidence of delivery or approval.
- **External provider UI:** Open-Meteo and OpenWeather are data providers; subscription and API-key management belong to the external provider, not a plugin screen. The forecast view's source link is an external link, while its attribution control is plugin UI.
- **Evidence tension:** `README.md` says the footer detail includes what the character wears, but `_weather_status` constructs place, feels-like, daily range and rain chance, plus conditional guessed/stale messages; accessories are instead used by the Today graphic and forecast list. Do not claim the footer detail displays clothing without runtime evidence.
