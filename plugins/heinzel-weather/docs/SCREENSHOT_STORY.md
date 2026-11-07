## Audience

Someone deciding whether Weather will make a quick daily check useful in Heinzelmännchen, and whether they can also retrieve a forecast from a terminal.

## Outcome

Show a fictional Berlin forecast moving from a glance on Today to richer details and a dedicated forecast page. Follow it with real CLI renderings of current conditions and a three-day outlook. The story should make clear that the warning and weather are demo data, not a live forecast or a safety assurance.

## Scenes

1. **Today weather:** the graphic and forecast list make the current conditions and coming days easy to scan in light appearance.
2. **Weather detail:** hover over the genuine footer status for the place, feels-like temperature and rain chance; crop to the resulting detail.
3. **Weather page:** show the dedicated forecast with current conditions, hourly outlook and the fictional warning.
4. **Phone weather:** show the Today contribution at phone width with dark appearance applied.
5. **CLI weather:** show `hz weather show` with the fictional current conditions, hours and warning.
6. **CLI forecast:** show `hz weather forecast --days 3` as a shorter planning result.

The existing plan already covers these useful, distinct surfaces and is preserved below. The mobile scene is a responsive, dark presentation of Today; it should not be counted as a different feature. The detail scene must actually expose the hover detail, not merely repeat the Today image with a new caption.

## Fictional fixtures

`docs/screenshot_fixture.py` starts the existing local fake provider, selects OpenWeather, sets Berlin and metric units, and uses a fake key. `src/heinzel_weather/fake.py` supplies fixed weather relative to the capture hour, including an alert; the browser clock in the plan fixes browser presentation, while the fixture anchors server data to the capture hour. The warning is fictional. The fake OpenWeather setup does not demonstrate Open-Meteo's keyless behavior or imply that Open-Meteo supplies severe alerts (`README.md`; `src/heinzel_weather/_openmeteo.py`).

Normal presentation fictionalization is explicitly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail and independent review must inspect every image and transcript.

## Privacy pitfalls

Use the isolated fictional profile and fake key only. Inspect images and transcripts for real locations, account names, hostnames, paths, credentials and other identifying data, including incidental Core UI and Doctor details. Fail on unknown identities instead of guessing replacements. Preserve provider attribution and the genuine health status and remaining Doctor detail. Review must independently inspect every image and transcript; the mappings above are not privacy approval.

## Acceptance criteria

- Capture the actual app and CLI using the existing bootstrap, with no invented screens, forged HTML, or terminal output presented as feature UI. Captions identify demo data.
- Today and the forecast page each provide genuine useful feature UI; the hover detail must show its distinct state. Reject duplicate captures or caption-only differences.
- Light and dark appearances are applied in their respective captures, and the phone scene is legible at the planned viewport.
- The forecast page shows the actual fixture state, including its fictional warning where rendered; CLI output is complete and attributable. Do not imply notification delivery or a live safety guarantee.
- Review every image and transcript for privacy and truthful attribution. Capture and review outcomes remain unverified until actually performed.

## Source-bound UI surface inventory

- **Plugin entry point:** `pyproject.toml` declares `heinzel.modules` → `weather = "heinzel_weather"`. Its actual declarations are in `src/heinzel_weather/__init__.py` and `src/heinzel_weather/_module.py`.
- **Feature UI:** `module.nav` points the sidebar to `/?panel=weather:forecast`; `module.view(... name="forecast", source="page")` contributes the Weather page. `web/src/WeatherPage.tsx` renders conditions, hours, days, alerts, update time and attribution, including setup and unavailable states. The shipped view is `src/heinzel_weather/views/index.js`. The page is plugin UI hosted by Core, not an external provider website.
- **Core-rendered feature UI:** `module.status(... slots={"footer": True, "sidebar": True})` contributes current weather and its detail; `module.widget` declares the Today graphic and forecast list. Their values and navigation effects are defined by `_weather_status`, `_weather_card` and `_forecast_card` in `src/heinzel_weather/__init__.py`. Settings are contributed by `module.settings(WeatherSettings)` and `module.nav(... settings=NavSettings(...))`; setup and health are declared by `@module.setup` and `@module.health` there. Doctor is a genuine Core health surface, but its specific runtime contents are not established by these files.
- **Operations and other contributions:** `ui`, `page`, `observe`, `weather`, `show`, `forecast`, `signals`, `conditions` and `info` are declared operations in `src/heinzel_weather/__init__.py`; the README documents CLI, MCP and REST exposure. `watch` is a scheduled job and may record notices through Core notifications; the sources do not establish a captured notice or delivery. `module.skill` contributes `src/heinzel_weather/skills/weather-trend/SKILL.md`; its discussion of approval does not declare a plugin approval screen. No plugin channel or approval contribution is declared in the supplied module. Generic Core operation, setup, information or notification surfaces may exist, but their exact runtime presentation is unresolved by these plugin sources and must not be invented.
- **CLI and provider boundaries:** `show` and `forecast` have native Rich renderers in `src/heinzel_weather/__init__.py`; their terminal output is a CLI result, not a substitute for feature UI. Provider account/key websites are external surfaces, not plugin screens. The README's keyless default describes Open-Meteo, whereas the screenshot bootstrap deliberately uses a local fake OpenWeather provider. The README describes status detail as including what the character wears; the actual `_weather_status` detail lists conditions, feels-like, high/low and rain, plus attribution or a warning, while accessories appear in the Today contributions. The capture must follow the actual declaration.
