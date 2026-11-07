## Audience

Someone deciding whether Weather makes the Heinzelmännchen app more useful for a quick daily check, while still offering a detailed forecast and command-line access.

## Outcome

Show a fictional Berlin day at a glance, invite the viewer to inspect the weather behind it, and demonstrate the same local forecast in the real CLI. The warning is fictional fixture data, not a live safety alert.

## Scenes

1. **Today weather:** The light Today view combines the current temperature, weather-dressed character and coming days. This is the quick answer before leaving home.
2. **Weather detail:** Hover the footer weather item to inspect the place, feels-like temperature and rain chance. This is a different interaction and detail state, not a second caption on the same capture.
3. **Weather page:** The actual Weather panel shows current conditions, the hourly outlook and the fixture warning. Its daily forecast and provider information are part of the same view; capture only what is genuinely visible.
4. **Phone weather:** The dark, phone-sized Today view demonstrates a different viewport and applied appearance. Keep it only if the resulting capture is visibly useful and distinct from scene 1.
5. **CLI weather:** `hz weather show` presents the current report, hours, days and warning in the native terminal.
6. **CLI forecast:** `hz weather forecast --days 3` demonstrates a shorter, parameterized daily outlook in the native terminal.

## Fictional fixtures

`docs/screenshot_fixture.py` is the existing capture bootstrap. It starts the plugin's local fake, selects OpenWeather, sets fictional Berlin and metric units, and supplies a fake key. `src/heinzel_weather/fake.py` specifies clear weather at 21.5 °C, rain beginning in the next hour, cooling, and an example thunderstorm warning. Its server data is anchored to the actual capture hour; `browser_time` fixes only the browser clock. Review timestamps for coherence rather than claiming the server forecast is fixed to the browser date. This fixture demonstrates the OpenWeather path; the normal default is keyless Open-Meteo, which does not provide severe alerts (`README.md`, `src/heinzel_weather/_models.py`).

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited to these verified mappings: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail. Independent review must inspect every image and transcript for identities, credentials, paths, location leakage and other sensitive data before publication. The fixture key is fake; do not expose real credentials. Doctor dismissals in the plan are optional and must not be represented as a healthy Doctor result.

## Acceptance criteria

- Capture genuine app and CLI output using the existing local bootstrap; do not fabricate HTML or present terminal output as feature UI. Retain at least two useful, distinct feature UI scenes and a useful CLI result.
- Confirm the light and dark appearances are actually applied, the phone layout is legible, and each scene shows the behavior its caption claims. Reject duplicate captures, caption-only differences, loading or error states, clipped essential content, and invisible or unverified warnings.
- Verify the footer hover opens the actual detail and that the focused region contains useful weather information. Confirm the panel route resolves to the real Weather view and the hourly heading appears. If Core's accessibility names or layout differ, revise the plan against observed UI rather than inventing selectors or screens.
- Confirm both CLI commands finish successfully and show their distinct reports, attribution and fictional location; do not use exact waits for individual table cells.
- Keep provider attribution where the actual UI or CLI supplies it. Do not imply Open-Meteo supplies the fixture's warning, or that a candidate weather change proves notice delivery.
- Independently inspect every final image and transcript and reject unknown identities or unapproved sensitive content. No capture, runtime behavior, privacy outcome or automated validation has been observed in this read-only review; the TOML was checked structurally against the requested schema without executing code.

## Source-bound UI surface inventory

- **Entrypoint:** `pyproject.toml`, `[project.entry-points."heinzel.modules"]`, declares `weather = "heinzel_weather"`. Its actual module is defined in `src/heinzel_weather/_module.py` and registered in `src/heinzel_weather/__init__.py`.
- **Plugin feature view:** `src/heinzel_weather/__init__.py` declares `module.nav` with sidebar `/?panel=weather:forecast` and `module.view(... name="forecast", source="page", abi=1)`. `web/src/index.ts` returns `WeatherPage`; `web/src/WeatherPage.tsx` renders the ready, needs-location, unavailable, stale and guessed states, alerts, current conditions, hourly and daily forecasts, attribution and a settings shortcut. `src/heinzel_weather/views/index.js` is the packaged view. The plan uses the declared route, not a route inferred from the plugin name.
- **Core-rendered feature UI:** `current_weather` is a `module.status` contribution to footer and sidebar; `today_weather` and `forecast_today` are `module.widget` contributions. Their source operation `ui` supplies a shared observation (`src/heinzel_weather/__init__.py`). The status detail and its Change place action are real contributions. The README claims attribution in status detail and Today, but the inspected contribution builders do not explicitly add an attribution line; whether Core adds it is unresolved and must be checked in captures.
- **Generic Core surfaces:** `module.settings(WeatherSettings)`, `module.nav(... settings=NavSettings(...))`, `module.setup`, `module.health`, and the credential declaration support settings, setup and Doctor surfaces; `ready` checks configuration and credentials without contacting the provider (`src/heinzel_weather/__init__.py`, `src/heinzel_weather/_module.py`, `src/heinzel_weather/_models.py`). Operations `ui`, `page`, `observe`, `weather`, `show`, `forecast`, `signals`, `conditions` and `info` are declared in `src/heinzel_weather/__init__.py`; Core may render operation-related surfaces, but their exact appearance is not established by the supplied plugin source. `watch` can contribute notices through Core notifications. No plugin channel or approval declaration was found; the packaged `weather-trend` skill and `docs/adr/0002-weather-observations-and-trend-advice.md` describe possible reviewed workflow proposals, not an implemented plugin approval screen or proof of delivery.
- **CLI and other interfaces:** `weather`, `show`, `forecast` and `conditions` have declared renderers, and the README documents CLI, MCP and REST interfaces. The planned CLI scenes are genuine terminal results, not substitutes for the existing feature UI. Exact Core-rendered operation, setup, Doctor and notification layouts are not established by these sources.
- **External provider UI:** Open-Meteo and OpenWeather are external data providers; the README describes an OpenWeather subscription and key, but declares no external provider screen to capture. The fixture is a local fake, not either provider's live interface.
