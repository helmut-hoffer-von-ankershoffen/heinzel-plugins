## Audience

A Heinzelmännchen user deciding whether to connect a private Slack app for notices and exact-draft decisions, and who wants to understand what they review before anything is sent.

## Outcome

Show Mira reviewing a fictional weekly-report notice in Core, confirming its delivery to a local Slack stand-in, and then seeing how a separate fictional draft and its decisions are represented. The story should make the boundary clear: confirming delivery is not approval of a captured write, and a Slack draft decision is a separate event.

## Scenes

1. **Review the notice — light.** Core’s actual chat confirmation shows the account, owner-DM destination, scope and complete fictional notice before delivery. This is a useful feature state, not a settings screen.
2. **See the delivery result — dark.** After confirmation, Core’s chat reports delivery to the fixture’s local stand-in. This is a second meaningful state of the same flow, not a duplicate or a caption-only change. It is not evidence of delivery to a real Slack workspace.
3. **Inspect the draft — CLI.** The documentation fixture renders the actual generated Slack message blocks as a terminal presentation, including the fictional draft and button labels. It is a representation of Slack content, not a screenshot of Slack’s UI.
4. **Inspect decision cases — CLI.** The fixture exercises the actual decision code with a non-owner, a mismatched digest, a typed reply, the owner’s approval, replay and expiry. The result illustrates the checks and the single recorded reply; it does not prove a real person clicked in Slack.

## Fictional fixtures

`docs/screenshot_fixture.py` supplies the isolated profile, fictional Mira, Jonas, Lotte, workspace, DM, notice and draft. Its UI path stages a Core channel proposal and uses a loopback Slack stand-in; its `showcase share` and `showcase answers` operations are documentation-only fixture commands. They are not installed plugin commands. The fixture’s network fence and profile checks are source evidence, not proof that a particular capture ran safely. The existing plan already expresses these useful states and is retained.

## Source-bound UI surface inventory

- `pyproject.toml` declares both `heinzel.modules` and `heinzel.connected_sources` entrypoints as `slack = "heinzel_slack"`. The actual module in `src/heinzel_slack/_module.py` is `Module("slack", ...)`; `src/heinzel_slack/__init__.py` registers settings, transport, service, `SlackChannel`, and the read/write `chat` adapter. `src/heinzel_slack/_adapter.py` implements channel messages and posting plus self notifications and questions. These capabilities can feed Core and Slack surfaces; the declarations alone do not establish a dedicated plugin route.
- `src/heinzel_slack/__init__.py` declares `manifest`, `notify`, `ask`, `status`, `wait`, `listen` and private `info` operations, a scheduled listener, static `@module.info`, health checks and optional setup. They can contribute to generic Core operation, information, Doctor and setup surfaces as well as CLI output. Their exact Core layouts and routes are not supplied here, so do not invent screens or classify all operations as terminal-only. No first-party Page, View, navigation or footer contribution is declared in the inspected module; that absence alone does not rule out generic Core UI.
- `src/heinzel_slack/_channel.py` declares `SlackChannel` as both `NotificationChannel` and `ApprovalChannel`, with target review, delivery, posting and reply methods. `docs/screenshot_fixture.py` explicitly stages the Core review on `/` and checks its target and pending action, providing the source-bound basis for the two Core feature scenes. The actual captured rendering and selector success remain to be verified.
- Slack itself is an **external provider UI**: `src/heinzel_slack/_blocks.py` constructs notice and approval message blocks, and the README describes Slack DM buttons. The terminal drawing in `docs/screenshot_fixture.py` is not that provider UI. No genuine Slack screenshot is claimed.
- `src/heinzel_slack/links/__init__.py` declares a separate `Module("links", ...)` and conditionally registers `SlackReviewedLinks` only when the Core contract and active captured source are available; `src/heinzel_slack/links/_reviewed_link.py` implements the reviewed-link channel. The README calls its record `slack.links`, while `pyproject.toml` exposes only the `slack` entrypoints. Discovery of that separate record and any generic Core review surface is unresolved from these supplied declarations; do not invent a route or depict delivery as verified.
- `docs/screenshot_fixture.py` declares two documentation-only `showcase` operations rendered in a terminal. Their output is genuinely terminal-rendered fixture output, while the underlying draft also has an external Slack presentation. Neither output is a substitute for the two Core UI states.

## Privacy pitfalls

Use only the fixture’s example data, isolated profile and local stand-in. Inspect account IDs, message bodies, paths, timestamps, logs and all surrounding browser or terminal chrome for real identities, credentials and workspace details. For normal presentation fictionalization, verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance; unknown identities still fail and independent review must inspect every image and transcript. Do not imply that a local stand-in receipt confirms a real Slack post.

## Acceptance criteria

- Capture all four distinct scenes using the existing bootstrap, with applied light and dark appearances in the two Core UI states. The pre-confirmation scene shows the full review terms; the post-confirmation scene shows the actual delivery receipt.
- The CLI scenes show the generated fictional draft and the distinct decision cases as terminal results, clearly labeled as fixture demonstrations. Do not present them as Slack or Core feature UI.
- Reject duplicate captures, caption-only differences, forged HTML, invented routes, cropped-away material review terms, or claims of actual Slack delivery or approval.
- Independently inspect every image and transcript for privacy and truthfulness, including any Doctor details and paths. Unknown identities fail review. Verify selectors, applied appearance and the fixture’s observed results during explicit capture; source inspection alone does not establish capture success.
- The TOML below is structurally checked against the requested fields by inspection; no code, import, bootstrap, capture or runtime TOML validator was executed under the read-only instruction.
