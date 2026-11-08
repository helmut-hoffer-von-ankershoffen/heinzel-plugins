## Audience

Someone deciding whether Heinzel Weather makes a useful daily forecast available in the app and at the command line, without needing an Open-Meteo account.

## Outcome

Show a fictional Berlin forecast progressing from an at-a-glance Today view to an inspectable forecast and two useful CLI results. The capture fixture uses a local fake OpenWeather provider, so its warning demonstrates the OpenWeather-backed experience; it does not imply that the default Open-Meteo provider supplies severe alerts.

## Scenes

1. **Today weather:** The light Today view shows the current conditions and upcoming days, with the weather-aware character and chart if visible. Source: `src/heinzel_weather/__init__.py`, `today_weather`, `temperature_today`, and `forecast_today`.
2. **Weather detail:** Hover the footer weather status to inspect its real detail: location, feels-like temperature, daily range, and rain chance. Source: `src/heinzel_weather/__init__.py`, `_weather_status` and `current_weather`.
3. **Weather page:** The actual Weather panel presents the fictional warning, current conditions, and hourly outlook. Its daily outlook follows in the same view. Sources: `src/heinzel_weather/__init__.py`, `module.nav`, `module.view`, and `page`; `web/src/WeatherPage.tsx`, `Forecast`.
4. **Phone weather:** The dark, phone-sized Today view shows how the same useful forecast fits a smaller display. Verify that dark appearance is actually applied and that its composition is meaningfully different from scene 1.
5. **CLI weather:** `hz weather show` presents the current report, approaching rain, hours, days, and the fictional warning through the real CLI renderer.
6. **CLI forecast:** `hz weather forecast --days 3` presents a shorter daily planning view. Sources for both CLI scenes: `src/heinzel_weather/__init__.py`, `show`, `forecast`, `_render_report`, and `_render_forecast`.

## Fictional fixtures

`docs/screenshot_fixture.py` starts the existing `heinzel_weather.fake.serve` on loopback, configures fictional Berlin, metric units and a fake credential, then launches Heinzel. `src/heinzel_weather/fake.py` supplies 21.5 °C and clear skies now, rain from the next hour, and an example thunderstorm warning. Its data follows the server's actual capture hour; `browser_time` fixes only the browser clock, so displayed dates and relative times must be checked for coherence. `web/src/fixture.ts` is a separate frontend test fixture and is not the capture bootstrap.

## Source-bound UI surface inventory

- **Plugin entrypoint:** `pyproject.toml` declares `heinzel.modules` entrypoint `weather = "heinzel_weather"`; its actual declarations are in `src/heinzel_weather/__init__.py` and `src/heinzel_weather/_module.py`.
- **Plugin feature UI:** `module.nav` points the sidebar to `/?panel=weather:forecast`; `module.view` registers `forecast`, sourced from operation `page`, with ABI 1. `web/src/index.ts` returns `WeatherPage`, implemented in `web/src/WeatherPage.tsx`. This is genuine feature UI, not external provider UI or a terminal substitute.
- **Core-rendered feature UI:** `current_weather` contributes footer and sidebar status with a detail and navigation action; `today_weather`, `temperature_today`, and `forecast_today` contribute graphic, chart, and list widgets. These are genuine feature surfaces even though Core renders them. `module.settings(WeatherSettings)`, `module.nav` settings, and `setup` provide configuration surfaces; `ready` contributes Doctor health checks. `watch` can emit Core notices via `_notify` in `src/heinzel_weather/_service.py`. The plan does not claim to capture a notice or setup flow.
- **Operations and other contributions:** `ui`, `page`, `observe`, `weather`, `show`, `forecast`, `signals`, `conditions`, and `info` are declared operations; `watch` is a scheduled job, and `module.skill` registers packaged skill text. The plugin declares an optional credential in `src/heinzel_weather/_module.py`. No plugin channel or approval contribution is declared in the provided entrypoint; the trend ADR describes separate Core grants and approvals rather than asserting a plugin approval screen. Operations may also be exposed through Core surfaces; their declarations alone do not establish a particular additional app screen.
- **External provider UI:** Open-Meteo and OpenWeather are data providers, not app screens in this plan. CLI output is genuinely CLI output, not feature UI. The plugin supplies a text fallback for an unavailable view, but that does not make the feature CLI-only.
- **Unresolved evidence:** `README.md` describes a Weather-page info button and attribution in status detail and Today; the inspected `web/src/WeatherPage.tsx` and `_weather_status` do not visibly render those elements. Verify the shipped bundle and Core behavior before asserting or depicting those claims. The source also describes a shared 15-minute observation while `module.view` declares `refresh=300`; the latter is a view refresh declaration, not proof of a five-minute provider fetch. Do not infer capture success from declarations alone.

## Privacy pitfalls

Use only the isolated fictional profile and fake credential; never capture real locations, accounts, API keys, machine names, paths, notifications, or unrelated personal content. Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and an independent reviewer must inspect every image and transcript. Do not fabricate a Doctor row or hide a failure through substitution.

## Acceptance criteria

- Capture the real app and real CLI using the existing bootstrap only during explicit capture; no forged HTML or invented product screens. Preserve provider attribution wherever the real surface supplies it.
- Show at least two distinct, useful feature UI scenes and a useful CLI result; the existing plan supplies Today, footer detail, Weather panel, phone layout, and two different CLI operations. Reject duplicate captures and caption-only differences.
- Confirm the requested light and dark appearances are applied in the actual captures. Ensure the phone scene remains legible and materially distinct.
- Verify visible forecast values, warning, location, and CLI output against the fake at capture time; do not present the fictional warning as a real alert or as an Open-Meteo capability. Check browser/server clock coherence.
- Keep captions identifying demo data. Inspect each full image and transcript independently for identity and secrets, including any Core Doctor content, before publication. Failed privacy checks fail the capture.
- The TOML below preserves the existing useful plan. It has been checked against the supplied field and step rules by inspection; no parser, capture, imports, network calls, or plugin code were run, so runtime rendering and privacy acceptance remain unverified.
