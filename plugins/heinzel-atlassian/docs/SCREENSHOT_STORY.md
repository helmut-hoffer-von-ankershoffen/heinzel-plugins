## Audience

Someone deciding whether Heinzelmännchen can bring Jira work and a Confluence plan into a local workflow without handing another credential to a plugin.

## Outcome

Show a fictional weekly review that declares both inputs, then show the actual adapter results for each input. The review is a local contract, not a generated report; the CLI results use fixture-only vendor replies, not a live Atlassian account.

## Scenes

1. **Find the review — light.** The Core contracts inventory shows the fictional Weekly work review alongside local contracts. This establishes where a person finds the workflow.
2. **Understand its inputs — dark.** The Core contract detail shows the fictional review's Jira and Confluence requirements and intended output. It declares a workflow; it has not generated a report. These are two meaningful views of the same real Core flow, not duplicate captures.
3. **Inspect Jira changes.** A CLI requester returns structured fictional WID issues through the Jira adapter. JSON makes the fields and their provenance inspectable.
4. **Read the plan.** A second CLI requester returns the fictional Confluence plan as formatted text, with its source and revision. The requester and its renderer are documentation fixtures, not built-in Atlassian commands.

## Fictional fixtures

`docs/screenshot_fixture.py` is the existing bootstrap. It creates the local review contract in the isolated state directory, binds both capabilities to Atlassian, supplies fictional Jira and Confluence replies through `DemoAcli`, and registers the documentation-only `showcase issues` and `showcase page` operations. The adapter parsers are real; no external acli or account is used for those replies. The review contract itself does not execute the workflow.

## Source-bound UI surface inventory

- `pyproject.toml` declares the sole `heinzel.modules` entry point, `atlassian = "heinzel_atlassian"`. `src/heinzel_atlassian/_module.py` declares the module; `src/heinzel_atlassian/__init__.py` registers its settings, services, read-only `tracker` and `documents` providers, public `info` and `status` operations, system info, offline health and live connector health contributions. No plugin navigation, Page, View, channel, approval, setup or footer contribution is declared in the supplied plugin source; that absence alone does not establish the absence of Core-rendered UI.
- **Core feature UI:** the existing plan and fixture identify `/contracts` and `/contracts/weekly-work-review` as the local contract inventory and detail flow. The detail route and visible content still need capture-time confirmation; the supplied source does not contain Core's route implementation. The contract is a demonstration consumer of the adapter, not an Atlassian-native screen.
- **Core connector UI:** `README.md` describes Settings → Connectors and a connector page; `src/heinzel_atlassian/_status.py` describes status-dot, text and button fields. The supplied source does not establish the connector route or a fixture that safely supplies its status replies. It is therefore an identified surface, not a fabricated scene. The live connector test can perform reads and must not be represented as an offline login check.
- **Core info and health:** `@module.info`, `@module.health` and `@module.health(live=True)` in `src/heinzel_atlassian/__init__.py`, with `src/heinzel_atlassian/_service.py`, contribute system information and checks. Their exact Core UI presentation is not established by the supplied files. Offline Doctor checks version, site and bindings; it does not establish login or live connectivity.
- **Private operations and approvals:** `src/heinzel_atlassian/__init__.py` declares assigned, epics, watch and three drafts as private operations; only the three actual writes additionally declare `heads={"cli"}`. Do not infer that all private reads or drafts are CLI-only. `README.md` and `src/heinzel_atlassian/_drafts.py` say the released Core has no generic approval contract for these private writes; draft approval text is data for a host, not an implemented approval screen. The fixture does not supply the extra responses these operations need.
- **External provider UI:** acli's browser login and Atlassian Jira/Confluence screens belong to the provider; none is a plugin screen or part of this plan. `README.md` says acli owns authentication and the plugin stores no token.
- **Terminal results:** `showcase issues` and `showcase page` are fixture-only operations declared in `docs/screenshot_fixture.py`; their CLI renderers show actual adapter output from local replies. They are CLI scenes, never presented as feature UI. The plugin's `create-issue`, `update-issue` and `comment-issue` explicitly restrict writes to CLI in `src/heinzel_atlassian/__init__.py`.
- **Evidence conflict:** `README.md` reports Jira shapes checked against acli 1.3.39 but later says all acli JSON shapes are unverified; it also says Confluence samples remain assumed. Treat live Jira coverage and Confluence compatibility as unresolved until independently verified, rather than claiming the fixture proves either.

## Privacy pitfalls

Use only the isolated fictional profile and local fixture replies. Normal presentation fictionalization may map verified owning-interpreter paths to `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row to `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail; an independent reviewer must inspect every image and transcript for names, accounts, paths, hostnames, credentials and other identifying data. Do not replace unknown values speculatively or imply fixture data establishes a live connection.

## Acceptance criteria

- Capture both useful Core contract views in their applied light and dark appearances, with the declared requirements legible and the absence of a generated report clear. Confirm the actual route and content at capture time; stop and resolve discrepancies rather than inventing a screen.
- Capture both CLI results with their fictional provenance visible in the gallery captions. The Jira result must show meaningful issue fields; the Confluence result must show the plan, source and revision. No network or real account is needed for the fixture replies.
- Reject duplicate captures, caption-only changes, terminal output presented as feature UI, forged HTML and invented routes or screens. Do not claim a live connection, approval, successful write or generated report.
- Independently inspect every image and transcript and resolve any unknown identity before acceptance. Verify the plan with the screenshot tooling during an explicitly authorized capture. This response preserves the existing plan and has been checked by inspection only: execution and runtime validation were prohibited.
