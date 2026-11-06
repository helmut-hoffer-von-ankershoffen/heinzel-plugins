## Audience

Someone considering a private Slack notification and draft-approval channel for Heinzelmännchen, who wants to understand what is reviewed, where decisions happen, and what setup requires.

## Outcome

Show a fictional weekly-report notice at the point where the owner can inspect its exact posting account, destination, scope, and message, then show the Core receipt after confirmation. Complement that real Core flow with terminal demonstrations of the Slack draft blocks and decision checks. The receipt establishes delivery to the fixture's local stand-in, not delivery to a real Slack workspace or approval of a separate captured write.

## Scenes

1. **Review the notice — light UI.** Mira sees the pending Core confirmation with the fictional account, owner DM, scope, title, and full reason. The existing fixture stages this through the channel proposal and Core chat APIs (`docs/screenshot_fixture.py`, `stage_notice`).
2. **See the result — dark UI.** After confirmation, Core reports that the channel delivered the notice to the local stand-in. This is a meaningful later state of the same flow, not a duplicate image or a claim that a draft was approved (`docs/screenshot_fixture.py`, `StandIn` and `RECEIPT`).
3. **Inspect a draft — CLI.** The fixture's `showcase share` renders the actual posted Slack message blocks as a terminal illustration, including the fictional draft and button labels. It is not a screenshot of Slack or an interactive feature UI (`docs/screenshot_fixture.py`, `share`, `draw`).
4. **Inspect decisions — CLI.** `showcase answers` exercises the real decision code with fictional owner, stranger, stale draft, replay, and expiry cases, and reports the host's replies. These are fixture operations, not declared production `hz slack` commands (`docs/screenshot_fixture.py`, `answers`).

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap and its private synthetic profile. Lotte, Mira, Jonas, the workspace and DM identifiers, and the reading-list report are fictional. The UI fixture binds a loopback Slack stand-in and stages one notice; the CLI fixture records posts in memory. No live Slack delivery or installed acceptance is established by this plan. The README explicitly says released-SDK acceptance and a new gallery review are pending (`README.md`, opening notice).

## Source-bound UI surface inventory

- **Core feature UI:** The actual Core chat confirmation and delivery result are evidenced by the fixture's proposal operations, pending action, review terms, confirmation, and receipt (`docs/screenshot_fixture.py`, `stage_notice`). The plan uses `/`, an existing generic Core route. This is sufficient evidence for two useful feature UI states even though this plugin declares no dedicated Page or View.
- **External provider UI:** Slack itself displays the posted notice or draft and its Approve and Decline buttons. The plugin constructs message blocks and handles button decisions (`src/heinzel_slack/_blocks.py`, `src/heinzel_slack/_service.py`, `src/heinzel_slack/_decide.py`). The fixture's terminal rendering is an illustration of those blocks, not genuine Slack UI. No provider screenshot is claimed.
- **Operations and generic Core contributions:** Both declared entry points in `pyproject.toml`, `heinzel.modules:slack` and `heinzel.connected_sources:slack`, target `heinzel_slack`. Its `module` is declared in `src/heinzel_slack/_module.py`; `src/heinzel_slack/__init__.py` registers settings, services, `info`, `manifest`, `notify`, `ask`, `status`, `wait`, and `listen`, plus a scheduled listener, local/live health, optional setup, and system-info metadata. These can contribute to generic Core operation, setup, health, and information surfaces; their precise rendered screens are not supplied here and are not invented in the plan. Settings are declared in `src/heinzel_slack/_settings.py`.
- **Channel and approval surfaces:** `src/heinzel_slack/_channel.py` exposes the notification and approval channel, while Core owns the demonstrated review and confirmation. The separate `Module("links", ...)` conditionally registers `SlackReviewedLinks` only when the captured-source SDK contracts are available (`src/heinzel_slack/links/__init__.py`); its reviewed Google Doc link flow and self-DM target are described in `README.md` and `src/heinzel_slack/links/_reviewed_link.py`. This fixture does not demonstrate that flow. Its module record is described by the README, but no separate packaging entry point for it is declared in the supplied `pyproject.toml`; how Core discovers it remains unresolved from these sources.
- **Terminal and unresolved evidence:** The fixture's two `showcase` operations are documentation-only native terminal results. Production operations are declared in source, but absence of a dedicated view does not make them terminal-only. No plugin navigation or footer declaration is evident in the inspected first-party declarations; this does not rule out generic Core rendering. The manifest operation reads `src/heinzel_slack/manifest.json`, which is not present in the provided file inventory, so its actual output cannot be verified here. The README's development-status warning qualifies any existing screenshot claims.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript. Inspect account IDs, paths, timestamps, tokens, hostnames, terminal history, and any unexpected Core content; do not publish if their provenance is unknown. The local stand-in and fictional account identifiers must remain visibly distinguishable from real delivery.

## Acceptance criteria

- Capture the existing four distinct scenes with applied light and dark appearances, using the declared bootstrap and demo data. Confirm the review contains the complete terms and the later state shows the actual Core receipt.
- Treat the two terminal outputs as labeled fixture demonstrations, never as Slack UI or production commands. Reject duplicate captures, caption-only changes, terminal output presented as feature UI, and forged HTML.
- Independently inspect every image and transcript for privacy and truthfulness, including the narrowly permitted path and hostname mappings. Unknown identities fail review.
- Verify that the local stand-in received only the intended notice and that the receipt does not imply draft approval or live Slack acceptance. Preserve any failure or changed SDK health status rather than masking it.
- The existing plan is preserved because it already demonstrates the useful Core review and delivery states plus two distinct decision-related CLI results. Its TOML structure was reviewed against the supplied schema requirements without executing code or performing a capture; runtime behavior and accessibility labels remain to be verified during explicit capture.
