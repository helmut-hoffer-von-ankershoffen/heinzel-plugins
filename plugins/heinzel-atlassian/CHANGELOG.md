# Changelog

## Unreleased

- Work with your own Jira work: `assigned`, `epics` and `watch` read assigned work, epics with progress and what
  deserves attention; `draft-*` and `create-issue`, `update-issue`, `comment-issue` propose and, once a person
  approved, carry out changes. Ticket text is returned as untrusted data.
- Notices and drafts carry what a host needs for notification and approval channels: a stable notice key, title
  and body without ticket text, and the SHA-256, link and plain preview of a draft.
- Fix against the real acli 1.3.39: `search` refuses `updated` as a field (each issue is now read with `view`), and
  answers after a browser login name a `*.prod.atl-paas.net` gateway shard, which is no longer refused as another
  site. A missing or hidden work item and a rejected work item type get messages of their own.
- Live checks and fixtures recorded from a real Jira Cloud site (`tests/live`).

## 0.9.1

Move this plugin to its independent repository project for the Heinzel 0.9.1 plugin contract.
Own its dependencies, tests and artifacts; consume public contracts without concrete provider dependencies.

Earlier history: the heinzel repository before 0.9.
