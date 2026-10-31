# Screenshot gallery

From the collection root, run `make screenshots NAME=heinzel-github OPEN=1`.
Review the [contact sheet](assets/screenshots/index.html) before committing.
The [scene plan](screenshots.toml) describes the real UI and CLI captures.
`make screenshots-check NAME=heinzel-github` verifies freshness offline.

Captures use a temporary fictional profile without connected accounts. The generated
[manifest](assets/screenshots/capture.json) records the SDK version and input/image digests.
See the [author guide](../../../docs/SCREENSHOT_AUTHORING.md) for human and agent commands.
