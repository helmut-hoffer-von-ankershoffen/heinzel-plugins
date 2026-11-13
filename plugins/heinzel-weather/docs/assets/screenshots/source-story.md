## Audience

People deciding whether Weather will give them a useful glance at local conditions in Heinzelmännchen, a fuller forecast when needed, and a practical command-line result.

## Outcome

A viewer can follow the fictional Berlin weather from Today’s quick glance to the detailed forecast and a three-day CLI outlook. The gallery demonstrates the plugin’s own UI and Core-rendered contributions using the existing offline fixture. It does not imply that the fictional warning is a live alert or that the default provider supplies severe-weather alerts.

## Scenes

1. **Today weather — light:** Show the current conditions and near forecast in Core’s Today view. The weather graphic, temperature-and-rain chart, and forecast list are separately declared contributions; retain this scene only if the capture makes useful weather content legible.
2. **Weather detail:** Hover the footer weather status to reveal the place, feels-like temperature, daily range and rain chance. Crop the actual detail region. This is a meaningful interaction, not a caption-only variation.
3. **Weather page — light:** Show the plugin’s actual forecast page, including current conditions, the hourly outlook and the fictional warning when visible. The page also contains daily forecasts and provider attribution; do not claim they appear in a single image if they are outside the captured viewport.
4. **Phone weather — dark:** Show the responsive Today view in a phone-sized viewport with dark appearance applied. Keep it only if its layout and visible weather information make it meaningfully different from the desktop view.
5. **CLI weather:** Show `hz weather show`, including the fictional current conditions, hours, days and warning as space permits.
6. **CLI forecast:** Show `hz weather forecast --days 3`, a concise parameterized three-day result. These are two different operations, each with a useful result; neither is presented as feature UI.

## Fictional fixtures and timing

`docs/screenshot_fixture.py` starts the existing loopback fake and configures Berlin, metric units and the OpenWeather provider with a dummy key. `src/heinzel_weather/fake.py` supplies clear weather at 21.5 °C, rain beginning in the next hour, cooling and a fictional thunderstorm warning from Example Weather Service. The fake’s server data is anchored to the actual capture hour; `browser_time` freezes only the browser clock. Check dates, update times and day labels for coherence during capture rather than assuming the browser clock freezes the server. `web/src/fixture.ts` is a separate frontend fixture with different overcast data and is not the bootstrap used by this plan.

## Privacy pitfalls

Normal presentation fictionalization is disclosed: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail. An independent reviewer must inspect every image and transcript for real names, paths, hostnames, locations, credentials and other identifying data. The optional Doctor dismissals do not replace that review. The fixture key is fictional; do not expose real credentials or connected-account data.

## Acceptance criteria

- Capture the genuine app and native CLI using the existing bootstrap, with no forged HTML, invented screens or external-provider website presented as the product.
- Verify at least two useful feature UI scenes and a useful CLI result; verify light and dark appearances were actually applied. Reject duplicate images, caption-only changes, unreadable crops and terminal output presented as feature UI.
- Confirm the footer hover and its accessible region work as declared in the running Core version. Confirm the Weather page route loads its actual bundled view, and that the warning and forecast data match the fake. If a selector or route fails, record the failure rather than substituting a fabricated screen.
- Check the phone scene contributes a distinct responsive view; remove or revise it if it merely duplicates the desktop capture. Review image framing, visible truncation, attribution where shown, and every transcript independently.
- Treat this as a source-reviewed plan, not a completed capture or privacy approval. TOML structure has been checked against the requested format by inspection; no parser, capture, imports, network calls or code execution were used for validation.

## Source-bound UI surface inventory

- **Entrypoint and page:** `pyproject.toml` declares `heinzel.modules` entrypoint `weather = "heinzel_weather"`. `src/heinzel_weather/__init__.py` declares `module.nav` with sidebar navigation and `module.view` named `forecast`, source `page`, slot `page`, route `/plugins/weather/forecast`, ABI 1. `web/src/index.ts` supplies the SDK view and `web/src/WeatherPage.tsx` implements ready, needs-location, unavailable and stale states, forecast, alerts, source info and settings shortcut. `src/heinzel_weather/views/index.js` is the bundled view. This is genuine feature UI, not an external provider page.
- **Core-rendered feature UI:** `src/heinzel_weather/__init__.py` declares the `ui` operation; `current_weather` status in footer and sidebar; and `today_weather`, `temperature_today`, and `forecast_today` widgets. Their builders define the status detail, graphic/avatar, chart and forecast list. Core renders these contributions; the provided sources do not establish Core’s exact DOM, layout or hover-region accessibility, so capture must verify them. The status and sidebar navigate to the declared page; the change-place action points to `/?settings=weather`.
- **Other Core surfaces:** The same module declares `WeatherSettings` via `module.settings`, a `module.setup` prompt, `module.health` checks and the `watch` job using `Notifications` when available. Settings, setup, Doctor and notices may be rendered by Core; their exact presentation and routes beyond the declared settings navigation are not established here. `module.operation` declarations also expose weather, show, forecast, conditions, observe, signals, info, ui and page; generic Core operation UI cannot be ruled out from this source. No channel or approval contribution is declared in the inspected module. The `weather-trend` skill is registered through `module.skill`.
- **CLI and interfaces:** `src/heinzel_weather/__init__.py` declares renderers for `weather`, `show`, `forecast` and `conditions`; `README.md` documents CLI, MCP and REST counterparts. The selected CLI scenes are genuine command results, not evidence that the operations are terminal-only.
- **External providers:** `src/heinzel_weather/_module.py` declares an optional OpenWeather credential, and `src/heinzel_weather/_api.py` implements its API client. `README.md` identifies Open-Meteo as the keyless default and OpenWeather as an optional keyed provider. The capture fixture deliberately uses a local OpenWeather fake, not either provider’s external UI. Open-Meteo has no severe alerts according to `README.md`.
- **Evidence qualification:** The `src/heinzel_weather/__init__.py` module docstring mentions the footer and Today widget but omits the separately declared page and chart; the declarations and view implementation establish those additional surfaces. `README.md` describes the shared observation and page, while `web/src/fixture.ts` depicts a different fictional forecast than the capture bootstrap. Neither discrepancy warrants inventing another screen.
