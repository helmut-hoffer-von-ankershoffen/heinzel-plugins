## Audience

A person considering the plugin for a Heinzelmännchen workflow that reads Jira changes alongside a Confluence plan, and who wants to understand what is demonstrated before connecting an account.

## Outcome

Follow a fictional weekly review from its place among local contracts to its declared inputs, then inspect the actual adapter results for Jira and Confluence. The contract is a workflow declaration: the screenshots must not imply that a review report was generated or that an Atlassian account was connected.

## Scenes

1. **Review inventory — light UI.** Find “Weekly work review” among local contracts. This places the example in a useful Core feature, with demo data identified in the caption.
2. **Workflow context — dark UI.** Open the same contract’s detail and show its Jira and Confluence inputs and intended review. This is a meaningfully different view of the workflow, not a second capture distinguished only by its caption. The existing plan declares this route; its availability and rendered content still need capture-time verification.
3. **Jira result — CLI.** Show structured fictional WID issue changes returned by the real Jira adapter through the fixture requester. The JSON makes issue keys, state and ownership inspectable.
4. **Confluence result — CLI.** Show the fictional Widget plan, its source and revision returned by the real Confluence adapter through the fixture requester.

The two CLI scenes exercise different operations, so the special requirement for two parameter cases of a single CLI operation does not apply. The existing four-scene plan already tells this story and is preserved below.

## Fictional fixtures

`docs/screenshot_fixture.py` creates the local Weekly work review contract, binds the tracker and documents capabilities to Atlassian, and supplies a `DemoAcli` with local Jira and Confluence replies. Its `showcase.issues` and `showcase.page` operations call the real adapter interfaces; the vendor executable and an account are not used. WID, Wilma Widget, the Widget plan and the `acme.atlassian.net` links are example data. The contract explicitly says no report has been generated. The bootstrap runs only during explicit capture.

Normal presentation fictionalization is also required: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail, and an independent reviewer must inspect every image and transcript.

## Source-bound UI surface inventory

- **Plugin entrypoint and capabilities:** `pyproject.toml` declares the sole `heinzel.modules` entrypoint, `atlassian = "heinzel_atlassian"`; `src/heinzel_atlassian/__init__.py` registers settings, services, and read-only `tracker` and `documents` providers. `src/heinzel_atlassian/_module.py` declares the module. No plugin navigation or page route is declared in the supplied source.
- **Core feature UI:** The existing plan uses `/contracts` and `/contracts/weekly-work-review` for the fixture’s contract inventory and detail. The former is a supplied generic Core route; the detail route is asserted by `docs/screenshots.toml`, but its implementation is outside the provided source. Verify both captures and their meaningful content; do not infer the detail route solely from the contract name. These are Core contract views of a declared workflow, not rendered Jira or Confluence results.
- **Connector and status UI:** `README.md` describes Settings → Connectors and a connector page; `src/heinzel_atlassian/__init__.py` declares `status`, ordinary health, and live health, while `src/heinzel_atlassian/_status.py` defines the connector state, identity, site, action and refresh fields. This is evidence of a Core-rendered connector surface even without a plugin Page/View. Its route and the fixture’s ability to populate its status are not established here; `DemoAcli.run` does not implement auth-status requests. Do not fabricate a connected view.
- **Operations and generic rendering:** `info` and `status` are public operations; `assigned`, `epics`, `watch` and three draft operations are private, everyday operations in `src/heinzel_atlassian/__init__.py`. Their declarations do not restrict them to CLI, so absence of a dedicated page does not establish terminal-only behavior. The supplied sources do not establish their actual Core web routes or fixture responses. `@module.info` contributes to system information, and `@module.health` contributes to Doctor; `@module.health(live=True)` is an on-demand connector test. `README.md` says Doctor is offline and does not prove sign-in.
- **Approval and channel surfaces:** `src/heinzel_atlassian/_drafts.py` and `README.md` describe draft previews, argument hashes and approval text for a host to use. The plugin declares no channel or approval UI and approves nothing. The README says released Core has no generic approval contract for private plugin operations; no approval screen is evidenced. The three actual write operations in `src/heinzel_atlassian/__init__.py` explicitly have `heads={"cli"}` and require a person’s CLI action.
- **Setup, footer and external UI:** The supplied declarations contain settings but no separate setup or footer contribution. The README describes acli installation and browser sign-in; those are external provider/tool flows, not plugin feature screens. Its description of the connector and current private-operation limitations is more specific than the absence of Page/View declarations. The provided source does not establish other generic Core surfaces, so unresolved rendering must be checked rather than invented.
- **Fixture CLI results:** `docs/screenshot_fixture.py` declares `showcase.issues` and `showcase.page` with Rich renderers and local replies. The plan’s CLI captures are genuine CLI output, not substitutes labelled as feature UI. The fixture does not provide the responses needed to claim a demonstrated live connector test, private Jira work flow, or write.

## Privacy pitfalls

Inspect images and transcripts for real usernames, email addresses, hostnames, local paths, credentials, tokens, unexpected issue text and account state. Apply only the explicitly verified presentation mappings above; unknown identities fail review. Fixture URLs and names must remain clearly fictional. Do not expose real acli configuration or claim the fixture proves a live connection. Independent review must inspect every image and transcript, including material outside cropped areas where available.

## Acceptance criteria

- Capture all four distinct scenes from the existing fixture and plan: two useful Core feature UI views, one light and one dark, plus both real adapter CLI results. Confirm the appearance is actually applied.
- Verify the inventory and detail really show the fictional contract and its declared inputs. If the detail route or expected content is unavailable, report the evidence and repair the plan only using a verified existing surface; do not fabricate a screen.
- Verify the CLI output reflects the fixture’s Jira issues and Confluence page, source and revision, and does not claim a generated report or connected account.
- Captions identify demo data; no duplicate captures, caption-only changes, terminal output presented as feature UI, forged HTML, or invented routes are accepted.
- Independently review every image and transcript for privacy and truthfulness. The specified path and Doctor-host substitutions are presentation fictionalization, not privacy approval.
- The TOML below preserves the supplied plan and has been inspected against the requested structure. No code or capture was executed, so parser validation and runtime behavior remain unverified.
