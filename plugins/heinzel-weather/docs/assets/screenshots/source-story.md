## Audience

Someone deciding whether Weather will make a quick daily check more useful in Heinzelmännchen, and whether its forecast is also convenient from a terminal.

## Outcome

Show a fictional Berlin day at a glance, then open the actual Weather view to see what is coming. Finish with two real CLI operations: a detailed report and a shorter three-day forecast. The warning and approaching rain are fixture data, not a live forecast or safety advice.

## Scenes

1. **Today, light:** The graphic and forecast list show the current conditions and coming days together, including the character’s weather accessory.
2. **Footer detail:** Hover over the real weather status to inspect the place, feels-like temperature and rain chance. Crop the actual detail region so it is legible.
3. **Weather page, light:** Show the contributed view with current conditions, hourly outlook and the fictional thunderstorm warning.
4. **Today, dark and phone-sized:** Show how the same useful forecast fits a small screen with dark appearance applied. This is a distinct responsive presentation, not a caption-only variant.
5. **CLI report:** Capture `hz weather show` with the fictional current conditions, hourly and daily tables, and warning.
6. **CLI forecast:** Capture `hz weather forecast --days 3` to show a concise, parameterized outlook.

Preserve the existing scene plan: it already covers useful feature UI, light and dark appearances, and two meaningful CLI results. Reject duplicate captures, caption-only differences, terminal output represented as feature UI, and forged HTML. If a scene cannot be captured as described, report the failure instead of substituting an invented screen.

## Fictional fixtures

`docs/screenshot_fixture.py` starts the existing local fake provider, selects OpenWeather, configures fictional Berlin and metric units, and supplies a fake key. `src/heinzel_weather/fake.py` defines 21.5 °C and clear conditions, rain beginning in the next hour, cooling and a fictional thunderstorm warning. Its data is anchored to the server’s current hour; `browser_time` fixes only the browser clock, so capture-time dates may differ. The fixture demonstrates OpenWeather, while the product defaults to keyless Open-Meteo; Open-Meteo does not provide severe alerts (`README.md`, `src/heinzel_weather/_openmeteo.py`). Do not imply the pictured warning comes from Open-Meteo or represents a real alert.

## Privacy pitfalls

Use the isolated fictional profile and existing bootstrap; do not expose real locations, accounts, keys, paths, hostnames or unrelated content. Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript. The provided plugin sources do not establish the actual interpreter path or Doctor hostname; verify ownership and the exact row before applying either mapping. The fixture key is fictional, but still inspect all output for other credentials and identifying data.

## Acceptance criteria

- Capture the real Core-rendered Today contributions and the actual `weather:forecast` view, plus both genuine CLI results. Show readable, meaningful differences between scenes, with applied light and dark appearances.
- Retain the fixture’s weather values, provider attribution where displayed, and health states without embellishment. Make fictional data clear in every caption.
- Verify the warning is visibly fictional in context, and do not describe it as a live alert. Preserve any stale or unavailable indication actually rendered; do not fabricate a ready state.
- Inspect every image and transcript independently for identities, secrets and unrelated private content. Apply only the expressly permitted, verified mappings; fail on unknown identities.
- Verify the footer hover target, detail region, panel route and mobile composition against the running application during explicit capture. The plan is source-reviewed but has not been executed or capture-validated here.

## Source-bound UI surface inventory

- **Plugin entrypoint:** `pyproject.toml`, `[project.entry-points."heinzel.modules"]`, declares `weather = "heinzel_weather"`. `src/heinzel_weather/_module.py` declares the module and optional OpenWeather credential.
- **Actual feature view:** `src/heinzel_weather/__init__.py` declares `module.nav(... sidebar=PAGE)` and `module.view(... name="forecast", source="page", abi=1)` with `PAGE = Navigate(path="/?panel=weather:forecast")`. `web/src/index.ts` supplies the ABI-1 view and `web/src/WeatherPage.tsx` implements its ready, needs-location, unavailable, stale and guessed states, forecast, warning, attribution and settings shortcut. `src/heinzel_weather/views/index.js` is the declared packaged view resource; its existence and runtime loading still need capture verification.
- **Core-rendered feature UI:** `current_weather` declares `module.status` for footer and sidebar; `today_weather` and `forecast_today` declare two `module.widget` contributions, all sourced from `ui` (`src/heinzel_weather/__init__.py`). These are real feature surfaces even though Core renders them. Status effects navigate to the forecast or settings.
- **Other generic Core surfaces and operations:** The same file declares settings, optional setup, health checks, the `watch` job, packaged skill, and operations `ui`, `page`, `observe`, `weather`, `show`, `forecast`, `signals`, `conditions` and `info`. Settings and Doctor can therefore produce Core UI; operation exposure may also produce generic Core surfaces, but their exact presentation is not established by these plugin files. `watch` may create notices when notifications are available; no notification delivery is demonstrated by this fixture plan. The source declares no plugin channel or approval contribution. `docs/adr/0002-weather-observations-and-trend-advice.md` explicitly separates observation and skill advice from grants, approvals and external writes.
- **Terminal and external surfaces:** `show` and `forecast` have actual Rich renderers in `src/heinzel_weather/__init__.py`; they are useful CLI results, not substitutes for feature UI. The README also documents CLI, MCP and REST access. Open-Meteo and OpenWeather are external data providers, not pictured provider interfaces; the fixture runs a local fake OpenWeather endpoint.
- **Unresolved evidence:** `README.md` says provider credit appears in the status detail and Today list and graphic, but `_weather_status`, `_weather_card` and `_forecast_card` do not explicitly add attribution. The page has an attribution control in `web/src/WeatherPage.tsx`; confirm any additional Core-provided credit during capture rather than claiming it from the README alone. README describes the page’s next 24 hours, while `show` declares the next 12 hours; these are different surfaces, and actual rendered fixture output should be checked.
