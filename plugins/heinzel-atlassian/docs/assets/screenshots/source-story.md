## Audience

A person considering Heinzelmännchen for a Jira-and-Confluence workflow who wants to see what can be read locally, how the sources fit a workflow, and what setup and approval limits apply.

## Outcome

Show a fictional weekly review that declares both capabilities, then show the actual adapter results for its fictional Jira issues and Confluence plan. The captures demonstrate reads through fixture-supplied responses; they do not demonstrate a connected Atlassian account, a generated report, or an approved Jira change.

## Scenes

1. **Review inventory — light UI.** Find the fictional Weekly work review in Core’s contracts inventory. This establishes the workflow’s context without implying it has run.
2. **Workflow context — dark UI.** Open the same fictional contract and inspect its Jira and Confluence requirements, inputs, and intended output. This is a meaningful detail state of the same Core feature, not a second route claimed to be a plugin-owned screen.
3. **Issue changes — CLI.** Show structured fictional Jira issue results, including state and owner, through the real adapter and fixture-only requester.
4. **Launch plan — CLI.** Show the fictional Confluence page, source, and revision through the real adapter and fixture-only requester.

The existing plan’s contract scenes and two useful CLI results are retained. Its two app-terminal captures are omitted as duplicate presentations of the CLI results, not counted as feature UI.

## Fictional fixtures

`docs/screenshot_fixture.py` creates the local Weekly work review contract and declares the documentation-only `showcase.issues` and `showcase.page` operations. Its `DemoAcli` supplies fictional Jira and Confluence replies to the real adapters without executing an external CLI. The contract declares a workflow and explicitly says no report has been generated. The fictional site, people, issue keys, page, and vendor responses are demo data. Capture must use this existing bootstrap only during explicit capture.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript. Do not infer that a fixture, a status label, or a successful capture proves privacy or a live connection.

## Acceptance criteria

- Capture four distinct scenes from the actual application and CLI with the existing isolated fixture; captions identify demo data and the fixture-only requester where applicable.
- The light inventory and dark detail scenes show real Core contracts UI. Confirm that `/contracts/weekly-work-review` resolves to the fixture contract and that the named heading appears; its route is present in the existing plan but its Core route declaration is not among the provided sources. If it does not resolve, investigate the actual Core navigation before capture rather than fabricate a page.
- The two CLI scenes show the issue and document results, respectively, with no duplicate or caption-only capture. Do not present terminal output as feature UI or forge HTML.
- Inspect every image and transcript independently for identities, paths, hostnames, credentials, and other unintended local data. Unknown identities fail review; only the disclosed verified mappings are permitted.
- Preserve the truth that no report, live sign-in, live connector test, or Jira write is demonstrated. Do not alter SDK health statuses or other Doctor details.
- Apply and verify the requested light and dark appearances in the captured views. Review the contact sheet and capture manifest described in `docs/SCREENSHOTS.md`.

## Source-bound UI surface inventory

- **Plugin entrypoint and capabilities:** `pyproject.toml` declares `heinzel.modules` entrypoint `atlassian = "heinzel_atlassian"`; `src/heinzel_atlassian/_module.py` declares the `atlassian` module. `src/heinzel_atlassian/__init__.py` registers settings, services, read-mode `tracker` and `documents` providers, public `info` and `status` operations, `system_info`, offline health, and live health. No plugin Page, View, navigation, channel, footer, or setup contribution is declared in the provided plugin source. That absence alone does not rule out Core-rendered UI.
- **Core feature UI:** `docs/screenshot_fixture.py` creates a real local responsibility contract with `tracker.issues_updated` and `documents.read` inputs. The existing `docs/screenshots.toml` specifies `/contracts` and `/contracts/weekly-work-review`; the user-provided route inventory confirms `/contracts`, but the detail route’s Core declaration is not provided. Its capture remains subject to the route check above. These are Core contract surfaces using example data, not Atlassian-owned screens.
- **Connector and system surfaces:** `README.md` describes Settings → Connectors and a connector page, while `src/heinzel_atlassian/_status.py` defines connector status data and `src/heinzel_atlassian/__init__.py` supplies status, info, and health contributions. These are evidence of generic Core-rendered surfaces, although their route and fixture-visible states are not declared in the provided files. The fixture’s `DemoAcli.run` handles only the three documented read requests, so do not assume it can produce a connected status or live test. Doctor is offline and does not establish login.
- **Operations, notices, and approvals:** `src/heinzel_atlassian/__init__.py` declares private assigned, epics, watch, and draft operations; its three writes explicitly have `heads={"cli"}`. `src/heinzel_atlassian/_work.py` and `_drafts.py` provide notice and approval text for a host, not a channel or approval UI. `README.md` says released Core has no generic approval contract for private plugin operations and that applying a draft currently requires the CLI. The private read and draft declarations alone do not establish a usable web screen or terminal-only restriction.
- **Terminal results:** `docs/screenshot_fixture.py` declares `showcase.issues` and `showcase.page` with Rich renderers for the fixture CLI. Their CLI captures demonstrate adapter outputs; no provided declaration establishes them as feature UI. The plugin’s explicit write operations are genuinely CLI-restricted, but this fixture does not supply their requests, so the plan does not simulate them.
- **External provider UI:** Atlassian’s browser sign-in and Jira/Confluence product screens are external, not plugin or Core screens; none is invented in this story.
- **Documentation contradiction:** `README.md` says Jira shapes were checked against a live acli site and Confluence samples remain assumed, while its Known gaps section broadly says acli JSON shapes have not yet been verified against a signed-in acli. Resolve that inconsistency before making a stronger verification claim.
