## Audience and outcome

For someone deciding whether Atlassian belongs in a Heinzel workflow: show how a local review can declare Jira and Confluence inputs, then show the fictional data the real adapters return. The review is a declaration, not a generated report or proof of a live connection.

## Scenes

1. **Review inventory — light UI.** Find the fictional Weekly work review in Core’s contracts inventory. It establishes where the workflow lives.
2. **Workflow context — dark UI.** Open that review to see its goal and declared tracker and documents inputs. This is a different, useful state of the same Core feature flow, not a duplicate or caption-only variation.
3. **Jira changes — CLI.** Show structured fictional WID issue results through the real Jira adapter and the fixture-only requester.
4. **Confluence plan — CLI.** Show the fictional plan’s converted text, source and revision through the real Confluence adapter. These are two distinct adapter operations, not substitutes for feature UI.

The existing `docs/screenshots.toml` already tells this story, so the plan below preserves it. The two appearances apply to the actual UI scenes.

## Fictional fixtures

`docs/screenshot_fixture.py` creates the local Weekly work review contract and registers a documentation-only `showcase` module. Its `issues` and `page` operations use the real adapters with `DemoAcli` and local fictional vendor replies. WID, its people, issues, site and plan are demonstration data. No report is generated, and these captures do not demonstrate an authenticated Atlassian account or a live vendor read.

## Source-bound UI surface inventory

- `pyproject.toml` declares the sole `heinzel.modules` entry point, `atlassian = "heinzel_atlassian"`. `src/heinzel_atlassian/_module.py` declares the module; `src/heinzel_atlassian/__init__.py` registers tracker and documents read adapters, public `info` and `status` operations, system info, and offline and live health contributions. The Core-rendered contracts inventory and detail in the plan come from the fixture’s contract, not from a plugin-owned Page or View.
- `README.md` describes a Core Settings → Connectors surface and a connector page. `src/heinzel_atlassian/_status.py` describes status fields intended for a connector page, and `src/heinzel_atlassian/_service.py` supplies health and live-test checks. Their exact routes, rendered controls and fixture-supported states are not established by the provided files; do not invent a route or capture a claimed connected state. `info` and health contributions may also appear in Core surfaces, but their precise UI presentation is unresolved here.
- `src/heinzel_atlassian/__init__.py` declares private `assigned`, `epics`, `watch` and three draft operations; privacy alone does not establish that all are terminal-only. Its three mutating operations explicitly declare `heads={"cli"}`. `README.md` says writes require a person’s CLI command and that released Core has no generic approval contract for private plugin operations. The plugin supplies notice and approval text as data, but declares no channel or approval handler; do not depict an approval screen or claim an approval occurred.
- Atlassian’s browser login is external provider UI (`README.md`), not a Heinzel feature screen. The fixture’s Rich renderers in `docs/screenshot_fixture.py` produce CLI output; they are not plugin UI. No plugin navigation, setup, footer, Page or View declaration was found in the provided source. That absence does not rule out the Core-rendered surfaces above.
- Surface evidence has a documentation contradiction: `README.md` says Doctor does not check login and `_service.py` repeats that claim in docstrings, but `_acli_check` calls `self.status(bindings)` after a successful version check. Treat the actual observed result as authoritative and do not claim Doctor is version-only without resolving that discrepancy. The README also says Jira shapes were checked against live acli while its Known gaps section says JSON shapes remain unverified; Confluence samples are expressly described as assumed.

## Privacy and presentation

Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail; an independent reviewer must inspect every image and transcript for identities, paths, hostnames, credentials and other sensitive content. Do not fabricate HTML or use terminal output as feature UI.

## Acceptance criteria

- Capture both genuine Core contract states in their specified light and dark appearances, with readable fictional content and no duplicate captures.
- Capture the two actual fixture-backed CLI results, retaining their demo-data labels and the distinction between adapter output and a generated report.
- Confirm the fixture and routes work in the capture environment; the supplied files establish the intended plan but no capture or execution was performed here. The TOML is structurally checked by inspection; runtime and schema validation remain to be performed during explicit capture.
- Inspect every image and transcript independently, reject unknown identities, and apply only the disclosed verified presentation mappings. Do not infer privacy acceptance from those mappings.
- Preserve actual health and connection states, avoid external provider screens and live reads, and record any route or rendering mismatch rather than inventing a screen.
