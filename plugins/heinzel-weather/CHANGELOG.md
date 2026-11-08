# Changelog

## 0.5.3

A chart on Today: the temperature over the next 24 hours as a line, the chance of rain as bars, today's range as a band and a marker for now, with a text summary and a table of values for screen readers. Needs Heinzelmännchen 0.9.29.

## 0.5.2

The OpenWeather API key is optional: with the default provider (Open-Meteo) Heinzelmännchen is no longer reported as degraded for a key it does not need, and no notification is posted. With OpenWeather and no key, the weather health check still asks for it.

## 0.5.1

The data credit (Open-Meteo, CC BY 4.0) is shown once, behind the info button on the Weather page, with its link; it is gone from the footer pane, the Today cards and the notifications. The Weather page build script runs only a fixed set of pnpm commands.

## 0.5.0

Weather has its own page: the sidebar item and the footer temperature open it instead of Settings. It shows the temperature, sky, feels like, wind, humidity and rain, the next 24 hours, the next 7 days, alerts, and when the data was updated, in Celsius and km/h (Fahrenheit and mph by locale). A small button in its header changes the place in Settings. Without a place, or while the provider cannot be reached, it says so in words with one button. The data credit (Open-Meteo, CC BY 4.0) is one info button on the page with the link, no longer a line in the footer pane and on the Today card. Needs Heinzelmännchen 0.9.16 or later.

## 0.4.1

Set the place in Settings: "Set a location" and the sidebar open Settings > Weather instead of typing a command into a terminal, and the city of your time zone is used until a place is set.

## 0.4.0

Move this plugin to its independent repository project for the Heinzel 0.9 plugin contract.
Own its dependencies, tests and artifacts; consume public contracts without concrete provider dependencies.

Earlier history: the heinzel repository before 0.9.
