# Changelog

## 0.9.8

Search your Google Docs, Sheets and Slides from Heinzel: the documents adapter finds files whose name or text contains your words (Drive full-text search, trashed files left out), with the title, link and, when Drive has one, a short description. It reads only and asks for no new Google grant. Whether Drive matches the text inside files under today's read-only Drive grant is not yet proven; if Drive refuses, the search says it needs broader Drive access (see the README).
A Docs, Sheets, Slides or Drive link now goes to Google when other document sources, such as Confluence, are connected too. Search and link routing need Heinzelmännchen 0.9.43 or later; on older versions everything else works as before.

## 0.9.7

Sign in to Google from Heinzel, without a terminal: the plugin declares its sign-in (Heinzelmännchen ADR 0136), so `hz system connector connect google` runs `gws auth login` asking for exactly the grants needed. The first sign-in reads your Docs and calendar; mail only when you read mail from Google or allow it; a change only when you allow it; never Google Cloud access. Finish it on the computer Heinzel runs on.
Errors about the sign-in are plain sentences that name `hz setup google`, without Google's scope addresses.
Needs Heinzelmännchen 0.9.30 or later.

## 0.9.6

Start gws when Heinzel runs as a background service: gws installed with npm under Homebrew needs `node`, which a short service PATH lacked, so the Calendar pane said gws gave no version. gws now runs with its own folder and Homebrew's (`/opt/homebrew/bin`, `/usr/local/bin`) after PATH, and Heinzel finds gws there too.
Say plainly what is wrong when gws can't be found, can't start or gives no version: where Heinzel looked, and the one next step.

## 0.9.5

Relock against Core 0.9.40. The mail-review and schedule journeys send from the personal conversation's Send button, which replaced Queue message in Core 0.9.40.

## 0.9.4

Relock opentelemetry-api to 1.45.2 (CVE-2026-126360).

## 0.9.3

Ask separately, in two plain lines, before the sign-in requests Docs write access (`documents`); reads keep working without it.
Log the consent step with structured fields (`google.setup.step.start` and `.outcome`).

## 0.9.2

Add connected reads for mail, calendar and files with item identity, so a helper wakes only on something new.
Add reviewed draft insertion into existing Google Docs and Slides, with exact owner approval and revision preconditions.
Add marked draft appends and human-edit capture for the selected tab of an existing Google Doc.
Sheets writes, file creation and existing Slides sections remain refused by the captured-write contract.
Require published Heinzel 0.9.16 for the captured read, write and draft-append APIs.
Declare the Slides API host and request its read-only scope during normal login; existing users must explicitly re-consent to add Slides reads.

## 0.9.1

Move this plugin to its independent repository project for the Heinzel 0.9.1 plugin contract.
Own its dependencies, tests and artifacts; consume public contracts without concrete provider dependencies.

Earlier history: the heinzel repository before 0.9.
