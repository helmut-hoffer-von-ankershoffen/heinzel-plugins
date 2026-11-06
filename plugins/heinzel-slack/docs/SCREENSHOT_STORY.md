## Audience

Someone deciding whether to add Slack as a private notification and draft-approval channel for Heinzelmännchen, and wanting to understand what is reviewed before anything is sent.

## Outcome

Show a fictional notice moving through Core’s real human-review flow, followed by an offline terminal demonstration of the plugin’s draft blocks and decision checks. The story distinguishes consent to deliver a notice from approval of a draft. It does not claim that a real Slack workspace was contacted or that installed acceptance has passed.

## Scenes

1. **Review the notice — light UI.** Mira sees the exact fictional account, destination, scope and weekly-report notice in Core’s proposal. This makes the pre-delivery review tangible.
2. **See the delivery receipt — dark UI.** After confirmation, Core reports delivery to the local stand-in. The receipt explicitly says that delivery does not approve a captured write. This is a meaningful later state of the same flow, not a duplicate with a different caption.
3. **Inspect a draft — CLI.** The fixture renders the actual generated Slack message blocks as a terminal panel, including printed button labels. This is a terminal rendering, not a screenshot of Slack or interactive buttons.
4. **Test the decisions — CLI.** Fictional clicks exercise the decision code: the owner’s valid click records an approval; non-owner, wrong-draft, typed-reply, replay and late attempts are refused. These are two different fixture operations, rather than two parameter cases of one operation.

## Fictional fixtures

`docs/screenshot_fixture.py` supplies the existing isolated bootstrap, fictional Mira, Jonas and Lotte, a demo workspace and weekly report. Its UI path stages a real Core channel proposal and uses a loopback Slack stand-in; its `showcase share` and `showcase answers` operations use an in-memory transport and real plugin code. The stand-in is not Slack, and the CLI renderer is not external-provider UI. The existing `docs/screenshots.toml` already captures these useful states, so the plan below preserves it.

## Privacy pitfalls and presentation

Normal presentation fictionalization is explicitly limited to these mappings: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail; independent review must inspect every image and transcript before publication. Inspect credentials, account and workspace identifiers, local paths, hostnames, chat history, URLs and any accidental real data. Fixture identifiers must remain visibly fictional. Do not treat a successful capture or these mappings as a privacy review.

## Acceptance criteria

- Capture both genuine Core feature states and both useful CLI results from the existing fixture; apply light and dark appearances to the UI scenes. Do not substitute terminal output for either UI state, forge HTML, duplicate captures, or change only captions.
- The review shows the exact fictional target and message before confirmation; the later image shows the real Core receipt after one local stand-in delivery. Neither implies a real Slack delivery or draft approval.
- The CLI draft is identified as rendered Slack blocks with printed, non-interactive controls; the decision result reflects the fixture’s actual outcomes. Do not assert live Slack behavior from this offline demonstration.
- Confirm all captions describe demo data, all scenes render without clipping, and the independent privacy review covers every image and transcript. If fixture setup, source capture, locator matching or delivery fails, report the failure rather than manufacture a result.
- The TOML below is structurally checked against the requested format by inspection; no parser, bootstrap, product code, capture or network call was run. Actual runtime compatibility and visual results remain unverified.

## Source-bound UI surface inventory

- **Entrypoints:** `pyproject.toml` declares both `heinzel.modules` and `heinzel.connected_sources` named `slack`, each targeting `heinzel_slack`. The actual exported `module` is `Module("slack", ...)` in `src/heinzel_slack/_module.py`, populated in `src/heinzel_slack/__init__.py`. `src/heinzel_slack/links/__init__.py` separately defines `Module("links", ...)` and conditionally registers `SlackReviewedLinks` when the SDK contract and active source capture exist; the provided entrypoint declarations do not directly name that module. `README.md` describes a `slack.links` record, so its discovery through the connected-source mechanism remains unresolved from the supplied files.
- **Core feature UI:** `src/heinzel_slack/__init__.py` registers `SlackChannel`, operations and health/setup/info contributions. `docs/screenshot_fixture.py` stages a channel notice through Core’s proposal operations and serves the installed Core UI; `docs/screenshots.toml` identifies the `/` chat review and receipt states. These are Core-rendered feature UI, not a plugin-owned page. Other generic operation, channel, approval, setup, info, health or footer renderings cannot be fully inventoried without the Core source; the declarations alone do not prove their exact routes or appearance.
- **External provider UI:** `src/heinzel_slack/_blocks.py` builds Slack message blocks, and `README.md` describes Slack DM notices and approval buttons. The supplied fixture only renders those blocks in a terminal and simulates clicks; it provides no genuine Slack UI capture.
- **Operations and supporting surfaces:** `src/heinzel_slack/__init__.py` declares `manifest`, `notify`, `ask`, `status`, `wait` and `listen`, private `info`, scheduled `listen_job`, local and live health checks, optional setup, and a system-info contribution. `manifest` reads `src/heinzel_slack/manifest.json`, which is absent from the provided file inventory; its actual output is therefore unresolved. Setup prompts and system info may also be rendered by Core; do not assume they are terminal-only or invent routes for them.
- **Reviewed links:** `src/heinzel_slack/links/_reviewed_link.py` declares the conditional `SlackReviewedLinks` channel, including target observation and reviewed link delivery; `README.md` describes its separate SlackCLI profile and safeguards. No corresponding staged reviewed-link UI is supplied by the screenshot fixture.
- **Terminal demonstration:** `docs/screenshot_fixture.py` declares the documentation-only `showcase` module and its `share` and `answers` operations. Their terminal results are useful evidence of the offline block and decision demonstrations, not proof that the plugin’s product capabilities are terminal-only.
- **Existing gallery contradiction:** `pyproject.toml` labels earlier terminal-rendered captures as `ui`, while `README.md` itself says the draft was rendered in the app terminal and notes installed acceptance and a new gallery review are pending. This plan classifies those demonstrations as CLI and uses the staged Core review and receipt for UI.
