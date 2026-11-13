## Audience

A developer or team lead deciding whether GitHub pull requests and issue changes can feed a Heinzelmännchen workflow without building a GitHub integration themselves.

## Outcome

Show a fictional weekly review taking shape: first its place in the workflow collection, then the inputs it declares, then the merged work and issue changes those inputs can return. The workflow is a declaration, not a completed report. The example requester is documentation-only; the installed GitHub adapter performs the conversions over fictional responses (`docs/screenshot_fixture.py`: `CONTRACT`, `DemoGh`, `showcase`, `merged`, and `issues`).

## Scenes

1. **Workflow collection — light.** Find “Weekly code review” among Core's contracts and graph. This establishes where a team can discover the fictional workflow.
2. **Workflow context — dark.** Inspect the same workflow's declared merged-work and issue inputs, its goal and its expected notes. This is a distinct, useful state of the Core workflow UI; it does not claim a report was generated.
3. **Merged work — light app terminal.** Run the fixture-only `showcase merged acme/widgets` requester and inspect fictional merged pull requests and authors. This is terminal output inside the app, not a feature UI.
4. **Issue changes — dark app terminal.** Run `showcase issues acme/widgets` and inspect fictional issue titles, states and owners. This is a different result, not a second view of the same table.
5. **Merged work — shell.** Show the same useful capability through a native CLI result, identifying the requester and data as fictional.
6. **Issue changes as JSON — shell.** Show the other fixture operation in machine-readable form for scripts and agents.

The two workflow scenes are genuine Core feature UI scenes; the two app-terminal scenes supplement them. The existing plan already demonstrates useful behavior and is preserved. Its `/contracts/weekly-code-review` detail route and its exact rendered contents are evidenced by the existing plan, not by Core implementation supplied here; capture must verify that route and the intended contents before acceptance (`docs/screenshots.toml`, `docs/screenshot_fixture.py`).

## Fictional fixtures

The existing `docs/screenshot_fixture.py` creates an isolated local demonstration contract, binds both capabilities to GitHub, injects `DemoGh`, and supplies fictional `acme/widgets` pull requests and issues for October 2026. The fake requester operations are not shipped GitHub plugin commands. The fixture's asserted login and executable are demonstration values, not evidence of a real connection. Its contract declares inputs and output but explicitly says no report has been generated. No new fixture file is assumed.

## Source-bound UI surface inventory

- **Plugin entrypoints:** `pyproject.toml` declares `heinzel.modules` and `heinzel.connected_sources`, both targeting `heinzel_github`. `src/heinzel_github/_module.py` declares the `github` module; `src/heinzel_github/__init__.py` registers settings, services, a read-only skill, the `code-host` and `tracker` read adapters, `info`, system info, offline health and live health. No plugin Page, View, navigation, channel, approval, setup or footer contribution is declared in the supplied plugin source. That absence alone does not establish that there is no feature UI.
- **Core feature UI:** The supplied fixture declares a responsibility with two capability inputs and a notes output; the existing plan identifies the Core contracts collection and detail views (`docs/screenshot_fixture.py`: `CONTRACT`; `docs/screenshots.toml`: `workflow-collection`, `workflow-context`). These are Core-rendered workflow surfaces, not GitHub-owned screens. The exact detail route and rendering remain capture-time evidence to verify.
- **Core connection and diagnostics surfaces:** `README.md` identifies Settings → Connectors as a Core UI for connection status; `src/heinzel_github/__init__.py` and `_service.py` contribute offline and live health checks, including binding details. The supplied sources do not establish the precise route or controls for capturing these surfaces, so the plan does not invent them. Live testing asks GitHub and is not part of this offline story.
- **Operations and info:** `@module.operation info` and `@module.info system_info` expose plugin and host details (`src/heinzel_github/__init__.py`, `_service.py`: `about`). Core may render contributions beyond a terminal; the supplied source does not establish a specific operation or info UI route. The fixture's `showcase` operations and their Rich table renderers are separately declared in `docs/screenshot_fixture.py`.
- **Release feed:** Conditional registration of `GithubReleaseFeeds` depends on Core support and an active captured source (`src/heinzel_github/__init__.py`; `src/heinzel_github/_release_feed.py`: `GithubReleaseFeeds`). `README.md` describes its use in a draft workflow, but the supplied evidence does not establish a capturable UI or an offline release-feed fixture. Do not imply this gallery demonstrates it.
- **External provider UI:** GitHub and `gh` own authentication (`README.md`, `src/heinzel_github/_gh.py`); no GitHub website or login screen is proposed. `README.md` describes capability use from CLI, MCP and REST, but does not establish separate plugin screens for them.
- **Terminal output:** The fixture declares two requester operations and table renderers; the plan also requests JSON for issues. These are useful terminal results, not proof that the adapter is CLI-only (`docs/screenshot_fixture.py`; `docs/screenshots.toml`).

## Privacy pitfalls

Use only the isolated fictional profile and fixture data during capture. Check every image and transcript for real account names, hostnames, paths, tokens, repository names, links, browser chrome and other identifying material; unknown identities fail review. Normal presentation fictionalization is explicitly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Independent review must inspect every image and transcript. Do not replace other values on the assumption that they are safe.

## Acceptance criteria

- Capture the existing six distinct scenes with the actual Core UI and terminal output; no forged HTML, duplicate captures or caption-only differences. Both workflow views must be useful and readable, and the collection and detail must actually show the fictional workflow and its declared inputs.
- Apply light and dark appearances as specified and verify their rendered appearance. Confirm that the CLI and app-terminal results show the fixture's relevant pull requests and issues, and that JSON is valid and useful. Terminal actions already wait for completion; do not add waits for individual table cells.
- Captions identify demo data and the fixture-only requester where relevant. Do not describe the declared workflow as an executed report, the mock login as a real account, or terminal output as a plugin feature screen.
- Verify the detail route and accessible heading during capture. If Core does not render the claimed detail or the route fails, do not substitute an invented screen; resolve the evidence and revise the plan.
- Review all images and transcripts independently for privacy and truthful representation before publication. The plan has been checked against the requested TOML structure by inspection only; no parser, capture, project code or network call was run.
