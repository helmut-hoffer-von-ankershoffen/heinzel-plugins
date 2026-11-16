# Changelog

## 0.2.3

- Filter and sort reports, see sent and updated dates, and close your own new Beads reports.
- Bind new Beads reports to the authenticated workspace identity. Earlier reports remain visible to the workspace
  owner; they are not reassigned and cannot be closed from Issues.

## 0.2.2

- Give the Issues sidebar consistent horizontal spacing, including on narrow screens.

## 0.2.1

Requires Python 3.15; relocked.

## 0.2.0

Everything works in the app now; no step needs a terminal.

- Set up in the app: the Issues page asks for the folder with the Beads database, checks that it answers, and saves
  it (`connect`). Nothing is saved when the check fails. The app and the daemon follow the saved settings at their
  next use, without a restart.
- Open a report to read what you sent, the files you sent with it and its history: Sent, Being worked on, Done,
  Released in.
- Send a screenshot or a text file with a report from the app (up to 2 MiB), with Heinzel 0.9.45 or newer; the
  confirmation shows the file shortened. An older Heinzel offers text only.
- More labels: `issues.beads.extra_labels` (the "More labels" field in the setup form) gives every new report further
  labels, so a team's intake queue sees it.
- Your reports only: Issues lists and shows only items with the Issues label that were sent under your login name,
  and changes only items with the Issues label. `list` and `show` are private operations now, so they need your
  sign-in on the network interfaces.
- What you type can never be read by the tracker program as an option: every value goes as `--name=value`.
- The form says under which login name and with which labels a report is stored, before you send.
- The view opens no terminal any more: the `hz setup issues` and `hz issues submit` buttons are gone, and messages
  the app shows name no command.

## 0.1.1

Relock for Heinzel Core 0.9.40 (its AI extra adds pyjwt) and refresh the gallery.

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
