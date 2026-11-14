## Audience and outcome

A developer or team lead considering the GitHub connector can see how a fictional weekly review brings merged pull requests and changed issues into a Core workflow, then inspect the underlying results. The gallery demonstrates read capability through an offline fixture; it does not claim to show a generated review or a live GitHub connection.

## Scenes

1. **Workflow collection — light:** The Core contracts list and graph introduce the fictional Weekly code review and its place in a workflow.
2. **Workflow context — dark:** The same fictional workflow’s detail shows its merged-work and issue inputs. It declares a workflow; no report was generated. These two scenes show different useful states of a Core feature, not two captions on the same capture.
3. **Merged work:** The native app terminal shows fictional merged pull requests, dates and authors through the real adapter and the fixture-only requester.
4. **Issue changes:** The native app terminal shows fictional issue titles, states and owners through the same adapter. These terminal captures are labeled as terminal results, not feature UI.
5. **Merged CLI:** A shell result shows the fictional merged-work table.
6. **Issues JSON:** A shell result shows fictional issue data in JSON for a script or agent.

The existing plan already covers these useful behaviors and is preserved. The two terminal cases are different fixture operations, rather than two parameters of one operation. `docs/screenshot_fixture.py` supplies the existing bootstrap, the fictional `acme/widgets` records, the October window, the local contract, and the `showcase.merged` and `showcase.issues` operations. Its `DemoGh` returns fictional responses while the real adapter converts them. These showcase commands are documentation fixtures, not commands supplied by the installed plugin.

## Source-bound UI surface inventory

- **Core feature UI:** `docs/screenshot_fixture.py` writes the Weekly code review contract with `code-host:read` and `tracker:read` inputs. The existing `docs/screenshots.toml` declares `/contracts` and `/contracts/weekly-code-review` captures. The collection route is a known Core route; the detail route and its heading are evidenced by the existing plan, but their actual rendering remains unverified from the provided source. Capture must confirm both scenes are genuinely useful and distinct.
- **Core connector/setup UI:** `README.md`, “Is it connected?”, explicitly identifies Settings → Connectors as a surface for login status. `src/heinzel_github/__init__.py` declares settings, offline `@module.health`, and on-demand `@module.health(live=True)`; `src/heinzel_github/_service.py` defines their checks. This is real Core-rendered setup UI, but the supplied fixture and plan do not establish a safe, useful capture of it. The live test asks GitHub and is outside this offline story.
- **Core operation and information surfaces:** `src/heinzel_github/__init__.py` declares `@module.operation` `info`, `@module.info` `system_info`, and read-only `module.provides` registrations for `code-host` and `tracker`. `src/heinzel_github/_models.py` defines the information and settings fields. The supplied files do not establish a dedicated feature view or route for those contributions; they must not be assumed terminal-only merely because a Page or View is absent. The fixture’s rendered operations do support the explicitly labeled app-terminal results.
- **External provider UI:** GitHub and `gh auth login` belong to the external provider, not a plugin screen (`README.md`, “Set up”). No external-provider screen is proposed.
- **Other entry point and conditional service:** `pyproject.toml` declares both `heinzel.modules` and `heinzel.connected_sources` as `github = "heinzel_github"`. The actual module declarations are in `src/heinzel_github/__init__.py`; conditional `GithubReleaseFeeds` registration depends on Core support and captured-source activation. `src/heinzel_github/_release_feed.py` declares `supported_operations = {"release-feed"}` and its lease behavior. The README describes a draft-workflow release feed, but the supplied sources do not establish its rendered route or an offline fixture for it. Do not invent a screen or claim the gallery demonstrates that feed.
- **Remaining contributions:** The inspected module declarations include a skill (`src/heinzel_github/skills/review-pull-request/SKILL.md`) and services, but no declared navigation, channel, approval, footer, Page or View contribution. This does not rule out generic Core rendering; the Core implementation is not among the provided files.

## Fictional fixtures and privacy

The repository, people, pull requests, issues and contract are demonstration data from `docs/screenshot_fixture.py`. Fixture login and version values simulate `gh`; they do not establish a real connection. Normal presentation fictionalization maps verified owning-interpreter paths to `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row to `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and an independent reviewer must inspect every image and transcript. Check paths, hostnames, accounts, tokens, URLs and incidental UI content; do not assume the fixture makes the entire capture private.

## Acceptance criteria

- Capture the existing isolated bootstrap only during explicit capture; make no network requests. Confirm the two contracts scenes render the stated, distinct feature states in applied light and dark appearances. If the detail route or heading fails, report the unresolved evidence instead of fabricating a replacement.
- Confirm both app-terminal results and both CLI results contain the expected fictional records, with pull requests excluded from the issue result. Clearly identify the requester and data as fictional; do not imply a generated report, live GitHub response, or production `showcase` command.
- Reject duplicate captures, caption-only differences, terminal output presented as feature UI, and forged HTML. Review the contact sheet and each image and transcript independently for truthfulness and privacy before publication.
- The TOML below has been checked against the requested structure by inspection; capture behavior and actual UI rendering have not been executed or verified.
