# Changelog

## Unreleased

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
