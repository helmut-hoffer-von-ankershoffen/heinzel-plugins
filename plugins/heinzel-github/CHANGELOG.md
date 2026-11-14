# Changelog

## 0.9.5

Find gh when Heinzel runs as a background service: a service that launchd starts has a short PATH without Homebrew's folders, so Heinzel did not find gh and every GitHub read failed. Heinzel now looks in Homebrew's folders (`/opt/homebrew/bin`, `/usr/local/bin`) after PATH, and gh runs with its own folder and Homebrew's on PATH.
Say where Heinzel looked when gh can't be found.

## 0.9.4

Relock opentelemetry-api to 1.45.2 (CVE-2026-126360).

## 0.9.3

Relock for Heinzel Core 0.9.40 (its AI extra adds pyjwt) and refresh the gallery.

## 0.9.2

Add a GitHub release feed for draft workflows. It starts at the current release frontier and reads published
release notes alongside the matching section of the supplied CHANGELOG. It stops without advancing the cursor
when a release cannot be matched or the bounded GitHub page may hide releases. Requires Heinzel 0.9.16 or newer.

## 0.9.1

Move this plugin to its independent repository project for the Heinzel 0.9.1 plugin contract.
Own its dependencies, tests and artifacts; consume public contracts without concrete provider dependencies.

Earlier history: the heinzel repository before 0.9.
