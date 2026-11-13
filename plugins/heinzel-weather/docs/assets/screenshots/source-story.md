## Audience

Someone considering Weather for a quick glance at local conditions, a forecast, and a useful command-line result without needing to visit a weather site.

## Outcome

Show how fictional Berlin weather moves from a glance on Today to an explanation in the footer and a fuller forecast. The example uses the existing local OpenWeather fake, so its warning illustrates the interface, not an actual forecast or safety advice. Open-Meteo is the default provider and does not supply severe weather alerts; OpenWeather requires a key and subscription for its One Call API (`README.md`, `src/heinzel_weather/_models.py`).

## Scenes

1. **Today, light:** The current temperature, weather-dressed character, near forecast and, where visible, temperature/rain chart give an immediate sense of the day. Use the existing `today-weather` scene.
2. **A closer glance:** Hover over the genuine footer weather item to reveal its condition, feels-like temperature and rain chance. Crop the resulting region, preserving enough context to identify it as a footer detail. Use `weather-detail`.
3. **The Weather page, light:** Show current conditions, the hourly and daily outlook, and the fictional thunderstorm warning. Use the declared `/?panel=weather:forecast` route and `weather-page` scene.
4. **Today on a phone, dark:** Show the same useful weather experience in an applied dark appearance at a narrow viewport. This is a responsive context, not a claim of another feature. Use `phone-weather`.
5. **Current conditions and hours in the CLI:** `weather show` displays the fictional current conditions, alerts, hours and days using the plugin's report renderer.
6. **A shorter forecast in the CLI:** `weather forecast --days 3` demonstrates a different, useful parameterized result. Both CLI scenes are real command output, not substitutes for feature UI.

## Fictional fixtures

`docs/screenshot_fixture.py` starts the existing local fake, selects OpenWeather, configures `Berlin, DE` and metric units, and supplies a fixture-only key. `src/heinzel_weather/fake.py` supplies clear weather at 21.5 °C, rain beginning in the next hour, cooling and an `Example Weather Service` thunderstorm warning. The fake anchors its server data to the actual capture hour; `browser_time` fixes only the browser clock, so reviewers must check dates and warning timing for coherence. The fixture runs only during explicit capture. No new fixture files are proposed.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript. Also inspect locations, account names, paths, hostnames, credentials, URLs, notifications and unrelated app content; the fixture key is not a real credential. Do not infer that dismissing Doctor or using a fictional profile makes a capture safe.

## Source-bound UI surface inventory

- `pyproject.toml` declares the sole `heinzel.modules` entry point, `weather = "heinzel_weather"`. `src/heinzel_weather/_module.py` declares the module and optional OpenWeather credential; `src/heinzel_weather/__init__.py` supplies its actual contributions.
- **Plugin feature view:** `module.nav` points the sidebar to `/?panel=weather:forecast`, and `module.view` declares `forecast`, sourced from the `page` operation. `web/src/WeatherPage.tsx` renders the weather view, including alert, hourly and daily sections; `src/heinzel_weather/views/index.js` is the bundled view. The route is grounded in the declaration, not inferred from the plugin name.
- **Core-rendered feature UI:** `module.status` contributes `weather-now` to footer and sidebar; `module.widget` contributes `weather-today`, `temperature-today` and `forecast-today` to Today. Their builders in `src/heinzel_weather/__init__.py` define the weather detail, character, chart and forecast list. These are genuine feature UI even though Core renders the contributions.
- **Other Core surfaces:** `module.settings(WeatherSettings)`, `module.nav` settings and `module.setup(required=False)` support configuration; `module.health` contributes Doctor checks; `module.job` can issue notices through `Notifications`; `module.skill` registers `weather-trend`. Operations expose data and may also have generic Core presentations; their presence alone does not prove a particular generic route or visual layout. No plugin channel or approval declaration was found. `docs/adr/0002-weather-observations-and-trend-advice.md` describes separate engine approval responsibilities, not a weather-specific approval screen.
- **CLI and interfaces:** `weather`, `show`, `forecast`, `conditions`, `observe`, `signals`, `info`, `ui` and `page` are declared operations in `src/heinzel_weather/__init__.py`; the README documents CLI, MCP and REST interfaces. The Rich renderers substantiate the selected CLI results. Do not label the operations generally terminal-only: the plugin also provides the feature UI above.
- **External provider UI:** Open-Meteo and OpenWeather are data providers; the supplied source does not establish a provider website screen as part of this capture. No external provider screen is proposed.
- **Evidence limits:** The README describes the Today card and forecast, while the current declarations additionally include a chart. Actual placement, responsive rendering, hover accessibility, applied appearance and the Doctor row must be verified during capture; source declarations alone do not prove the resulting pixels. The fictional alert depends on the OpenWeather fake and must not be presented as an Open-Meteo alert.

## Acceptance criteria

- Capture at least two distinct, useful genuine feature UI scenes and a useful CLI scene; retain both CLI parameter cases. Each image must add useful evidence, with no duplicate captures, caption-only variations, forged HTML or terminal output presented as feature UI.
- Show applied light and dark appearances, readable content and a useful mobile layout. Verify the footer hover and crop show the actual detail. If any planned UI state fails, investigate the real surface rather than replacing it with a terminal screenshot.
- Verify the Weather page and CLI output match the fake's data and identify all captions as fictional. Do not imply the fictional warning is live, or that the default provider supplies alerts.
- Independently inspect every image and transcript for privacy and truthfulness after the narrowly specified mappings; unknown identities fail review. Check that health status and all other Doctor detail remain unchanged.
- Validate the plan with the capture tooling when execution is authorized, then review the generated images and transcript. This proposal has been checked against the supplied schema description and source by inspection; capture and runtime validation were not performed.
