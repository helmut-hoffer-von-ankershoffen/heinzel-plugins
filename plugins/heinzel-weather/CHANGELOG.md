# Changelog

## 0.5.0

Weather has its own page: the sidebar item and the footer temperature open it instead of Settings. It shows the temperature, sky, feels like, wind, humidity and rain, the next 24 hours, the next 7 days, alerts, and when the data was updated, in Celsius and km/h (Fahrenheit and mph by locale). A small button in its header changes the place in Settings. Without a place, or while the provider cannot be reached, it says so in words with one button. Needs Heinzelmännchen 0.9.16 or later.

## 0.4.1

Set the place in Settings: "Set a location" and the sidebar open Settings > Weather instead of typing a command into a terminal, and the city of your time zone is used until a place is set.

## 0.4.0

Move this plugin to its independent repository project for the Heinzel 0.9 plugin contract.
Own its dependencies, tests and artifacts; consume public contracts without concrete provider dependencies.

Earlier history: the heinzel repository before 0.9.
