## Audience

A person deciding whether to connect Jira and Confluence to Heinzelmännchen workflows, especially someone who wants to understand what the adapter reads before configuring a real account.

## Outcome

Show a fictional weekly review that brings issue changes and a planning document into one workflow. Make clear that the contract declares inputs; it has not generated a report. Follow it with actual adapter results from the offline demonstration, so the reader can see both the workflow context and the data available to it.

## Scenes

1. **Review inventory — light UI.** Find the fictional Weekly work review in Core’s contracts inventory. This establishes the workflow in its real app context.
2. **Workflow context — dark UI.** Open the same contract and show its Jira and Confluence input declarations and goal. This is a meaningful detail state, not a second capture of the inventory. Do not imply that the workflow has run or produced notes.
3. **Issue changes — CLI.** Show structured fictional WID issue results from the real tracker adapter through the fixture-only requester and vendor replies. The JSON exposes useful fields and distinguishes this from a live Jira connection.
4. **Planning document — CLI.** Show the fictional Widget plan, its source and revision through the documents adapter. This complements the issue result with the other declared workflow input.

The two CLI scenes exercise two different fixture operations; the one-operation requirement for two parameter cases therefore does not apply. They are CLI results, not feature UI. Preserve the existing scenes because they already demonstrate the useful source behavior.

## Fictional fixtures

`docs/screenshot_fixture.py` creates the local Weekly work review contract, binds the actual tracker and documents adapters, and supplies `DemoAcli` replies for two fictional WID issues and the Widget plan. Its `showcase.issues` and `showcase.page` operations are documentation-only requesters, not shipped Atlassian commands. The fixture uses `https://acme.atlassian.net` as example data and does not establish a connected account. The bootstrap is intended to run only during explicit capture.

## Source-bound UI surface inventory

- **Plugin entry point and capabilities:** `pyproject.toml` declares `heinzel.modules` → `atlassian = "heinzel_atlassian"`; `src/heinzel_atlassian/_module.py` declares the module, and `src/heinzel_atlassian/__init__.py` registers settings, services, and read providers for `tracker` and `documents`.
- **Core feature UI:** The existing `docs/screenshots.toml` identifies `/contracts` and `/contracts/weekly-work-review` for the fixture’s contract inventory and detail. The contract itself is declared in `docs/screenshot_fixture.py`. These are Core-rendered workflow surfaces, not an Atlassian-owned page. The provided source does not independently declare the detail route or prove a successful capture; verify the actual route and content during capture.
- **Connector and setup UI:** `README.md` describes Settings → Connectors, a connector page, the site and login command, and an on-demand connector test. `src/heinzel_atlassian/_status.py` describes the status model used by a connector page; `src/heinzel_atlassian/__init__.py` declares `status`, offline `health`, and live `health`. The exact route and fixture-backed visual states are not established by the provided files, so no invented route or connected state is planned.
- **Other Core-rendered contributions:** `src/heinzel_atlassian/__init__.py` declares public `info` and `status` operations and a `system_info` contribution. Their possible generic Core presentation is not fully specified in the supplied files. The same file declares private assigned, epics, watch and draft operations; their privacy declaration alone does not prove they are terminal-only. `README.md` says Core chat excludes private operations and that private writes are unavailable through web, API and MCP. The three write operations explicitly declare `heads={"cli"}` and are genuinely CLI-restricted. No plugin navigation, channel, approval, setup or footer contribution is declared in the inspected module; `README.md` describes hypothetical host notices and approval requests, not an implemented approval UI. Absence of a Page or View declaration alone is not evidence that generic Core UI cannot exist.
- **External provider UI:** Atlassian’s browser login is external to this plugin (`README.md`); do not present it as plugin UI. The fixture does not open or authenticate it.
- **Evidence conflict:** `README.md` says Jira shapes were checked against a live acli site and Confluence samples remain assumed, while its Known gaps section says the acli JSON shapes have not yet been verified against a signed-in acli. Preserve this contradiction rather than claiming all shapes are verified.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript. Check for real usernames, hostnames, paths, account identities, credentials, site names and unexpected live data; stop on anything not positively established as fictional. Do not replace an unknown identity with a guessed demo value.

## Acceptance criteria

- Capture both genuine Core contract states, with light applied to the inventory and dark applied to the detail, and confirm the actual route and visible fixture content. Do not substitute a terminal, forged HTML, a duplicate image or a caption-only change for a UI state.
- Show the declared issue and document inputs without implying a generated report, live account or successful connection.
- Capture the two useful CLI results from the existing local bootstrap, with fictional data clearly identified and no exact table-cell waits after terminal actions.
- Confirm every caption identifies demo data, all images and transcripts pass independent privacy review, and the only presentation mappings are those explicitly described above.
- Validate the plan with the actual capture tooling and inspect the resulting images and transcripts before publication. TOML structure and fields were checked against the supplied requirements by inspection; capture behavior and tool validation were not executed under the read-only, no-code-execution constraint.
