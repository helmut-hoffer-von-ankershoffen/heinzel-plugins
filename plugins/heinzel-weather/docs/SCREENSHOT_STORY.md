**Audience**
Heinzelmännchen users who want weather beside their daily work, with a fuller forecast available from the CLI.

**Outcome**
Answer “What’s it like now, and should I bring an umbrella?” from Today, then inspect the next hours or choose a shorter outlook. The plugin defaults to keyless Open-Meteo; these screenshots demonstrate its existing local OpenWeather fixture. The fictional warning shown by that fixture does not demonstrate notification delivery or Open-Meteo alerts.

**Scenes**
1. **today-weather:** Open Today with fictional Berlin weather: 22°C displayed, clear sky, an umbrella accessory because today’s rain chance is 80%, and the coming days. The character makes the forecast memorable without replacing the numbers.
2. **weather-detail:** Hover the footer’s Berlin status and crop its existing detail region. Show clear sky, feels like 21°C, today’s rounded 12–24°C range, 80% rain chance and provider attribution.
3. **phone-weather:** Show the same useful Today content at 390 × 844. Check that temperature, forecast and attribution remain readable.
4. **cli-weather:** Run `hz weather show`. Show hourly rain probabilities, cooling conditions, the five-day outlook and the clearly fictional thunderstorm warning from Example Weather Service.
5. **cli-forecast:** Run `hz weather forecast --days 3`. Show a compact three-day result with lows, highs, rain chances, sky descriptions and attribution.

**Fictional fixtures**
Reuse only `docs/screenshot_fixture.py` and its existing `heinzel_weather.fake` implementation. During explicit capture, the bootstrap starts a loopback server on an available port and selects fictional Berlin weather, metric units and a dummy credential. The fixture supplies 21.5°C now, rain beginning next hour, cooling toward 12°C and a sample warning. Retain the documented temporary fictional profile. The added browser clock fixes browser time only: the existing fixture still anchors forecast timestamps to the server’s capture hour.

**Privacy pitfalls**
Keep personal accounts, actual locations, credentials, notifications and terminal history outside the capture profile. Label every image as fictional demo data and retain the provider attribution, including in the detail crop. Describe the warning as a fixture result, never as a real public warning or proof that a notice was delivered.

**Acceptance criteria**
- Preserve the existing five scenes, captions, commands, interactions and phone viewport; add only the requested browser time and its clock limitation comment.
- Today shows both current weather and the near forecast; the hover scene exposes useful detail; the phone view has readable content without clipping essential information.
- CLI captures contain completed real command results. The three-day command produces three day rows. Do not add individual table-cell waits.
- Optional Doctor dismissals may clear overlays; the detail hover and crop must resolve to the intended existing UI.
- Static review checks TOML structure, five unique lowercase names, three UI scenes, two CLI scenes, captions under 180 characters, local routes, accessible locators, the existing relative bootstrap and argument-array commands.
- No source was changed, imported or run, and no network calls or captures were made. Runtime rendering and locator success remain acceptance checks for explicit capture.
