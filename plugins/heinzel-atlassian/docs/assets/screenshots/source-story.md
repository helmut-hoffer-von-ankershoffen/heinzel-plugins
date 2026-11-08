## Audience

People considering an Atlassian connector for a Heinzel workflow who want to see what Jira and Confluence data can contribute before configuring their own account.

## Outcome

Show a fictional weekly review as a local contract, then show the issue data and plan that its inputs can read. The contract declares a workflow; the captures must not imply that a review ran or a report was generated. The CLI results use real adapter code with a fixture-only requester and fictional vendor responses, not a connected Atlassian account.

## Scenes

1. **Find the review — light UI.** The Core contracts inventory places the fictional Weekly work review among local contracts. This establishes where a user finds the workflow.
2. **Understand its inputs — dark UI.** The review detail shows the goal and the declared tracker and documents inputs. This is a meaningful second state of the contract flow; it does not claim to display a generated report.
3. **Inspect Jira changes — CLI.** The fixture’s `showcase issues WID --json` returns structured fictional issue changes through the Jira adapter.
4. **Read the plan — CLI.** The fixture’s `showcase page` returns the fictional Confluence plan, source and revision through the documents adapter.

These preserve the existing plan’s useful behavior. The two CLI scenes exercise different fixture operations, so a second parameter case for a single CLI operation is not needed. Light and dark appearances are requested for the two UI scenes and must be verified as actually applied.

## Fictional fixtures

`docs/screenshot_fixture.py` creates the local review contract, binds `tracker` and `documents` to Atlassian, and supplies `DemoAcli` responses for WID issues and the Widget plan. Its `showcase.issues` and `showcase.page` are documentation-only requesters; they are not shipped Atlassian operations. The fixture supplies a fictional site, people, issue keys and page. Its isolated bootstrap runs only during explicit capture.

## Source-bound UI surface inventory

- **Entrypoint and adapters:** `pyproject.toml` declares `heinzel.modules` entrypoint `atlassian = "heinzel_atlassian"`; `src/heinzel_atlassian/_module.py` declares the module and `src/heinzel_atlassian/__init__.py` registers settings, services, and the `tracker:read` and `documents:read` providers. There is no declared plugin navigation or plugin-owned Page/View in these files; that alone does not establish that Core has no feature UI.
- **Core feature UI:** `docs/screenshot_fixture.py` declares the local Weekly work review contract and its inputs. `docs/screenshots.toml` already targets the Core `/contracts` inventory and `/contracts/weekly-work-review` detail. The supplied source does not include Core’s route declarations, so the detail route and rendered contents remain capture-time evidence to verify, not independently established here. These are Core workflow views, not Jira or Confluence screens or proof that the workflow executed.
- **Core connector and diagnostic surfaces:** `README.md` describes Settings → Connectors and a connector page; `src/heinzel_atlassian/__init__.py` declares public `info` and `status`, `@module.info`, ordinary health and live health contributions. `src/heinzel_atlassian/_status.py` describes state, identity, site, cause, command and refresh for a connector page. The provided files do not establish a connector route or fixture-backed authentication status suitable for a capture. Doctor checks and live connector tests are distinct: the former does not establish a successful login or read.
- **Operations, approvals and channels:** `src/heinzel_atlassian/__init__.py` declares private everyday `assigned`, `epics`, `watch` and three draft operations; only the three applying writes explicitly declare `heads={"cli"}`. `src/heinzel_atlassian/_work.py` and `_drafts.py` expose notice and approval fields, but `README.md` says the plugin imports no channel and released Core has no generic approval contract for private plugin operations. Do not invent a notice, approval screen, or CLI-only restriction for the read and draft operations. No plugin setup, footer, channel or navigation contribution is declared in the supplied module registration.
- **External provider UI:** Atlassian’s browser login and Jira/Confluence interfaces are external surfaces described in `README.md`, not plugin screens. Do not capture them as a plugin feature.
- **Terminal results:** `docs/screenshot_fixture.py` declares `showcase.issues` and `showcase.page` and their CLI renderers; the plan labels both captures `cli`. Their presence does not establish that all adapter or operation behavior is terminal-only.
- **Unresolved source evidence:** `README.md` says Jira shapes were checked against signed-in acli 1.3.39, while its Known gaps section says the JSON shapes have not yet been verified against signed-in acli. It also says Confluence samples have not been checked live. Treat the fixture as a demonstration, not proof of current live compatibility.

## Privacy pitfalls

Use only the fictional fixture profile and inspect every image and transcript independently for account names, credentials, hostnames, paths, personal content and unexpected real data. Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail and independent review must inspect every image/transcript. Do not fabricate a Doctor row or use the mappings to conceal an unknown identity.

## Acceptance criteria

- Capture the actual Core inventory and review detail as distinct, useful states, with the requested light and dark appearances visibly applied. Verify the detail route and its contents during capture; if unavailable, report the gap rather than invent a screen.
- Show the fictional contract’s declared Jira and Confluence inputs without implying a generated report or live account connection.
- Capture both fixture requester results in the CLI, showing useful issue data and the plan’s body, source and revision. Do not present terminal output as feature UI.
- Use the existing bootstrap and genuine application surfaces. Reject duplicate captures, caption-only differences, forged HTML, unknown identities and any screenshot or transcript that fails independent privacy review.
- The TOML below is structurally reviewed against the supplied format; capture behavior and runtime validation remain unverified because the request prohibits code execution.
