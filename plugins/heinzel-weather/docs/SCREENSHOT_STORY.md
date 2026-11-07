## Audience and outcome

For someone deciding whether Weather makes Heinzelmännchen useful at a glance: show a fictional clear Berlin morning, the rain approaching, and the fuller forecast available when they want to investigate. The gallery also shows the real CLI’s concise and detailed outputs.

## Scenes

1. **Today, light:** the weather graphic and near forecast put current conditions beside the character. `src/heinzel_weather/__init__.py` declares the `weather-today`, `temperature-today`, and `forecast-today` widgets.
2. **Footer detail:** hover over the real weather status to see the place, feels-like temperature and rain chance. The `weather-now` status declares footer and sidebar slots and a detail action in `src/heinzel_weather/__init__.py`.
3. **Weather page, light:** show the actual forecast panel, including the fictional warning and hourly outlook. The `forecast` view and `/?panel=weather:forecast` navigation are declared in `src/heinzel_weather/__init__.py`; `web/src/WeatherPage.tsx` renders the forecast and alerts.
4. **Today, dark and phone-sized:** show the same useful weather contribution in a compact applied dark view. This is a responsive and theme comparison, not a claim of another feature.
5. **CLI report:** `hz weather show` renders current conditions, alerts, hours and days.
6. **CLI outlook:** `hz weather forecast --days 3` demonstrates a shorter parameterized forecast. Both operations and renderers are declared in `src/heinzel_weather/__init__.py`.

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap, which selects a local fake OpenWeather provider, fictional Berlin, metric units and a dummy key. `src/heinzel_weather/fake.py` supplies clear weather, approaching rain and a fictional thunderstorm warning from Example Weather Service. The fake anchors server data to the actual capture hour; `browser_time` controls the browser clock, so reviewers must check displayed times and freshness rather than assume the two clocks are synchronized. The fixture illustrates OpenWeather behavior; it does not demonstrate the default Open-Meteo provider, which the README says has no severe alerts.

## Source-bound UI surface inventory

- **Plugin feature UI:** `pyproject.toml` declares the sole `heinzel.modules` entry point, `weather = heinzel_weather`. `src/heinzel_weather/__init__.py` registers the forecast view, its sidebar route, the footer/sidebar status and three Today widgets. `web/src/WeatherPage.tsx` implements ready, missing-location, unavailable and stale presentations, attribution and a settings shortcut. The existing plan captures the ready view and contributed Today/status surfaces; it does not claim to capture every state.
- **Core-rendered contributions:** `module.settings(WeatherSettings)`, `module.setup`, `module.health`, `module.credential`, `module.nav`, the status and widgets are declared in `src/heinzel_weather/__init__.py` and `src/heinzel_weather/_module.py`. Setup and Doctor may appear through Core, but their precise Core rendering is not established by these provided sources. The `watch` job can create notices; no particular notice screen or delivery outcome is established. The operations `ui`, `page`, `observe`, `weather`, `show`, `forecast`, `signals`, `conditions`, and `info` are declared there; generic Core presentation of operations or info beyond the documented interfaces remains unverified. No plugin channel or approval contribution is declared. `docs/adr/0002-weather-observations-and-trend-advice.md` assigns grants and approval to the engine and does not establish a plugin approval screen.
- **External provider UI:** Open-Meteo and OpenWeather are data providers described in `README.md`; their websites and account flows are not plugin screens and are not part of this gallery.
- **Terminal and programmatic interfaces:** `README.md` documents CLI, MCP and REST operations. The two CLI scenes are real command outputs, not substitutes presented as feature UI. The packaged `weather-trend` skill is registered in `src/heinzel_weather/__init__.py`; its proposed workflow does not establish a separate UI.
- **Evidence to resolve:** the README mentions provider attribution in status detail, while the `DetailLine` construction in `src/heinzel_weather/__init__.py` contains condition, location, feels-like, range and rain chance but no explicit attribution line. Do not claim that detail shows attribution without observing it. The exact appearance of the generic Core surfaces and the footer hover target must be confirmed during capture.

## Privacy pitfalls

Use only the isolated fictional profile and dummy credential; inspect the entire frame and transcript for real locations, account identifiers, secrets, paths and hostnames. Normal presentation fictionalization is expressly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript.

## Acceptance criteria

- Capture genuine application surfaces and real CLI output using the existing bootstrap; no forged HTML, invented screens or terminal output labelled as feature UI.
- Verify the Today widgets, footer detail and forecast panel show useful distinct content; reject duplicates or caption-only changes. Confirm the warning is visibly fictional and the provider attribution is accurate.
- Confirm both light and dark appearances are actually applied, and the phone view remains legible. Check hover/focus targeting and any Doctor dismissal against the running app.
- Confirm both CLI commands complete with useful fictional results, including the requested three-day limit. Review all images and transcripts independently for privacy and unknown identities before publication.
- This plan is preserved from `docs/screenshots.toml`; its TOML structure and supplied field constraints were checked by inspection only. Capture behavior, Core routes and visual output have not been executed or verified in this read-only task.
