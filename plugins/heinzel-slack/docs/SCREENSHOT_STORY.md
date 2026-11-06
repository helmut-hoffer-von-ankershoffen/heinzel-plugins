## Audience

A Heinzelmännchen user deciding whether Slack is a useful private mailbox for notices and exact-draft decisions, and whether its setup and approval limits fit their workflow.

## Outcome

Show the owner reviewing the exact account, destination, scope and notice before a fictional delivery, then seeing Core's delivery receipt. Complement that flow with a terminal rendering of a draft and the decision code's responses to valid and invalid clicks. The receipt means the local stand-in reported delivery; it does not mean a captured write was approved or that a real Slack delivery occurred.

## Scenes

1. **Review the notice — light.** In Core's real chat confirmation surface, Mira reviews Lotte's complete fictional weekly-report notice and its posting terms before deciding. The fixture stages a pending `deliver-channel-item` action without posting (`docs/screenshot_fixture.py`, `stage_notice`).
2. **See the result — dark.** Confirm the same kind of staged notice and show the resulting Core receipt. The fixture's loopback stand-in accepts one matching post; this is a distinct state of the real review flow, not evidence of live Slack delivery (`docs/screenshot_fixture.py`, `StandIn` and `stage_notice`).
3. **Read a draft — CLI.** Show the fictional weekly report and button labels rendered from the plugin's Slack message blocks in the native terminal. This is a fixture rendering, not a screenshot of Slack (`docs/screenshot_fixture.py`, `share` and `draw`).
4. **Understand the decision — CLI.** Show the fixture's table of owner, stranger, stale, replay and other cases, including the reply returned to the host. These are simulated payloads passed to the real decision code, not live clicks (`docs/screenshot_fixture.py`, `answers`).

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap and its isolated gallery profile, fictional Mira, Jonas, Lotte, workspace, DM and weekly report. The UI transport uses an exact loopback stand-in; the CLI fixture records posts in memory. Its `showcase share` and `showcase answers` operations are documentation-only fixture commands, not declared product CLI operations. No new fixture files or product screens are needed.

## Source-bound UI surface inventory

- `pyproject.toml` declares both `heinzel.modules: slack = heinzel_slack` and `heinzel.connected_sources: slack = heinzel_slack`. Their target, `src/heinzel_slack/__init__.py`, registers settings, transport, service and channel, and declares operations `info`, `manifest`, `notify`, `ask`, `status`, `wait` and `listen`; the scheduled `listen` job; local and live health checks; optional setup; and a system-info contribution. `src/heinzel_slack/_module.py` declares the `slack` module. These declarations can feed generic Core operation, setup, health and info surfaces; absence of a plugin Page or View is not evidence that no feature UI exists. Exact generic surfaces beyond the fixture's demonstrated confirmation flow remain unverified from the supplied sources.
- `src/heinzel_slack/_channel.py` supplies the notification and approval channel; the fixture demonstrates Core's genuine chat proposal and confirmation UI for a notice. Pending review and delivered receipt are two useful states of that same feature flow. The delivered receipt must not be described as draft approval.
- Slack's DM, message blocks and Approve/Decline buttons are **external provider UI**, built by `src/heinzel_slack/_blocks.py` and used by the channel/service. The terminal rendering in `docs/screenshot_fixture.py` is an explanatory representation of those blocks, not actual Slack UI. Live provider capture is not established by this offline fixture.
- `src/heinzel_slack/links/__init__.py` declares a separate `links` module and conditionally registers `SlackReviewedLinks` when the Core contract and captured-source condition exist; `src/heinzel_slack/links/_reviewed_link.py` names its channel `slack-reviewed-links` and implements reviewed link delivery. README describes it as `slack.links`, but `pyproject.toml` declares only `heinzel_slack` for both entry points; the supplied declarations do not establish how the separate record is discovered. Its generic Core review surface and installed availability remain unresolved, so this plan does not invent a route or capture for it.
- The declared setup and `system_info` contribution can appear in Core surfaces; health checks can inform Doctor. No plugin nav, footer, Page or View declaration is established in the supplied first-party source. `manifest()` reads `src/heinzel_slack/manifest.json`, which is absent from the supplied file inventory, so its availability cannot be assumed. README also says installed acceptance against the released SDK and a new gallery review are pending; existing captures illustrate earlier behavior.

## Privacy pitfalls

Use synthetic identities, report text and isolated credentials only. Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail; independent review must inspect every image and transcript for identifiers, credentials, paths and unintended content. Do not treat an apparent fixture, sanitized path or hostname as proof of privacy.

## Acceptance criteria

- Capture the two genuine Core feature states in applied light and dark appearance, plus both useful native-terminal fixture results. Reject duplicate captures, caption-only changes, terminal output presented as feature UI, and forged HTML.
- Show the complete review terms and the actual delivery receipt; retain the distinction between consent to send a notice, the stand-in's delivery report, and a separate draft approval.
- Label all scenes as demo data. Do not imply the fixture proves a real Slack workspace, released-SDK acceptance, live provider behavior or privacy acceptance.
- Independently inspect every image and transcript, failing unknown identities and any exposed secrets or unintended personal data. Verify the selected UI actions, appearance and readable framing during explicit capture.
- Preserve the existing plan's four useful scenes. The TOML below has been checked against the supplied format and source declarations by inspection; no code execution, capture or runtime validation was performed.
