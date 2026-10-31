**Audience**
People who want weather beside their daily work, with a fuller forecast available from the CLI.

**Outcome**
See the weather now, notice tomorrow’s outlook, and inspect approaching rain without leaving Heinzelmännchen. The character’s umbrella adds a useful touch: clear skies now can still mean rain ahead.

The default provider is keyless Open-Meteo. These screenshots use the existing local OpenWeather fake; its fictional thunderstorm warning does not demonstrate severe alerts from Open-Meteo, which supplies none.

**Scenes**
1. **today-weather** — Establish the useful everyday view: current temperature, the character with an umbrella, and the coming days on Today. The fictional forecast combines clear skies now with an 80% rain chance today.
2. **weather-detail** — Hover over the footer’s Berlin status to read conditions, feels-like temperature, today’s range and rain chance. Keep the detail crop from the existing plan.
3. **phone-weather** — Show the same useful Today content at 390 × 844, checking that forecast text and attribution remain readable.
4. **cli-weather** — Show the actual `hz weather show` result: current conditions, hourly rain probabilities, five days and a fictional warning from Example Weather Service.
5. **cli-forecast** — Show `hz weather forecast --days 3` as the compact alternative for planning the next few days.

Preserve the existing five-scene sequence, names, routes, captions and commands. Correct the detail trigger from click to hover: the documented click action opens the forecast command. Remove the crop’s `padding` field to match the requested focus schema. No dedicated Weather page is inferred from the navigation entry.

**Fictional fixtures**
Use only `docs/screenshot_fixture.py` during explicit capture in the documented temporary profile. It starts the plugin’s own loopback fake and selects Berlin, metric units and a dummy OpenWeather key. The fixture supplies 21.5 °C now, 21 °C feels-like, rain from the next hour, cooler conditions ahead and an example thunderstorm warning. Displayed temperatures are rounded by the actual renderers. Today’s rain probability should produce an umbrella, rather than sunglasses.

The fake anchors dates and hours to capture time. Omit `browser_time`: freezing only the browser would not freeze this backend fixture. No new fixture files are needed.

**Privacy pitfalls**
Use an isolated profile without connected accounts, personal locations, credentials or terminal history. A stored credential takes precedence over the fixture’s fallback dummy key, so isolation matters. Keep provider attribution visible and label every caption as fictional. A forecast warning is not evidence that a notification was delivered; these scenes make no delivery claim.

**Acceptance criteria**
- All five scenes use actual app or CLI output and the existing bootstrap; at least two useful UI views and both CLI results are readable.
- Today shows Berlin weather, the umbrella, the near forecast and OpenWeather attribution.
- Hover reveals the status details without launching the terminal; the crop retains their meaning.
- The phone capture preserves readable weather content without horizontal clipping.
- CLI captures contain successful weather results, including the three-day parameter case, rather than help or setup output.
- Every caption identifies demo data and stays below 180 characters. Routes, argument arrays, steps and focus fields follow the requested schema.
- The plan was statically checked against the provided source and requested structure. Parser validation and live capture were not run; visual acceptance remains for explicit capture.
