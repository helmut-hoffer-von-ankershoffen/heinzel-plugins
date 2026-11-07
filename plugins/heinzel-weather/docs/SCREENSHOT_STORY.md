## Audience

Someone deciding whether Weather will make Heinzelmännchen more useful for checking conditions at a glance, planning the next few hours, and consulting a forecast from the command line.

## Outcome

Show a coherent journey from the Today view to a closer look at the weather, then to the full forecast and useful CLI results. The existing six-scene plan already covers this journey, so it is preserved. Its light and dark appearances are applied to actual UI scenes; the dark scene also shows a phone-sized layout.

## Scenes

1. **Today, at a glance — light.** The fictional Berlin conditions appear with the weather graphic and near-term list, showing the everyday value without opening a separate tool.
2. **A closer look.** Hover the genuine footer weather item to reveal the place, feels-like temperature and rain chance. The focused detail is a different state of the real status contribution, not a replacement screen.
3. **The forecast page — light.** Open the declared Weather panel to see the current conditions, hourly outlook and fictional warning. The page also supports daily forecasts and attribution; actual visibility depends on the captured viewport.
4. **Today on a phone — dark.** Show the real Today contributions at a narrow viewport with dark appearance applied. This establishes a distinct responsive and appearance state, rather than merely changing a caption.
5. **Current report in the CLI.** `hz weather show` presents current conditions, alerts, hours and days from the same fictional provider data.
6. **A shorter CLI forecast.** `hz weather forecast --days 3` demonstrates the useful days parameter with a concise forecast.

## Fictional fixtures

`docs/screenshot_fixture.py` starts the existing loopback fake from `src/heinzel_weather/fake.py`, selects OpenWeather, sets Berlin and metric units, and uses a fixture-only key. The fake describes clear conditions at 21.5 °C, rain beginning in the next hour and an example thunderstorm warning. Its weather is anchored to the capture hour; `browser_time` fixes only the browser clock. Consequently, timestamps can differ from the browser clock and must be reviewed for coherence. This is an OpenWeather-shaped demonstration, not evidence of the default Open-Meteo provider or a live forecast. Open-Meteo has no severe alerts according to `README.md`.

`web/src/fixture.ts` contains a separate fictional, overcast Open-Meteo example; the planned capture bootstrap uses the Python fake instead. Do not substitute the web fixture or invent another fixture file.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript. Review locations, account names, paths, hostnames, credentials, logs and incidental app content; fixture configuration alone does not prove an image is safe. The plan optionally dismisses Doctor notices, but their absence also does not establish privacy.

## Acceptance criteria

- Capture genuine application and CLI output with the existing bootstrap during an explicit capture; do not forge HTML, substitute terminal output for feature UI, or use external provider pages as plugin UI.
- Confirm at least two useful feature UI scenes and a useful CLI result, with both light and dark appearances actually applied. Reject duplicates and caption-only changes.
- Verify the Today content, footer hover detail, forecast panel and each CLI result against the fictional data and their captions. Preserve attribution where rendered; do not imply that the warning is real or that it comes from Open-Meteo.
- Confirm the panel route and accessibility targets work in the installed app. If a target, warning, focus crop or responsive layout does not render as expected, record the discrepancy rather than fabricating it.
- Independently inspect every image and transcript for privacy, including any Doctor content, before publication. Apply only the disclosed mappings and reject unknown identities.
- The TOML below was checked against the supplied field and action rules by inspection; no parser, capture, plugin code, network call or source edit was run. Runtime validity and screenshot freshness remain unverified.

## Source-bound UI surface inventory

- **Entrypoint and declarations:** `pyproject.toml` declares the `heinzel.modules` entrypoint `weather = "heinzel_weather"`. `src/heinzel_weather/__init__.py` registers settings, service, skill, navigation, an ABI 1 view, operations, status, widgets, job, health and optional setup. `src/heinzel_weather/_module.py` declares the module and its OpenWeather credential.
- **Plugin feature view:** `module.nav(... sidebar=PAGE)` and `module.view(... name="forecast", source="page")` in `src/heinzel_weather/__init__.py` establish `/?panel=weather:forecast`; `web/src/index.ts` supplies the ABI 1 view and `web/src/WeatherPage.tsx` renders ready, needs-location, unavailable, stale and guessed states, alerts, hourly and daily forecasts. Settings navigation is `/?settings=weather`. The source references `web/src/style.css`, which is not present among the provided files; packaged view behavior and styling therefore require capture verification.
- **Core-rendered feature UI:** the `current_weather` status declaration contributes footer and sidebar items, detail and navigation; `today_weather` and `forecast_today` contribute graphic and list widgets on Today, all in `src/heinzel_weather/__init__.py`. These are real feature surfaces even though Core renders them. `watch` and `src/heinzel_weather/_watch.py` define candidate notices; a delivered notice is not established by the fixture or this plan.
- **Generic Core surfaces:** operations `ui`, `page`, `observe`, `weather`, `show`, `forecast`, `signals`, `conditions` and `info`, plus `ready`, `setup`, settings and the credential, may be exposed by Core through its generic interfaces. The provided plugin source does not establish specific generic app routes or rendered states for each, so none are invented here. `docs/adr/0002-weather-observations-and-trend-advice.md` explicitly leaves scheduling, grants, drafts and approval to the engine; it does not establish a plugin approval screen.
- **CLI and other interfaces:** the operation declarations and `README.md` describe CLI, MCP and REST access; the selected CLI captures are genuine command results, not feature UI. The packaged `weather-trend` skill is checked advice, not an independently established screen. Provider websites and subscription/key management are external provider UI, not plugin screens.
- **Evidence limits and contradictions:** `src/heinzel_weather/__init__.py` describes `show` as 12 hours and five days, whereas the page declaration and `web/src/WeatherPage.tsx` support up to 24 hours and seven days; these are distinct outputs, not interchangeable claims. The README mentions what the character wears in status hover, while `_weather_status` declares place, feels-like, range, rain chance and attribution/staleness, with accessories instead present in Today contributions. Capture the declared hover detail and verify any additional Core rendering rather than promise it.
