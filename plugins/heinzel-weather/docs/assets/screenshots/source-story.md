## Audience and outcome

For someone deciding whether Weather earns a place in their Heinzelmännchen setup: see the forecast at a glance, inspect the coming rain and warning, and get the same kind of practical forecast in a terminal. The warning and all weather shown are fictional examples, not live advice.

## Scenes

1. **Today, light:** The graphic and forecast list show the fictional Berlin conditions alongside the weather-dressed character. This establishes the everyday glanceable benefit.
2. **Status detail:** Hover over the footer’s Berlin weather item to inspect the fictional conditions, feels-like temperature and rain chance. Crop the actual detail region, retaining enough context to identify it.
3. **Weather page, light:** Show the fictional current conditions, hourly outlook and thunderstorm warning in the actual Weather panel. The warning comes from the fake OpenWeather response; it is not a claim that the default Open-Meteo provider supplies alerts.
4. **Today, dark and phone-sized:** Show the same fictional forecast in the applied dark appearance at 390 × 844. This is a responsive and appearance example; retain it only if the capture visibly demonstrates that difference from scene 1.
5. **CLI report:** `hz weather show` displays the fictional current conditions, hours, days and warning.
6. **CLI forecast:** `hz weather forecast --days 3` demonstrates a shorter, parameterized fictional outlook. These CLI scenes are genuine terminal results, not substitutes for feature UI.

The existing plan already covers these useful behaviors, so it is preserved below. Scenes 1–3 must each show their distinct contribution; reject duplicate images or differences limited to captions.

## Fictional fixtures

`docs/screenshot_fixture.py` is the existing bootstrap. At explicit capture time it starts the local fake server from `src/heinzel_weather/fake.py`, selects OpenWeather, sets Berlin and metric units, and supplies a fake key. The fake describes 21.5 °C and clear conditions now, rain beginning in the next hour, cooling, and an example thunderstorm warning. Its server data is anchored to the capture hour; `browser_time` fixes only the browser clock, so do not imply the two clocks are synchronized without checking the resulting images. The fixture’s OpenWeather choice is a demonstration configuration; `README.md` and `WeatherSettings` describe Open-Meteo as the keyless default.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited to these mappings: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and an independent reviewer must inspect every image and transcript. Check for real locations, usernames, paths, hostnames, credentials, unrelated notices and account data. The fixture key and Berlin forecast are examples; do not expose real credentials or claim the fake warning is live.

## Acceptance criteria

- Capture the real app and real CLI using the declared bootstrap; no forged HTML, invented screens or fabricated terminal output. Verify the panel and status interactions actually work in the installed Core and plugin combination.
- Show at least two useful, distinct feature UI scenes and a useful CLI result. The light and dark appearances must actually be applied; the phone scene must visibly demonstrate its viewport. Reject duplicate captures, caption-only changes and terminal output represented as feature UI.
- Verify the forecast, warning, attribution and times against the fixture and the rendered output. Do not claim Open-Meteo provides severe alerts. Preserve any stale or health status exactly as rendered.
- Independently inspect every image and transcript for privacy, including the narrowly permitted mappings above; an unknown identity is a failure. Review the contact sheet and manifest described in `docs/SCREENSHOTS.md`.
- The TOML below has been reviewed against the requested structure and the existing plan, but was not parsed or capture-tested because execution was prohibited. Resolve any runtime accessibility, route, timing or rendering mismatch before publication.

## Source-bound UI surface inventory

- **Entry point and actual view:** `pyproject.toml` declares `heinzel.modules.weather = "heinzel_weather"`. `src/heinzel_weather/__init__.py` registers `module.nav` with sidebar `/?panel=weather:forecast`, and `module.view` named `forecast`, sourced from the `page` operation. `web/src/index.ts` supplies the ABI-1 view, and `web/src/WeatherPage.tsx` implements ready, missing-location, unavailable and stale states, forecast, warning, attribution and settings shortcut. The packaged `src/heinzel_weather/views/index.js` is the registered view artifact; its correspondence with the readable web source needs capture-time verification.
- **Core-rendered feature contributions:** In `src/heinzel_weather/__init__.py`, `module.status(source="ui", name="weather-now", slots={"footer": True, "sidebar": True})` contributes the status and detail; `module.widget` declares `weather-today` and `forecast-today`. Their `ui` operation supplies shared data. Status and widgets are actual feature UI even though Core renders them. The declared status effect opens the Weather panel and its Change place action opens settings.
- **Settings, setup and health:** `module.settings(WeatherSettings)`, the navigation settings section, `module.setup(required=False)`, `module.credential` in `src/heinzel_weather/_module.py`, and `module.health` declare Core-facing configuration, setup and Doctor contributions. They are supporting surfaces, not the main story. Doctor checks configured location and OpenWeather credential readiness; the health declaration explicitly does not query the provider.
- **Operations and other surfaces:** `src/heinzel_weather/__init__.py` declares `weather`, `show`, `forecast`, `conditions`, `signals`, `info`, `observe`, `ui` and `page` operations; `README.md` documents CLI, MCP and REST exposure for the public weather operations. Core may render generic operation or info surfaces, but their exact presentation is not established by these supplied files, so no invented route or UI is included. The `watch` job can create notices; no plugin channel or approval declaration is present. `docs/adr/0002-weather-observations-and-trend-advice.md` says the packaged `weather-trend` skill and observation do not grant operations, send notices or provide approval. External provider account/key pages are external UI, not plugin screens. The two planned command results are genuinely CLI captures; the underlying weather capability also has feature UI.
- **Evidence tension:** `README.md` says the status detail includes what the character wears and that attribution appears in Today items. The actual `_weather_status`, `_weather_card` and `_forecast_card` builders in `src/heinzel_weather/__init__.py` do not explicitly put attribution in those items, and the status detail does not explicitly include accessories; the list and graphic do use accessories. Check actual Core rendering before making either claim. `README.md` also calls the page data-contributed, while `module.view` declares a packaged custom view; both the declaration and real rendered result matter.
