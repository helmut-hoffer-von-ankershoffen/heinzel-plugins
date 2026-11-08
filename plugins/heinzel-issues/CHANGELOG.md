# Changelog

## 0.1.0

- First release: report a problem or request something from the app or `hz issues submit`, and see it as
  Received, Being worked on or Done, with the release that shipped it.
- A task-tracking contract (submit, list, get, changes) with a built-in Beads connector; other trackers plug in
  through the `heinzel_issues.connectors` entry point.
- A notice when a report is being worked on, is done, or is released; open reports on Today.
- Send from the app: the view's form uses the typed-input `send` action (Heinzel 0.9.30+), confirmed before it
  runs; an older Heinzel gets the terminal command instead.
- Beads writes go through the methods of Heinzel's `Tracker` contract (core ADR 0141) with the sender as actor;
  no capability adapter is registered, so other trackers stay bound. Requires Heinzel 0.9.31.
- Opt-in only: in no standard set, and it says how to set it up until a reachable tracker is configured.
- Structured `issues.submit.*` and `issues.watch.*` log events, never with the typed text.
