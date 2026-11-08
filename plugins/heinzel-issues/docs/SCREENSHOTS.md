# Screenshot gallery

From the collection root, run `make screenshots NAME=heinzel-issues OPEN=1`.
Review the [contact sheet](assets/screenshots/index.html) before committing.
The [scene plan](screenshots.toml) describes the real UI and CLI captures.
`make screenshots-check NAME=heinzel-issues` verifies freshness offline.

Captures use a temporary fictional profile without connected accounts and an in-memory tracker with three
fictional reports (`screenshot_fixture.py`); no Beads database is read or written.
See the [author guide](../../../docs/SCREENSHOT_AUTHORING.md) for human and agent commands.
