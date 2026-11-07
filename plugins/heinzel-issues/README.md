# Issues

Report a problem or request something, then see where it stands: **Received**, **Being worked on** or **Done**, and
once it ships, **Released in 0.9.27 on 7 Nov 2026**. You never see the tracker behind it: no statuses of its own,
no ids, no pull requests, unless you ask for the details.

Add it with `hz system plugin add issues --confirm`. It is off until you choose a tracker.

## Use it

- **In the app:** open **Issues** in the sidebar. The list shows each report with its state as a word and a mark
  (○ Received, ◐ Being worked on, ✓ Done), never colour alone. **Report or request** opens the app's terminal
  with `hz issues submit`; a text box with **Send** right in the view appears once Heinzel lets plugin views send
  text to their own operations. Your open reports also appear on Today.
- **In a terminal:**

  ```sh
  hz issues submit "The footer clock jumps by a pixel every minute"
  hz issues submit "Here is what I saw" --attachment shot.png
  hz issues list
  ```

  `hz issues list --json` adds the details for agents and experts: the tracker, its id and status, and each pull
  request with its release. `hz issues show <id>` shows one.
- **Notices:** every five minutes the daemon looks for changes and tells you when a report is being worked on, is
  done, and when it is released. The first check after turning Issues on only remembers what is there.

When nothing is set up, the app says **Issue tracking is not set up** with one button, **Set up issue tracking**;
`hz issues list` says the same and names `hz setup issues`.

## Set it up

`hz setup issues` asks where reports go and, optionally, a git clone whose tags are releases. Or set it directly:

```toml
[issues]
tracker = "beads"

[issues.beads]
path = "~/Code/team-board"   # the folder with the .beads database
label = "heinzel-issues"      # what Issues gives each report, and the items it shows

[[issues.releases]]
path = "~/Code/harbor"        # a clone on this computer; read, never fetched
names = ["core"]              # how notes name it: "core #12"
ref = "origin/main"
tags = "v*"
```

`hz system doctor` reports Issues as up while it is off, and as down with the reason when a chosen tracker does
not answer.

## How "Released in" is found

Whoever works on a report notes the pull request in the tracker: `Fixed in #562`, `gh-562`, `plugins #38` or a
pull request link. Issues finds the merge commit whose subject ends in `(#562)` on the configured branch, then the
oldest release tag matching the pattern that contains it. A report with several pull requests is released when the
last of them is. The clone is only read; keep it fetched as you normally do.

## Trackers

Beads is built in: Issues runs `bd ... --json` in the configured folder, on this computer, and never syncs,
pushes or publishes. Other trackers (Linear, Jira, GitHub issues, cards in git) plug in behind the same contract,
described in [docs/CONTRACT.md](docs/CONTRACT.md), without a change to Issues or to Heinzel's core.

## Privacy

What you send stays in the tracker you chose. Issues stores only what it has already told you, under Heinzel's
state folder, readable by you only. Notices are local, like every Heinzel notice.

## Develop

From this directory: `make setup`, `make check-fast`, `make check`, `make build`, `make acceptance`. The
integration tests create a temporary Beads database and need `bd` installed; they are skipped without it.
