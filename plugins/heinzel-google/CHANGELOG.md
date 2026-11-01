# Changelog

## 0.9.2

Add connected reads for mail, calendar and files with item identity, so a helper wakes only on something new.
Add reviewed writes into Google Docs, Sheets and Slides: the owner approves the exact draft, and a file that changed after review is refused.
Requires a Heinzel core with the connected sources and captured write contracts.

## 0.9.1

Move this plugin to its independent repository project for the Heinzel 0.9.1 plugin contract.
Own its dependencies, tests and artifacts; consume public contracts without concrete provider dependencies.

Earlier history: the heinzel repository before 0.9.
