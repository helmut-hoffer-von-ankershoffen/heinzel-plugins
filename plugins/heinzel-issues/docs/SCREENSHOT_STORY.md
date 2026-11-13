## Audience

Someone deciding whether Issues gives them a simple way to report a problem and follow it through to a release. Installation is optional and requires a writable tracker; the built-in Beads setup currently needs a writable Beads database (`README.md`, `pyproject.toml`, `[tool.heinzel.catalog]`).

## Outcome

Show a fictional report progressing from Received to Being worked on to a named release, with a quick view of outstanding work on Today and a useful terminal listing. The viewer should understand both the benefit and the setup prerequisite without mistaking the demonstration for a live tracker.

## Scenes

1. **Issues, light:** The genuine Issues panel shows three fictional reports in different states, including one released in 0.9.27, alongside the report form. This is the main reason to install: a plain-language view from submission to release. The fixture disables sending, so the image must not imply a successful submission.
2. **Today, dark:** The genuine Today widget shows the two fictional open reports; the completed report is absent. This demonstrates a second useful surface and an applied dark appearance.
3. **CLI list:** The real `hz issues list` result presents the same fictional reports and their states as a terminal table. It complements the app views rather than substituting for them.

The existing `docs/screenshots.toml` already expresses this story, so the plan below preserves it. If capture shows that a declared surface or appearance did not actually render, repair the evidence or plan before publication; do not substitute a terminal image for either UI scene.

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap and `browser_time` in the plan. Its in-memory tracker supplies three fictional tasks, and its temporary local release clone supplies the fictional 0.9.27 release. It does not use a real Beads database. The fixture raises `Sending is off in this demonstration` for its tracker submission; do not claim the capture proves a successful send or notification. The bootstrap runs only during an explicit capture.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript. Also inspect paths, account names, terminal history, notifications, report text, tracker details and any other incidental Core chrome; use only the fictional profile and fixture data. Do not mask an unknown identity by assuming it belongs to either mapping.

## Source-bound UI surface inventory

- **Plugin entrypoint and panel:** `pyproject.toml`, `[project.entry-points."heinzel.modules"]`, declares `issues = "heinzel_issues"`. `src/heinzel_issues/__init__.py` declares `module.nav`, `module.action` and `module.view(name="requests", source="list")`; `src/heinzel_issues/_service.py`, `ROUTE`, supplies `/?panel=issues:requests`. `src/heinzel_issues/views/index.js` implements the real list, status marks, composer, setup state and older-SDK terminal fallback.
- **Core-rendered feature UI:** `src/heinzel_issues/__init__.py`, `today`, contributes a `ListWidget` on Today with navigation to the Issues route. The same file's `submit` operation is private and writable, and its view declares `RunOperation` for Send; `views/index.js` says Core presents confirmation. A confirmation is a real flow surface, but the supplied fixture does not establish a successful submission and the plan does not capture it.
- **Other Core contributions:** `__init__.py` declares `list`, `submit` and `show` operations, a five-minute `watch` job, a `tracking` health check and optional `setup`. These can yield Core operation, notification, Doctor and setup surfaces; their precise Core rendering and routes are not declared in the supplied files, so they remain unverified rather than being invented. No channel, info or footer contribution is declared in the supplied module. The README documents notices and Doctor behavior, but this plan does not claim to capture either.
- **CLI and external systems:** `__init__.py`, `_render` and `_render_one`, provide terminal renderers for operations; `README.md` documents `hz issues list`, `show` and `submit`. The CLI scene is genuinely terminal output. `docs/CONTRACT.md` describes connector entrypoints, while `_beads.py` invokes the local `bd` program and `_releases.py` reads local git clones; no external provider UI is declared or depicted.
- **Evidence boundary:** The README says the app asks before sending and that older Heinzel versions use an app-terminal fallback; `views/index.js` makes the fallback conditional on the SDK exposing `submit`. The installed Core version and actual confirmation rendering must be checked during capture. The fixture's `Demo.submit` refuses sending, while the Beads path in `__init__.py` also constructs `BeadsBoard`; therefore a successful or safely refused submission must not be inferred from the fixture alone. No capture has been run for this response.

## Acceptance criteria

- Capture the actual panel, Today widget and CLI result using the existing bootstrap; verify the three fictional states and the fictional release against the fixture. The Today capture must show only open reports.
- Verify that light and dark appearances are actually applied and that both UI images show useful feature content. Reject duplicate images, caption-only differences, terminal output presented as feature UI, forged HTML and invented screens.
- Keep captions explicit that the reports are fictional. Do not present the fixture as evidence of real submissions, live tracker health or delivered notices.
- Independently inspect every image and transcript for privacy, including the narrowly permitted presentation mappings above. Unknown identities fail review.
- The TOML below was checked against the requested fields and the supplied declarations by inspection; no parser, application, fixture or capture was executed.
