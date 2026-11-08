## Audience and outcome

For someone deciding whether Issues will help them report a problem and follow its progress without learning a tracker. The story shows the full fictional report list, the open items on Today, and the same plain-language results in the CLI. It also makes clear that the demo does not prove sending works.

## Scenes

1. **Issues page, light:** Three fictional reports show Received, Being worked on, and a fix released in 0.9.27. The composer shows where another report would begin. The real view and its accessible list are declared in `src/heinzel_issues/__init__.py` (`module.view`) and implemented in `src/heinzel_issues/views/index.js` (`Issues`, `Item`, `Composer`).
2. **Today, dark:** The two open fictional reports appear in the Core-rendered Today widget, offering a quick way back to Issues. The completed report is excluded by `today` in `src/heinzel_issues/__init__.py`.
3. **CLI list:** `hz issues list` presents the same fictional reports with status and sent date. The `list` operation and `_render` table are declared in `src/heinzel_issues/__init__.py`.

These are different feature surfaces, not duplicate captures. Light and dark must be visibly applied. The existing plan already demonstrates these useful behaviors, so it is retained.

## Fictional fixtures

`docs/screenshot_fixture.py` supplies three in-memory tasks and builds a temporary fictional release clone with a fix tagged 0.9.27 on 7 Nov 2026. It selects the demo connector and runs Heinzel only during explicit capture; `docs/SCREENSHOTS.md` says no Beads database is touched. The demo connector refuses `submit`, and the Beads capability used by the declared submit operation is a separate write path. Do not send a report or claim a successful submission from this fixture.

## Source-bound UI surface inventory

- **Plugin feature UI:** `pyproject.toml` registers `issues = "heinzel_issues"` in `heinzel.modules`. In `src/heinzel_issues/__init__.py`, the Issues navigation and `requests` action navigate to `ROUTE`, defined as `/?panel=issues:requests` in `src/heinzel_issues/_service.py`. The `requests` view consumes `list`, exposes setup, send and legacy report actions, and refreshes every 60 seconds. `src/heinzel_issues/views/index.js` implements loading, unavailable, not-set-up, empty, list and composer states. The composer uses Core's operation confirmation when `submit` exists; older SDKs offer a terminal-opening fallback. The installed Core version and confirmation rendering are not verified by these source files.
- **Core-rendered feature UI:** `today` contributes a `ListWidget` of up to eight open reports with navigation to the Issues panel. `watch` can emit Core notices linked to the same route or `hz issues list` (`src/heinzel_issues/__init__.py`, `src/heinzel_issues/_service.py`); the first check only records existing state. The fixture does not establish a notice transition, so no notice is staged.
- **Core operation and setup surfaces:** `list`, private write `submit`, and `show` are operations; the view's send action invokes `submit`, while setup and the older report fallback run commands. `setup(required=False)` provides prompts and confirmation, and `tracking` contributes Doctor health checks (`src/heinzel_issues/__init__.py`). These declarations do not establish a separate plugin page for each operation. The setup and Doctor surfaces are not substitutes for the feature scenes.
- **Terminal results:** The `list` renderer produces a report/status/date table, and `show` and `submit` use `_render_one` (`src/heinzel_issues/__init__.py`). These operations are not described as terminal-only: Core also renders operation-related UI, and the list powers the feature view. Structured CLI details are described in `README.md` and `src/heinzel_issues/_service.py` (`Details`, `Report`).
- **External provider and integrations:** Beads is a local tracker adapter, not an external provider screen supplied here (`src/heinzel_issues/__init__.py`, `src/heinzel_issues/_beads.py`). `src/heinzel_issues/_contract.py` discovers third-party factories under `heinzel_issues.connectors`; `docs/CONTRACT.md` gives a registration example, not another entrypoint declared by this package. No external provider UI is evidenced. No channel, info, or footer contribution is declared in the provided module. The five-minute job and tracker capability are integrations, not evidence of standalone screens.

## Privacy pitfalls

Normal presentation fictionalization is limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail. An independent reviewer must inspect every image and transcript for identities, paths, hostnames, account data, tracker content, and other sensitive material before publication. Fixture isolation is not proof that the surrounding Core UI is private.

## Acceptance criteria

- Capture the actual Issues list and Today widget with the stated fictional data, plus the real CLI result. Do not forge HTML, present terminal output as feature UI, or accept duplicate images or caption-only changes.
- Confirm all three list states and the fictional release, the two open Today items, applied light and dark appearances, and the CLI table against the actual captures. Do not claim the release or dates were verified merely from the plan.
- The composer may be visible, but do not submit or imply successful sending. The fixture does not establish a safe successful write.
- Apply only the disclosed mappings to verified values; preserve the Doctor row's health status and all other detail. Fail on unknown identities and obtain independent review of every image and transcript.
- The TOML below is structurally checked against the supplied format by inspection. Runtime capture, actual theme application, output privacy, and fixture behavior have not been verified; no source was executed.
