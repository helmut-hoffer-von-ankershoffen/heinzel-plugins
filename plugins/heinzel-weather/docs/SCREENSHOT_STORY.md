# Know the weather before the next meeting or commute

Show why Weather belongs on Today: current conditions, a useful multi-day outlook and a character that reflects
the forecast. The primary image must contain populated weather cards. A provider/settings form or **Set a
location** prompt is not a conversion image.

## Demonstration profile

Use `docs/screenshot_fixture.py`, which starts this plugin's `heinzel_weather.fake.serve(0)` on loopback and launches
the installed `hz` entry point. It sets provider `openweather`, metric units, location **Berlin, DE**, a loopback
base URL and a deliberately fake credential. Keep the environment credential backend and isolated state; never
use a real account or request a live forecast. Berlin is a fictional demo location, not inferred user location.

The fixture currently serves **21.5°C** clear sky, feels like **21°C**, today's high **24°C**, low **11.5°C**, rain
probability **80%**, and rain approaching in the next hour. The Today card rounds current temperature to **22°C**;
the expected accessory is an umbrella even though it is clear right now. The near forecast includes changing
conditions, not repeated empty rows. These are canned provider answers, not current Berlin weather.

```sh
python docs/screenshot_fixture.py weather show
python docs/screenshot_fixture.py weather forecast --days 3
python docs/screenshot_fixture.py ui --no-browser --port 0
```

Run from the owning plugin in its installed SDK environment and isolated profile. Normal public equivalents are
`hz weather show`, `hz weather forecast --days 3`, and `hz weather ui --json`. For standalone provider debugging,
`python -m heinzel_weather.fake --port 8787` exposes the same local fake. `serve(port, now=callable)` can anchor its
dates; the weather service also has a clock. Align both if a capture requires fixed dates rather than relative days.

## Scenes to publish

| Scene | Action and visible proof | Caption |
| --- | --- | --- |
| `today-weather` | At `/`, wait for **Weather in Berlin, DE** and **22°C**. Frame both the graphic current-weather card and the list forecast card: umbrella-bearing character, condition, several day rows with high/low temperatures and rain chances, and provider attribution. | “Current weather and the coming days on Today — fictional Berlin forecast.” |
| `weather-detail` | Inspect the footer weather control and keep the entire expanded detail above its trigger. Show **Clear sky · Berlin, DE**, **Feels like 21°C**, today's low/high and 80% rain, plus attribution. Keep the populated Today cards behind it when space permits. | “Inspect conditions, feels-like temperature and rain chance from the weather status.” |
| `phone-weather` | At 390×844, capture the populated current-weather and forecast cards at a useful scroll position. Text, character and day rows must remain readable, with no horizontal clipping. | “Plan the next few days from the phone-sized Today view.” |
| `cli-weather` | Run `hz weather show` through the fixture. Show actual current conditions, the approaching rain, hourly outlook, daily forecast and the fixture's warning where rendered. Preserve attribution. | “Explore the detailed hourly and daily demonstration forecast in the CLI.” |
| `cli-forecast` | Run `hz weather forecast --days 3` through the same fixture. Show three distinct days with low/high, sky and rain probability; avoid a long unreadable output strip. | “Get a concise three-day outlook in the CLI.” |

The same weather status appears in both sidebar and footer. A global button match `22.*Berlin` is ambiguous:
scope to the footer landmark, or hide only the sidebar status for the detail scene with
`hz system ui hide weather:weather-now --slot sidebar`. A sidebar click runs `hz weather show`; a footer click pins
the detail popover. If the footer overflowed, first open **More status items**. The popover is current-condition
detail, not a custom right-side forecast panel. Never caption it as showing hourly data that is only in the CLI.

## Acceptance and privacy

Both Today widgets must be populated before capture; reject **Set a location**, **Loading…**, stale observations,
failed refreshes, empty cards and unrelated settings screens. Confirm the umbrella is visible, current values agree
with CLI rounding, future days have readable temperatures/rain chances, and provider attribution is retained.
At desktop and phone widths, inspect both the card content and expanded-status geometry, not merely DOM presence.

Stage images and transcripts privately. An agent must inspect every frame for real identity, account addresses,
credentials, private locations, paths, browser/session tokens and accidental live-provider output before promotion.
Do not display the fake API-key value either; it belongs only in the local fixture environment. Captions must say
demonstration or fictional forecast so a public gallery cannot be mistaken for a live weather report.
