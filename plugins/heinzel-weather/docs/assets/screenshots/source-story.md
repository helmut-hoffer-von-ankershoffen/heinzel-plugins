## Audience and outcome

For someone deciding whether Weather will make Heinzelmännchen more useful day to day: show a quick glance, the detail behind it, a fuller forecast, and useful command-line results. The forecast and warning are fictional examples, not live advice.

## Scenes

1. **Today, light:** the real Today widgets show the fictional Berlin conditions and near forecast alongside the weather-aware character.
2. **Footer detail:** hover over the genuine weather status to reveal the fictional place, feels-like temperature and rain chance.
3. **Weather page, light:** show current conditions, the hourly outlook and the fictional thunderstorm warning in the actual Weather panel.
4. **Today, dark on a phone-sized viewport:** show how the fictional forecast works in a compact, dark presentation. This is a separate layout and applied appearance, not just a new caption.
5. **CLI report:** `hz weather show` gives the fictional current conditions, hours, days and warning.
6. **CLI forecast:** `hz weather forecast --days 3` gives a concise three-day fictional outlook.

## Fictional fixtures

`docs/screenshot_fixture.py` configures the existing local fake OpenWeather provider, fictional Berlin and metric units for capture. `src/heinzel_weather/fake.py` supplies clear conditions now, approaching rain and an example thunderstorm warning relative to the actual capture hour. The plan's browser clock does not freeze the fake server clock; review dates and times for coherence. `web/src/fixture.ts` is a different frontend fixture with overcast Open-Meteo data and is not the bootstrap selected here. OpenWeather alerts in these scenes do not imply that default Open-Meteo supplies severe alerts (`README.md`).

## Source-bound UI surface inventory

- `pyproject.toml` declares the sole `heinzel.modules` entry point, `weather = heinzel_weather`. Its actual declarations are in `src/heinzel_weather/__init__.py` and `src/heinzel_weather/_module.py`.
- **Plugin feature UI:** `module.nav` points to `/?panel=weather:forecast`; `module.view` registers `forecast`, sourced from the `page` operation. `web/src/index.ts` supplies the ABI 1 view and `web/src/WeatherPage.tsx` renders ready, needs-location, unavailable, stale and guessed states, forecast, alerts and attribution. The packaged view lives under `src/heinzel_weather/views/`.
- **Core-rendered feature UI:** `module.status` contributes `weather-now` to footer and sidebar, including detail and navigation; the three `module.widget` declarations contribute the graphic, temperature/rain chart and forecast list to Today. These are genuine app UI even though Core renders them.
- **Setup and health:** `module.settings(WeatherSettings)`, `module.nav` settings and `module.setup` support Weather settings and setup; `module.health` contributes Doctor checks. `_module.py` declares the optional OpenWeather credential. These are supporting Core surfaces, not the main story.
- **Operations and other surfaces:** `weather`, `show`, `forecast`, `conditions`, `observe`, `signals`, `info`, `ui` and `page` are declared operations. README documents CLI, MCP and REST exposure; generic Core presentation of operations must be checked at capture rather than assumed terminal-only. `module.job` declares `watch` notices, and `module.skill` packages weather-trend. No channel or approval contribution is declared in the inspected module; the ADR says approval belongs to the engine. The plugin supplies weather signals but declares no theme of its own (`pyproject.toml`, `src/heinzel_weather/__init__.py`, `docs/adr/0002-weather-observations-and-trend-advice.md`). External OpenWeather and Open-Meteo provider interfaces are not plugin screens. The CLI scenes are genuine command results and are supplementary to feature UI, not substitutes for it.
- **Unresolved evidence:** source declarations establish intended routes and states, not a successful capture or the current Core layout. The README describes Today weather and days but the source also declares a chart; inspect the running capture for its actual placement. The existing plan expects a footer hover region and English labels; verify those against the actual rendered app.

## Privacy and acceptance

Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail; independent review must inspect every image and transcript for real names, paths, hostnames, credentials, locations and other identifying data.

Capture the actual app and native CLI with the existing bootstrap, with applied light and dark appearances. Verify each scene shows its stated useful behavior and fictional-data caption, including the page warning and two distinct CLI results. Reject duplicate captures or caption-only changes, terminal output presented as feature UI, forged HTML, failed or misleading health states, and any unreviewed identity. Confirm the footer detail, panel route, phone layout and readable forecast in the resulting captures. This plan preserves the existing six-scene plan; its TOML structure was reviewed against the supplied scene rules, but no parser, capture or product code was executed, so runtime validity and visual acceptance remain unverified.
