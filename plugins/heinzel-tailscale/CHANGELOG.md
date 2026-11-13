# Changelog

## 0.9.7

Relock opentelemetry-api to 1.45.2 (CVE-2026-126360).

## 0.9.6

The footer pane no longer has a Details line that only repeats the switch (*Private web sharing is off.*);
Details stay for anything to act on or wait for. The CLI and JSON message is unchanged.

## 0.9.5

Relock for Heinzel Core 0.9.40 (its AI extra adds pyjwt) and refresh the gallery.

## 0.9.4

The switch shows your choice: On reads On while hz finishes turning it on. One short status line replaces the
long text under it (*Turning on…*, the URL, or one cause such as *Sign in to Tailscale, then try again.* with
Try again); the full explanation moves to Details on cores that support it. Sharing turned on from the CLI, or
after a web restart, now finishes on the web app's next status read instead of waiting for a restart.

## 0.9.3

Require Heinzel 0.9.16 as the supported standard-app installation and plugin-change baseline.
Refresh the dependency lock, including the pinned uv runtime, and the source-bound gallery.

## 0.9.2

Rewrite the sharing messages in plain words: what Tailscale already does, what hz left alone and what you can do,
with the exact command. The footer popup now shows one bullet per sentence instead of cutting a sentence at 80
characters.

## 0.9.1

Move this plugin to its independent repository project for the Heinzel 0.9.1 plugin contract.
Own its dependencies, tests and artifacts; consume public contracts without concrete provider dependencies.

Earlier history: the heinzel repository before 0.9.
