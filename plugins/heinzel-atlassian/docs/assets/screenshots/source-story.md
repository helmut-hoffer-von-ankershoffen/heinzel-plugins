## Audience

A person deciding whether Heinzelmännchen can bring Jira issues and a Confluence plan into a local workflow without handing the plugin an Atlassian token.

## Outcome

Show a fictional weekly review as a workflow that requests tracker and document capabilities, then show the actual adapter results that could supply it. The contract declares a workflow; it has not generated a report. The CLI results come from local fixture replies, so they demonstrate parsing and presentation, not a successful connection to Atlassian.

## Scenes

1. **Review inventory, light:** Find the fictional Weekly work review in Core’s contracts inventory. This establishes where a user can discover a workflow.
2. **Workflow context, dark:** Open that contract and inspect its Jira and Confluence inputs and intended output. This is a second meaningful state of the same Core feature flow, not a duplicate capture.
3. **Issue changes, CLI:** Show structured fictional WID issues returned by the real Jira adapter through the fixture requester.
4. **Plan, CLI:** Show the fictional Confluence plan, source, and revision returned by the real document adapter through the fixture requester.

The existing plan already tells this story, so preserve its scenes and commands. The two CLI scenes demonstrate different fixture operations; they do not claim the plugin’s operations are all terminal-only.

## Fictional fixtures

`docs/screenshot_fixture.py` creates the local Weekly work review contract and registers the documentation-only `showcase` module. Its `DemoAcli` supplies local Jira and Confluence replies to the real adapters; its fictional project, people, site, issue titles, page, and dates are demonstration data. Its `issues` and `page` operations are fixture operations, not declared Atlassian plugin commands. The fixture’s vendor executable path is deliberately never executed. The browser clock is fixed by the plan.

## Source-bound UI surface inventory

- `pyproject.toml`, `[project.entry-points."heinzel.modules"]`: the sole declared plugin entry point is `atlassian = "heinzel_atlassian"`. `src/heinzel_atlassian/_module.py` declares its `Module`.
- `src/heinzel_atlassian/__init__.py` registers settings, services, `tracker:read` and `documents:read` providers, public `info` and `status` operations, system info, offline health and live connector health. It also declares private `assigned`, `epics`, `watch`, and draft operations; the three mutating operations explicitly restrict their heads to CLI. Private reads and drafts must not be described as CLI-only merely because this plan shows terminal output.
- Core renders useful workflow UI: the fixture’s contract and its declared inputs appear in the existing `/contracts` inventory and `/contracts/weekly-work-review` detail plan. These are Core feature surfaces using the fixture contract, not a bespoke Atlassian page and not proof that a report ran. The supplied files do not include Core’s route implementation, so actual rendering and the detail route remain capture-time evidence to verify.
- `README.md` describes Settings → Connectors and a connector page, including an on-demand test; `src/heinzel_atlassian/_status.py` defines the status, identity, site, action, and refresh data intended for that surface. The supplied plugin declarations do not establish the Core route, renderer, or whether this fixture produces a useful connector state. Inspect the real Core UI before adding a connector scene; do not invent its route or simulate a successful sign-in. The fixture’s `DemoAcli.run` handles only issue search/view and page view, so it does not furnish status or live-test replies.
- `src/heinzel_atlassian/__init__.py` contributes system info and health; Core may render these generically. The supplied sources do not establish their UI routes or rendered layout. `README.md` documents `hz system doctor` as offline and `hz system connector test atlassian` as a separate live read. Do not present Doctor as proof of login or a live test.
- `README.md` describes notices and approval information a host can use, but says the plugin imports no channel, approves nothing, and the released Core has no generic approval contract for private plugin operations. No approval screen or channel is established by the supplied declarations. Browser authorization and Jira/Confluence themselves are external provider UI, not plugin feature screens. No plugin navigation, page, view, setup, footer, or channel declaration is present in the supplied entry-point module; this absence does not rule out generic Core surfaces.
- `README.md` reports live Jira shape checks while its Known gaps section says acli JSON shapes have not yet been verified against a signed-in acli. Treat that as an unresolved documentation contradiction; Confluence samples are explicitly described as not yet checked live.

## Privacy pitfalls

Use only the fictional fixture profile and replies. For normal presentation fictionalization, verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail; an independent reviewer must inspect every image and transcript. Inspect URLs, account names, paths, environment details, terminal history, and any unexpected real connector status before publication. Do not turn failed or unknown health into success.

## Acceptance criteria

- Capture both genuine Core contract states with the requested light and dark appearances applied, plus both useful CLI results; reject duplicates and caption-only changes.
- Confirm the inventory identifies the fictional review and its detail accurately declares both inputs and the intended notes output, without implying execution.
- Confirm issue and page results are produced by the existing fixture through the adapters, and their captions disclose demo data and local replies. Do not present terminal output as feature UI or forge HTML.
- Verify actual routes, visible content, and applied appearance during capture. Review every image and transcript independently for privacy and truthful health/status presentation; unknown identities fail.
- The TOML below was checked by inspection against the requested fields and preserves the existing plan. No parser or capture was run because code execution was prohibited; syntactic and runtime validation remain required before publication.
