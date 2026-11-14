## Audience

Someone considering Slack as a private notification and draft-approval channel for Heinzelmännchen, who wants to see what is reviewed and what an approval actually means.

## Outcome

Show Mira reviewing a complete fictional notice and its exact Slack destination before delivery, then seeing Core’s delivery receipt. Follow with a terminal demonstration of a fictional draft and the decisions the plugin accepts or refuses. Delivery of a notice is not approval of a captured write, and an owner’s Slack click is a separate decision that the host must validate.

## Scenes

1. **Review the notice — light UI.** In the genuine Core review region, show the fictional account, destination, scope and complete weekly-report notice alongside Confirm and Decline. This is the pre-delivery state staged by `docs/screenshot_fixture.py`.
2. **See the result — dark UI.** Confirm the same staged notice and show Core’s real delivery receipt. The recipient is a local Slack stand-in, not a live workspace. This is a meaningful subsequent state of the same flow, not a duplicate capture.
3. **Read the draft — CLI.** Show `showcase share`: the fixture renders the actual Slack message blocks as terminal text, including the exact fictional draft and button labels. It is a terminal rendering, not a screenshot of Slack or an interactive approval screen.
4. **Understand the decision — CLI.** Show `showcase answers`: the fixture exercises the real decision code with a stranger, an old digest, a typed reply, the owner’s click, a replay and an expired click. The result illustrates safeguards without claiming a live Slack acceptance test.

The two CLI commands are separate operations declared by the existing documentation fixture; they are not installed plugin operations. The two UI scenes are genuine Core feature states created through the channel-review flow. The existing plan already demonstrates this behavior and is preserved below.

## Fictional fixtures

`docs/screenshot_fixture.py` supplies Mira, Jonas, Lotte, a demo workspace, a weekly-report notice and draft, a private isolated profile, and a loopback Slack stand-in. It stages the Core review and records the stand-in post; its CLI showcase uses the plugin’s channel and decision code with an in-memory transport. It is a capture fixture, not evidence of a live Slack integration. `README.md` states that installed acceptance against the released SDK and a new gallery review are pending.

## Privacy pitfalls

Use only the isolated capture profile and fictional values. Inspect every image and transcript independently for credentials, real account or workspace identifiers, paths, hostnames, message content and other identifying details. Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail and independent review must inspect every image/transcript. Do not substitute invented status, conceal unrecognized values, or infer privacy acceptance from these mappings.

## Acceptance criteria

- Capture both genuine Core review states with the notice and exact target legible; the second must show the observed stand-in delivery receipt and its limitation.
- Apply light and dark appearances as specified, and use visibly distinct pre-confirmation and post-confirmation states.
- Label all four scenes as demo data. Keep the terminal rendering and simulated decisions clearly distinct from external Slack UI and live delivery.
- Reject duplicate captures, caption-only changes, terminal output presented as feature UI, and forged HTML. Do not claim a Slack click approved any downstream action.
- Independently review every image and transcript for privacy and accuracy. Treat the fixture’s source assertions as intended behavior until capture and review actually establish the observed result.

## Source-bound UI surface inventory

- `pyproject.toml` declares both `heinzel.modules` and `heinzel.connected_sources` entrypoints named `slack`, each pointing to `heinzel_slack`. `src/heinzel_slack/_module.py` declares `Module("slack", ...)`; `src/heinzel_slack/__init__.py` registers settings, transport, service and `SlackChannel`. The channel implements notification and approval ports in `src/heinzel_slack/_channel.py`. These contributions can produce genuine Core channel review and confirmation UI; `docs/screenshot_fixture.py` demonstrates the actual `/` chat review flow and receipt. Absence of a plugin Page or View is not evidence of absence of feature UI.
- `src/heinzel_slack/__init__.py` declares operations `info`, `manifest`, `notify`, `ask`, `status`, `wait` and `listen`, plus the scheduled `listen` job, local and live health checks, optional setup, and a `system_info` contribution. These can contribute to generic Core operation, setup, Doctor and system-info surfaces; the supplied sources do not establish additional exact routes or capture-ready states. `src/heinzel_slack/_settings.py` declares settings, but a settings screen alone would not tell the main feature story. No footer or plugin navigation declaration is evidenced in the inspected first-party declarations.
- Slack’s actual DM and interactive buttons are **external provider UI**, produced from blocks in `src/heinzel_slack/_blocks.py` through the channel/service. The fixture’s `draw` function in `docs/screenshot_fixture.py` renders those blocks in a terminal; it is not the provider UI. The plugin’s operations may also produce terminal results, but their existence does not make the Core review flow terminal-only.
- `src/heinzel_slack/links/__init__.py` separately declares `Module("links", ...)` and conditionally registers `SlackReviewedLinks` when the Core contract and captured-source condition exist. `src/heinzel_slack/links/_reviewed_link.py` implements the reviewed-link channel. `README.md` calls its workflow channel `slack-reviewed-links` and its module record `slack.links`; the supplied entrypoint declaration itself only names `heinzel_slack`, so discovery of that separate record and its exact Core UI remain unresolved from these declarations. Do not invent a route or screenshot for it.
- `manifest()` reads `src/heinzel_slack/manifest.json`, but that file was not present in the supplied file inventory; its runtime availability is unresolved. The README’s earlier-capture disclaimer also prevents treating catalog entries in `pyproject.toml` as current acceptance evidence.
