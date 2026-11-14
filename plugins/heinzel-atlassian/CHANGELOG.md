# Changelog

## 0.9.7

Say which web addresses Confluence opens: with several documents connectors active, Heinzel routes a Confluence page link to this plugin by the host of your site (never Atlassian's API gateway). Older Heinzel versions ignore it. Confluence search is not offered: acli 1.3 has no page search or CQL, and it arrives once acli offers it.

## 0.9.6

Find acli when Heinzel runs as a background service: a service that launchd starts has a short PATH without Homebrew's folders, so Heinzel did not find acli, could not read the site acli is signed in to, and System health showed the Atlassian hosts as unknown. Heinzel now looks in Homebrew's folders (`/opt/homebrew/bin`, `/usr/local/bin`) after PATH, and acli runs with its own folder on PATH.
Say where Heinzel looked when acli can't be found.

## 0.9.5

Relock opentelemetry-api to 1.45.2 (CVE-2026-126360).

## 0.9.4

Relock for Heinzel Core 0.9.40 (its AI extra adds pyjwt) and refresh the gallery.

## 0.9.3

- Say the true sign-in state: `hz atlassian status` reads `acli auth status` and `acli <product> auth status` and
  reports `not-installed`, `not-connected`, `needs-attention` or `connected` with who, which site, a one-line cause and
  the one command to run (`brew install acli`, or `acli jira auth login --web`). Signed in to acli but Jira or
  Confluence not authorised yet is `needs-attention`, not "not connected". The doctor check carries the same verdict.
- The site is read from acli when `atlassian.site_url` is not set.

- Work with your own Jira work: `assigned`, `epics` and `watch` read assigned work, epics with progress and what
  deserves attention; `draft-*` and `create-issue`, `update-issue`, `comment-issue` propose and, once a person
  approved, carry out changes. Ticket text is returned as untrusted data.
- Notices and drafts carry what a host needs for notification and approval channels: a stable notice key, title
  and body without ticket text, and the SHA-256, link and plain preview of a draft.
- Fix against the real acli 1.3.39: `search` refuses `updated` as a field (each issue is now read with `view`), and
  answers after a browser login name a `*.prod.atl-paas.net` gateway shard, which is no longer refused as another
  site. A missing or hidden work item and a rejected work item type get messages of their own.
- Live checks and fixtures recorded from a real Jira Cloud site (`tests/live`).

## 0.9.2

Add assigned work, epics and attention views, and Jira changes the owner approves.
Hand hosts notices and drafts shaped for notification and approval channels.

## 0.9.1

Move this plugin to its independent repository project for the Heinzel 0.9.1 plugin contract.
Own its dependencies, tests and artifacts; consume public contracts without concrete provider dependencies.

Earlier history: the heinzel repository before 0.9.
