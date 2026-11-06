## Audience

Someone considering Slack as a private notification channel and a way to collect an owner’s decision on an exact draft.

## Outcome

Show the distinction between reviewing a Slack delivery in Heinzelmännchen, delivering a notice to a local stand-in, and receiving a separate owner decision on a draft. The plugin is in development; `README.md` says installed acceptance against the released SDK and a new gallery review are pending. These scenes do not establish live Slack delivery or installed acceptance.

## Scenes

1. **Review the notice — light UI.** In Core’s actual chat review, Mira sees the fictional account, destination, scope and complete notice before confirming. This is a genuine Core feature surface staged by `docs/screenshot_fixture.py`, not a Slack screen.
2. **Delivery receipt — dark UI.** After confirmation, the same flow reports delivery to the local Slack stand-in. The receipt explicitly says this does not approve a captured write. This is a meaningful subsequent state, not a duplicate capture.
3. **The draft — CLI.** The fixture renders the plugin-produced Slack message blocks as terminal text, including the fictional draft and printed button labels. It is a terminal representation, not an interactive Slack screenshot.
4. **The decisions — CLI.** A second fixture operation exercises decision handling for the owner, a stranger, a stale button, typed text, replay and expiry. It shows a recorded owner reply and refusals without implying a live Slack interaction.

The existing plan already tells this story, so its scenes and capture actions are preserved. The fixture operations are documentation-only demonstrations, not installed `hz slack` commands.

## Fictional fixtures

`docs/screenshot_fixture.py` supplies Mira, Jonas, Lotte, a demo workspace, synthetic IDs and a weekly report. Its UI bootstrap stages a real Core review and uses a loopback Slack stand-in; its CLI demonstrations use an in-memory transport and actual plugin channel and decision code. The fixture fences network access and subprocesses when it runs. Capture must use the existing isolated bootstrap; no fixture file is invented here.

Normal presentation fictionalization is explicitly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript.

## Privacy pitfalls

Review every image and transcript for real workspace, member, account and DM identifiers; tokens, credential paths, local usernames, hostnames, URLs, message contents and unrelated application data. The fixture’s synthetic identifiers are acceptable only after verification against the fixture. Do not generalize the two presentation mappings to unverified strings or use them to conceal unexpected identities. Do not publish a failed or partially captured scene.

## Acceptance criteria

- Capture the actual light review and dark delivered states with the specified appearance applied; the account, destination, scope and full fictional notice must be readable in the review. The second image must show the actual delivery receipt and its limitation.
- Capture both distinct CLI results from the existing fixture. Clearly label the printed buttons as terminal output; do not present them as Slack UI or as live clicks.
- Reject duplicates, caption-only changes, forged HTML, missing review terms, unexpected identities and any screenshot or transcript that fails independent privacy review. Preserve the actual SDK health status and all detail outside the narrowly verified mappings.
- Treat capture and privacy acceptance as pending until the images and transcripts have actually been inspected. The plan below was checked against the supplied schema and source by inspection; it was not executed or capture-tested.

## Source-bound UI surface inventory

- `pyproject.toml`, `[project.entry-points."heinzel.modules"]` and `[project.entry-points."heinzel.connected_sources"]`, both declare `slack = "heinzel_slack"`. `src/heinzel_slack/_module.py` declares `Module("slack", ...)`; `src/heinzel_slack/__init__.py` registers settings, transport, service and `SlackChannel`, plus `manifest`, `notify`, `ask`, `status`, `wait` and `listen` operations, a scheduled listener, health checks, optional setup and system info. These declarations can contribute to Core-rendered operation, setup, information and health surfaces; the supplied source does not establish a plugin-specific navigation route or prove those operations terminal-only.
- `src/heinzel_slack/_channel.py` and `src/heinzel_slack/__init__.py` provide notification and approval channel behavior. The actual Core confirmation and resulting chat state are evidenced concretely by the staged `/` flow in `docs/screenshot_fixture.py`; they are the two feature UI scenes. The captured notice confirmation is distinct from approving a draft.
- Slack’s actual DM and its Approve/Decline controls are **external provider UI**: `src/heinzel_slack/_blocks.py` constructs message blocks, and `README.md` describes their use. The supplied fixture draws those blocks in a terminal, not in Slack; no genuine provider UI capture is established.
- `src/heinzel_slack/links/__init__.py` conditionally registers `SlackReviewedLinks` under `Module("links", ...)`, and `src/heinzel_slack/links/_reviewed_link.py` implements the reviewed-link channel. `README.md` calls this a separate `slack.links` module record, while the supplied `pyproject.toml` declares only the two `slack` entry points above. Discovery of that separate record and its corresponding Core review surface are therefore unresolved from these files; do not invent a route or scene for it.
- `@module.info`, `@module.health`, `@module.health(live=True)` and `@module.setup` in `src/heinzel_slack/__init__.py` are Core contributions; their exact UI placement is not established by the supplied source. No plugin page, view, navigation or footer declaration was found in the first-party declarations. That absence alone does not make channel or operation behavior terminal-only.
- `docs/screenshot_fixture.py` declares the documentation-only `showcase.share` and `showcase.answers` operations and their terminal renderers. They support the two useful CLI captures, but do not establish that the plugin’s broader behavior is CLI-only. `manifest()` reads `src/heinzel_slack/manifest.json`, which is absent from the supplied file inventory; manifest availability remains unresolved.
