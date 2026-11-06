## Audience

Someone considering a private Slack channel for useful notices and exact-draft decisions, who wants to understand what they can review before anything is sent.

## Outcome

Show Mira reviewing a fictional notice in Heinzelmännchen, confirming its delivery to a local Slack stand-in, and then seeing how a separate fictional draft and its decision checks work. Delivery of the notice does not approve a draft. The plugin is in development; `README.md` says installed acceptance against the released SDK and a new gallery review are pending.

## Scenes

1. **Review the notice — light UI.** In the genuine Core chat review, show the posting account, owner-DM destination, scope, and full fictional weekly-report notice before confirmation. This is a Core feature surface fed by the Slack channel, not Slack’s own interface. The existing fixture stages the real proposal in `docs/screenshot_fixture.py` (`stage_notice`); the channel’s target and reviewed delivery are declared in `src/heinzel_slack/_channel.py` (`SlackChannel.delivery_target`, `deliver_reviewed`).
2. **See the delivery receipt — dark UI.** Confirm that same proposal and show Core’s resulting receipt. The fixture sends only to its loopback stand-in; the receipt reports delivery and expressly does not approve a captured write. This is a meaningful post-confirmation state of the same flow, not a duplicate capture.
3. **Read the draft — CLI.** The fixture’s `showcase share` renders the fictional draft and button labels from actual Slack message blocks. Label it as a terminal rendering, not a screenshot of Slack or an interactive approval interface. See `docs/screenshot_fixture.py` (`draw`, `showcase`, `share`) and `src/heinzel_slack/_blocks.py`.
4. **Test the decision — CLI.** `showcase answers` exercises the decision code with the owner, a stranger, an old draft binding, a typed reply, a replay, and an expired click. Show the result table and distinguish the one recorded reply from refusals. This is a documentation-only fixture operation, not a claim that those clicks occurred in Slack. See `docs/screenshot_fixture.py` (`answers`) and `src/heinzel_slack/_decide.py`.

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap and its isolated private profile. Mira, Jonas, Lotte, workspace IDs, the weekly report, transport, and Slack responses are demonstration data. UI delivery goes to its loopback stand-in; CLI posts are recorded in memory. No real account, workspace, message, or live Slack delivery is demonstrated. The fixture contains two distinct showcase operations, so both useful cases are retained.

## Source-bound UI surface inventory

- `pyproject.toml` declares both `heinzel.modules` and `heinzel.connected_sources` entry points as `slack = heinzel_slack`. `src/heinzel_slack/_module.py` declares `Module("slack", ...)`; `src/heinzel_slack/__init__.py` registers its settings and services. There is no plugin Page, View, navigation, or footer declaration in the supplied first-party sources. That absence does not rule out Core-rendered UI.
- **Core feature UI:** the notification and approval ports are declared by `SlackChannel` in `src/heinzel_slack/_channel.py`. The fixture explicitly stages a channel notice review through Core’s proposal APIs and serves the installed Core UI at `/` (`docs/screenshot_fixture.py`, `run_gallery_ui` and `stage_notice`). The review and receipt are the two evidenced feature states. The fixture does not establish a genuine Slack draft-approval screen in Core.
- **External provider UI:** `src/heinzel_slack/_blocks.py` constructs Slack message blocks, including draft actions. Actual Slack renders those blocks; the supplied fixture’s `draw` is a terminal representation, not the provider UI. Do not forge Slack HTML or present the rendering as a real Slack screen.
- **Operations and generic Core surfaces:** `src/heinzel_slack/__init__.py` declares `info`, `manifest`, `notify`, `ask`, `status`, `wait`, and `listen`; a scheduled `listen` job; local and live health checks; optional setup; and a static `system_info` contribution. These can contribute to Core’s generic operation, Doctor, setup, or info experiences, but the supplied files do not establish exact routes or capture-ready UI states for each. The operation declarations alone do not make their behavior terminal-only. The existing fixture’s `showcase` renderers are specifically terminal demonstrations.
- **Reviewed links:** `src/heinzel_slack/links/__init__.py` declares a separate `Module("links", ...)` and conditionally registers `SlackReviewedLinks` only when the reviewed-link contract exists and source capture is active. `src/heinzel_slack/links/_reviewed_link.py` declares `delivery_target` and `deliver_link_reviewed`. `README.md` describes a separate `slack.links` module record, but the supplied entry-point declaration does not itself show how that record is discovered. Its generic Core review surface and a capture-ready fixture are therefore unresolved; do not invent a route or scene.
- **Unresolved source evidence:** `manifest()` in `src/heinzel_slack/__init__.py` reads `manifest.json`, but that file is absent from the supplied file inventory. Do not promise a working manifest capture from these files. `README.md` also describes earlier captures and pending acceptance; the plan is a capture specification, not evidence of a successful current run.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail. Independently inspect every image and transcript for credentials, paths, hostnames, real account or workspace identifiers, message content, and other identifying details before publication. Do not conceal a failure, alter a status, or imply that a local stand-in is live Slack.

## Acceptance criteria

- Capture the two genuinely different Core review states in applied light and dark appearances, followed by both useful CLI results; no duplicate captures, caption-only variants, forged HTML, or terminal output presented as feature UI.
- Keep the exact reviewed target and complete fictional notice visible before confirmation, and the truthful local-delivery receipt visible afterward. A delivery receipt must not be described as draft approval.
- Preserve the actual decision results and identify the terminal draft rendering and showcase operations as fixture demonstrations.
- Execute the existing bootstrap only during an explicit capture, in its required isolated profile. Do not invent fixture files or routes.
- Independently review every resulting image and transcript, apply only the disclosed verified mappings, and reject unknown identities. Verify the real capture, theme application, and source/SDK compatibility; the supplied files and this plan alone do not establish capture or privacy acceptance.
