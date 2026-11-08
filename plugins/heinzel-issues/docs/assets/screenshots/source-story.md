## Audience

Someone considering Issues who wants a simple way to report a problem and follow it through to a release, and a maintainer deciding whether they can provide a writable Beads database.

## Outcome

Show the reassuring journey from “received” to “being worked on” to a named release, with open items also visible on Today. Make the prerequisite clear: the plugin is optional and needs a writable tracker; the built-in connector uses Beads (`README.md`, “Set it up” and “Trackers”).

## Scenes

1. **Issues, light:** The genuine Issues panel shows three fictional reports in different states, including the release that shipped the finished one, alongside the report composer. The view and its list are declared in `src/heinzel_issues/__init__.py` (`module.view`, source `list`) and rendered by `src/heinzel_issues/views/index.js`. Do not imply that the fixture can successfully send a report.
2. **Today, dark:** The real Core Today widget shows the two open fictional reports and their plain-language states; the completed report is absent. `src/heinzel_issues/__init__.py` declares `@module.widget(source="list")` and filters out done items. This is a distinct useful surface, not a recoloring of the first capture.
3. **CLI:** `hz issues list` renders the same fictional reports in a real terminal table with report, status, and sent date (`src/heinzel_issues/__init__.py`, `list_` and `_render`).

The existing `docs/screenshots.toml` already tells this useful story, so the plan is preserved. The appearance fields request light and dark; capture review must verify that each appearance was actually applied.

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap only during explicit capture. It supplies three in-memory fictional tasks and creates a temporary local release clone whose fictional fix is released in 0.9.27 on 7 Nov 2026. It does not read or write a Beads database. Its `Demo.submit` refuses sending; additionally, the Beads submit operation constructs a `BeadsBoard`, so neither a successful submission nor a particular refusal path is established by this fixture. Do not stage a success or claim that the composer was exercised end to end.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited to these mappings: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript. Also inspect terminal prompts, paths, account names, tracker details, notifications, and any incidental Core UI; do not publish captures that reveal real data. The fictional tracker IDs and release are example data, not evidence of a real deployment.

## Source-bound UI surface inventory

- `pyproject.toml` declares the sole installed module entry point, `heinzel.modules: issues = "heinzel_issues"`; its actual declarations are in `src/heinzel_issues/__init__.py`. `src/heinzel_issues/_contract.py` defines the separate `heinzel_issues.connectors` discovery group; `docs/CONTRACT.md` gives a hypothetical third-party registration, not an additional installed entry point here.
- **Plugin feature UI:** `module.nav` and `module.action` navigate to `ROUTE`, defined as `/?panel=issues:requests` in `src/heinzel_issues/_service.py`. `module.view(name="requests", source="list")` supplies the genuine panel. `src/heinzel_issues/views/index.js` renders loading, unavailable, setup, empty and populated states, plus the composer or older-SDK terminal fallback. The fixture supports the populated state.
- **Core-rendered feature UI:** `@module.widget(source="list")` contributes open reports to Today at `/`. `RunOperation(operation="submit", inputs=("text",))` supplies a Core confirmation flow before sending; cancellation preserves text according to the view implementation. The setup and older-SDK report actions use `RunCommand`, opening command flows in the app terminal. Exact Core dialog and terminal presentation is not supplied here and must be observed, not invented.
- **Other Core contributions:** `@module.health` provides the tracker Doctor check, and `@module.setup(required=False)` provides the setup flow. `@module.job` schedules the watch every five minutes; `src/heinzel_issues/_service.py` emits local plugin notices with an Issues route and CLI command when changes are found. Settings are declared through `module.settings(IssuesSettings)`. These declarations do not establish a separate plugin page, channel, footer, or info contribution; no such declarations are present in the supplied module. Core may render generic surfaces for declared contributions, but their exact appearance is unresolved in the supplied sources.
- **Terminal output:** `list`, `submit`, and `show` are actual operations declared in `src/heinzel_issues/__init__.py`; the list table is a useful CLI result, not a substitute for feature UI. `README.md` documents `list --json` and `show <id>` for details. External provider UI is neither declared nor needed for these captures; the Beads connector invokes local `bd` commands (`src/heinzel_issues/_beads.py`, `docs/CONTRACT.md`).
- **Evidence tension:** `README.md` describes an older-than-0.9.30 fallback, while `pyproject.toml` requires `heinzel>=0.9.31,<0.10`; the fallback remains in the view source but is not evidence that such an older Core is supported by this package. No Core source or capture result was supplied to verify generic surface appearance or actual theme application.

## Acceptance criteria

- Capture the real panel, real Today widget, and real CLI output using the existing fixture; show all three fictional statuses and the fictional release in the panel and CLI, and only the two open items on Today.
- Verify applied light and dark appearances and legible status words and marks. Keep the scene captions explicit that the data is fictional.
- Do not publish duplicate captures, caption-only variations, terminal output labeled as feature UI, forged HTML, or an unsupported submission-success claim.
- Independently inspect every image and transcript for privacy and truthful status, including Doctor if visible. Apply only the stated verified presentation mappings; unknown identities fail review.
- The TOML below was checked against the requested structure by inspection. No parser, capture, plugin code, or network operation was run, so runtime validity and screenshot results remain to be verified.
