## Audience and outcome

A developer or team lead considering a GitHub connector should see how a local workflow can declare both merged pull requests and updated issues as inputs, and what those reads return. The story should make clear that the example is fictional, the workflow is only declared, and no review report has been generated.

## Scenes

1. **Workflow collection, light:** Find the fictional Weekly code review alongside local workflows. This establishes where the example is discovered.
2. **Workflow context, dark:** Inspect the same workflow’s distinct detail state: its two capability inputs, repository, and intended output. It is a declaration, not a completed review.
3. **Merged work, app terminal:** Show the fictional merged pull requests returned by the real adapter through the fixture-only requester.
4. **Issue changes, app terminal:** Show fictional issue titles, states, and owners; the adapter excludes pull requests from issue results.
5. **Merged work, CLI:** Show the same useful read in a native terminal, identifying the requester as demonstration-only.
6. **Issues as JSON, CLI:** Show a different capability and output format for scripts, with fictional data.

The first two are Core feature UI scenes with different purposes; the app-terminal scenes are terminal results within the app, not feature UI. The existing plan already expresses this story and is preserved below. Its routes and rendered results still require capture-time verification.

## Fictional fixtures

`docs/screenshot_fixture.py` creates the local Weekly code review contract in isolated state, binds both capabilities to GitHub, and supplies `DemoGh` responses for `acme/widgets`. Its `showcase.merged` and `showcase.issues` operations use the real adapter with October 2026 fixture responses. The names, repository, accounts, PRs, issues, and links are example data; they are not evidence of a real GitHub connection. The fixture’s fixed window and `browser_time` make the story coherent. Some raw fixture records reuse an API URL or ID despite differing displayed numbers; do not present those raw fields as consistent production records.

## Source-bound UI surface inventory

- `pyproject.toml` declares both `heinzel.modules` and `heinzel.connected_sources` entrypoints as `github = "heinzel_github"`. Their target, `src/heinzel_github/__init__.py`, configures the module, settings, services, skill, two read capability providers, `info` operation, system-info contribution, and offline and live health contributions. The connected-source entrypoint points to that same package; the supplied source does not independently establish a separate connector screen or its exact rendering.
- `src/heinzel_github/_module.py` declares the GitHub module. `src/heinzel_github/_adapter.py` implements merged pull-request and updated-issue reads. No plugin-specific Page, View, navigation, channel, approval, setup, or footer declaration appears in the supplied plugin source. That absence alone does not rule out Core-rendered UI.
- `README.md` explicitly describes Core Settings → Connectors, connector list/test, system capability list, system info, and doctor. `src/heinzel_github/__init__.py` and `_service.py` provide the info and health data those generic surfaces may render; exact routes and visual controls are not established by these sources. The live test contacts GitHub when explicitly run, so it is outside this offline fixture story.
- `docs/screenshot_fixture.py` contributes the fictional workflow and two fixture-only operations. `docs/screenshots.toml` declares `/contracts` and `/contracts/weekly-code-review` for collection and detail captures. These are Core workflow surfaces, not GitHub-owned screens; the provided plan is evidence of the intended detail route, not proof that it currently renders. If capture cannot verify it, do not substitute invented HTML or an assumed route.
- `src/heinzel_github/__init__.py` conditionally registers `GithubReleaseFeeds` from `src/heinzel_github/_release_feed.py`; `README.md` describes its draft-workflow release-feed use. The supplied fixture does not demonstrate that flow or establish its UI, so no release-feed screenshot is claimed.
- GitHub and `gh auth login` are external provider tools. The app-terminal and native CLI outputs are terminal surfaces. The `review-pull-request` skill declared in `src/heinzel_github/skills/review-pull-request/SKILL.md` is agent guidance, not an evidenced product screen. The existence of the `info` CLI operation does not prove it is terminal-only.

## Privacy pitfalls

Normal presentation fictionalization is limited to these explicit mappings: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and an independent reviewer must inspect every image and transcript. Review account names, paths, hostnames, URLs, environment-derived details, tokens, logs, browser chrome, and unrelated background content; fixture labels alone do not establish privacy. Do not run the live connector test during this offline story.

## Acceptance criteria

- Capture the two genuine Core workflow states in applied light and dark appearances, plus the distinct app-terminal and native CLI results. Verify actual routes, headings, and data during capture; do not treat this source review as a successful capture.
- The collection and detail must show meaningfully different states. Reject duplicate images, caption-only changes, terminal output represented as feature UI, and forged HTML.
- Verify the merged results and issue results against the fixture and adapter, including exclusion of the PR-shaped issue; show JSON only if it is the actual CLI output. Clearly label the fixture-only requester and fictional data.
- Do not imply that the declared workflow ran, that a report exists, or that the fixture proves a live GitHub login or production health.
- Inspect every image and transcript independently for privacy and truthful presentation before publication. Only the narrowly specified path and Doctor-host mappings are permitted; unknown identities fail review.
- The TOML below was checked against the requested structure by inspection only. No parser, fixture, application, capture, network call, or source code was executed, so runtime route, theme, and output validation remains outstanding.
