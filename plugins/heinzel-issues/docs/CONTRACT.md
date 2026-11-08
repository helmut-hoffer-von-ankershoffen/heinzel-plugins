# The task-tracking contract

Issues talks to a tracker only through `TaskTracker` in `heinzel_issues._contract`. A connector implements four
operations and maps the tracker's own statuses onto three states; everything else stays inside the connector.

| Operation | What it does |
|---|---|
| `submit(title, body, attachments)` | Create an item from a person's report; it starts as `received`. |
| `list()` | Every item submitted through Issues, newest first. |
| `get(task_id)` | One item by the tracker's id. |
| `changes(since)` | Items changed after `since` (all for `None`); the daemon's watch calls it every five minutes. |

Each returns `Task`s: `id`, `title`, `body`, `state` (`received`, `working`, `done`), the tracker's own `status`,
`created_at`, `updated_at`, `closed_at`, and `references`: text written by whoever works on the item (notes, links,
close reason) where pull request numbers are found. Never put the submitter's own text in `references`.

A connector raises `TrackerError` with a plain sentence that says what to do; Issues shows it as it is.

## Adding a connector

Register a factory in your package under the `heinzel_issues.connectors` entry point group:

```toml
[project.entry-points."heinzel_issues.connectors"]
linear = "harbor_linear.issues:connect"
```

The factory receives the settings table `issues.connectors.<name>` and returns a `TaskTracker`. People choose it
with `issues.tracker = "linear"`. A connector that fails to load is skipped; a built-in name always wins.

## The Beads connector

| Beads status | State |
|---|---|
| `open`, `deferred`, `pinned`, any custom status | Received |
| `in_progress`, `blocked`, `hooked` | Being worked on |
| `closed` | Done |

It runs `bd create|list|show|update --json` in `issues.beads.path` with `BD_NON_INTERACTIVE=1`, labels every
report with `issues.beads.label`, lists only items with that label, and copies attachments to
`.beads/attachments/<id>/` next to the database, noting their path on the item.

## Heinzel's Tracker contract

`BeadsBoard` implements core's `Tracker` protocol (ADR 0141) over the same database: `issues_updated`, `create`,
`claim`, `transition`, `note`, `attach` and `close`. A project is a Beads label. Every write runs
`bd ... --actor <actor>`; `claim` is Beads' atomic `--claim` and refuses an item another actor holds. `hz issues
submit` writes through it; listing and the watch read through the connector above. Issues registers no capability
adapter, so it never changes which tracker other plugins are bound to.
