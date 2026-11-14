## Audience

Someone considering a private Slack notification and draft-approval channel for Heinzelmännchen, who wants to understand both the review experience and what an approval actually means.

## Outcome

Show Mira reviewing the exact terms of a fictional notice in Core, then seeing the delivery receipt after confirmation. Follow with a terminal rendering of a separate fictional draft and the decision code’s responses to several clicks. The delivery receipt is evidence from a local Slack stand-in, not a live Slack delivery or approval of a captured write.

## Scenes

1. **Review the notice — light UI.** In Core’s chat, Mira sees the fictional posting account, destination, scope and complete weekly-report notice before deciding whether to deliver it. This is the pending state staged by `docs/screenshot_fixture.py`, not a Slack screen.
2. **See the result — dark UI.** After confirmation in the same flow, Core reports that the local stand-in delivered the notice. This distinct result state makes the consequence of the review visible; it does not represent draft approval.
3. **Inspect a draft — CLI.** The fixture’s `showcase share` operation renders the actual generated message blocks and button labels as terminal output. It illustrates the draft content, but is neither Slack’s UI nor an interactive approval screen.
4. **Compare decisions — CLI.** `showcase answers` exercises the decision code with fictional owner, stranger, stale, replayed and late interactions. The result shows the recorded owner decision alongside refusals. These two showcase commands are fixture-only operations, not shipped `hz slack` commands.

## Fictional fixtures

`docs/screenshot_fixture.py` supplies the existing isolated-profile bootstrap, fictional Mira, Jonas and Lotte, the demo workspace and weekly report, a local Slack stand-in, and the two `showcase` operations. The UI fixture stages a real Core proposal and uses a loopback transport; the CLI fixture records posts locally and invokes the plugin’s decision code. Capture only when explicitly requested, using that bootstrap and its private-profile safeguards. No new fixture or product screen is assumed.

## Source-bound UI surface inventory

- `pyproject.toml` declares both `heinzel.modules` and `heinzel.connected_sources` entry points as `slack = "heinzel_slack"`. `src/heinzel_slack/_module.py` declares `Module("slack", ...)`; `src/heinzel_slack/__init__.py` registers settings, transport, service and `SlackChannel`, plus operations `info`, `manifest`, `notify`, `ask`, `status`, `wait` and `listen`. These are operation contributions; their presence alone does not establish a dedicated plugin route or that their output is terminal-only.
- The same `__init__.py` declares static system info, local and live health checks, optional setup and a scheduled listener. These can contribute to Core-rendered information, Doctor and setup surfaces; the supplied source does not establish their exact rendered navigation or appearance. No plugin Page, View, navigation or footer declaration is present in the supplied first-party declarations. That absence does not rule out Core-generated feature UI.
- `src/heinzel_slack/_channel.py` provides the notification and approval channel; `docs/screenshot_fixture.py` stages its source-bound notice through Core’s proposal and confirmation flow at `/`. The pending review and delivery result are genuine Core feature UI states. The fixture’s assertions establish the expected review terms and receipt, while actual screenshot rendering remains to be verified.
- `src/heinzel_slack/links/__init__.py` declares a separate `Module("links", ...)` and conditionally registers `SlackReviewedLinks` when the reviewed-link contract and active source capture are available. `src/heinzel_slack/links/_reviewed_link.py` implements that channel. `README.md` describes the `slack-reviewed-links` workflow and its separate safeguards; the supplied fixture does not stage a reviewed-link scene, so this plan makes no visual or live-delivery claim for it.
- Slack itself is external provider UI. `src/heinzel_slack/__init__.py` declares `ask` and `manifest`, while the README describes Slack’s draft buttons and app setup. The fixture’s terminal drawing of blocks is a representation of generated content, not a capture of Slack. The source does not establish that the underlying draft behavior is terminal-only.
- `docs/screenshot_fixture.py` declares `showcase share` and `showcase answers` as documentation-only CLI operations. Their useful output is genuinely terminal output from the fixture; neither is presented as feature UI.
- `README.md` says installed acceptance against the released SDK and a new gallery review are pending, and existing captures illustrate earlier behavior. The source declares `manifest()` reading `src/heinzel_slack/manifest.json`, but that file was not present in the supplied file inventory; its contents and successful rendering therefore remain unresolved. No capture in this plan depends on it.

## Privacy pitfalls

Use only the fictional fixture identities and content. Normal presentation fictionalization maps verified owning-interpreter paths to `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row to `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail; independent review must inspect every image and transcript for identifiers, credentials, paths, unexpected provider content and other leaks. Do not substitute a fabricated Doctor result or alter its health status.

## Acceptance criteria

- Capture the pending review and the confirmed delivery result as two useful, distinct states of the actual Core flow, with applied light and dark appearances respectively. Show the exact fictional review terms and the actual receipt; do not use duplicate captures, caption-only changes, forged HTML or terminal output as feature UI.
- Capture both fixture CLI cases as terminal results, clearly labelled demo data. Preserve the distinction between the rendered Slack blocks and the provider’s actual interface, and between notice delivery and draft approval.
- Keep captions truthful and within 180 characters. Do not claim live Slack delivery, released-SDK acceptance or privacy acceptance from the fixture.
- Independently inspect every image and transcript after capture. Reject unknown identities and any unexpected sensitive data. Confirm the source-bound mappings only where their complete original values have been verified.
- The existing plan already expresses these behaviors and is preserved below. Its TOML structure has been inspected against the requested format; parsing and capture were not executed because the request prohibits code execution.
