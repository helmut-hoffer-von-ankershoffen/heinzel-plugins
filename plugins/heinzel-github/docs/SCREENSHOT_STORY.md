## Audience

A developer or workflow author deciding whether GitHub pull requests and issues can supply a useful Heinzelmännchen review workflow without building a GitHub-specific integration into that workflow.

## Outcome

Show a fictional weekly review taking shape: a Core workflow declares the two inputs, then the actual GitHub adapter converts fictional vendor responses into merged-work and issue results. The workflow is a declaration, not a generated report. The example requester is documentation-only, so its `showcase` commands must not be presented as commands installed by the GitHub plugin.

## Scenes

1. **Workflow collection, light.** The Core contracts collection places “Weekly code review” in context. Its fictional contract requires both read capabilities and names the two inputs.
2. **Workflow context, dark.** The same actual Core workflow shows the input declarations and goal in more detail. This is a distinct useful state, not a second caption on the collection. The existing plan supplies `/contracts/weekly-code-review`, but the provided source does not independently establish that detail route; capture must verify it resolves to the genuine Core view. If it does not, use a verified interaction from `/contracts` to reach the detail, rather than inventing a route or screen.
3. **Merged work, light.** The app terminal runs the fixture requester through the real adapter and displays fictional pull requests, dates and authors. This is a terminal result inside the app, not a feature UI scene.
4. **Issue changes, dark.** The app terminal shows a different fictional result: issue titles, states and owners. It is also a terminal result, and must not be counted as feature UI.
5. **Merged work in the CLI.** A native shell result demonstrates the same fixture requester for a person using the command line.
6. **Issues as JSON.** A native CLI result illustrates structured fictional issue data for scripts and agents.

The two Core workflow views are the genuine feature UI scenes; the terminal scenes supply complementary adapter results. Light and dark appearances must actually be applied and visible.

## Fictional fixtures

`docs/screenshot_fixture.py` creates the local `weekly-code-review` contract in the isolated state directory, binds `code-host` and `tracker` to GitHub, and supplies `DemoGh` responses for `acme/widgets`. Its documentation-only `showcase.merged` and `showcase.issues` operations use the real adapter with the fixed October 2026 window. The fictional people, repository, links, pull requests and issues are examples, not evidence of a real account or live GitHub access. The fixture deliberately includes a pull-request-shaped issue; the adapter excludes pull requests from issue results (`src/heinzel_github/_adapter.py`, `issues_updated`). Do not claim the workflow ran or produced its `notes` output.

## Source-bound UI surface inventory

- `pyproject.toml` declares both `heinzel.modules` and `heinzel.connected_sources` entry points as `github = "heinzel_github"`. Their shared target is `src/heinzel_github/__init__.py`; the second entry point must not be assumed to declare a separate page.
- `src/heinzel_github/_module.py` declares `Module("github", ...)`. `src/heinzel_github/__init__.py` registers settings, services, a skill, read providers for `code-host` and `tracker`, the `info` operation, a system-info contribution, offline health and live health. These are real Core integration surfaces even though this plugin declares no Page, View, navigation, channel, approval, setup or footer contribution in the provided source. Absence of a Page or View alone would not establish terminal-only behavior.
- The `info` operation and `module.info` contribution expose plugin, version, Core version, host and executable details (`src/heinzel_github/_service.py`, `about`); `module.health` contributes Doctor/connector status, while `module.health(live=True)` performs the on-demand connector test. `README.md` identifies Settings → Connectors as a Core-rendered UI and describes the CLI counterparts. The provided files do not establish a direct route or the exact Core rendering of every contribution. Do not manufacture one.
- The Core contracts collection and detail are workflow feature UI, populated by the fixture contract; they are not GitHub-owned screens. The fixture's `showcase` operations render tables in the app terminal and CLI. Their terminal output is not feature UI. The adapter's capability methods are programmatic reads, not separately declared plugin CLI operations (`src/heinzel_github/_adapter.py`; `docs/screenshot_fixture.py`).
- GitHub and `gh` are external provider surfaces. No GitHub website or provider screen is needed here. The optional `GithubReleaseFeeds` service is registered only under the captured-source condition (`src/heinzel_github/__init__.py`, `src/heinzel_github/_release_feed.py`); the README describes its draft-workflow use, but the provided fixture does not demonstrate that flow. Do not invent a release-feed screen or claim it was exercised.
- The existing plan and catalog describe the workflow collection and detail (`docs/screenshots.toml`, `pyproject.toml`). They are evidence of intended capture, not proof that the current Core route renders successfully. Resolve that uncertainty during capture and review.

## Privacy pitfalls

Use the isolated fixture and inspect every image and transcript for real account names, repository names, hostnames, paths, tokens, incidental data and browser or terminal chrome. Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail, and independent review must inspect every image and transcript. Do not substitute fictional status, redact away an unexplained identity, or treat fixture isolation as proof of privacy.

## Acceptance criteria

- Capture genuine Core UI with applied light and dark appearances: the collection and a distinct useful detail state of the fictional weekly review. Verify the existing detail route or reach it by a verified Core interaction.
- Show the fixture's merged pull requests and issue changes as genuine terminal output, plus a useful CLI result and JSON case. Clearly label demo data and the fixture-only requester; do not imply its commands are shipped plugin operations.
- Preserve real SDK statuses and details under the narrowly defined presentation mappings. Independently inspect every image and transcript; any unknown identity fails review.
- Confirm screenshots are distinct, legible and consistent with the fictional source data. Reject duplicates, caption-only changes, terminal output represented as feature UI, forged HTML, invented product screens, and claims that a report or live GitHub read occurred.
- The plan is structurally checked against the requested format and retains the existing six scenes and local bootstrap. Runtime rendering, route availability, applied themes and privacy acceptance remain to be verified during explicit capture; no code, imports or network calls were run for this proposal.
