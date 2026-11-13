## Audience

Someone deciding whether to connect their own Slack workspace to Heinzelmännchen, especially someone who wants to see what is reviewed before a notice is sent and how a draft decision is tied to its text.

## Outcome

Show a small, honest journey: Mira reviews a fictional notice and its exact Slack destination in Core, confirms delivery to a local stand-in, then sees a fictional draft and examples of accepted and refused decisions in terminal output. The story illustrates the safeguards and their limits; it does not claim a live Slack installation or a captured-write approval.

## Scenes

1. **Review the notice — light.** In Core’s actual review flow, show the fictional account, destination, scope and complete notice before confirmation. This is a Core feature UI produced by the channel flow, not a Slack screen. The fixture stages it through Core’s proposal APIs (`docs/screenshot_fixture.py`, `stage_notice`).
2. **See the delivery receipt — dark.** Confirm the same staged notice and show Core’s receipt from the local Slack stand-in. This is a different, useful state of the same flow: delivery of the notice does not approve a captured write (`docs/screenshot_fixture.py`, `StandIn` and `stage_notice`).
3. **Inspect the draft — CLI.** Show the fictional weekly report and Approve/Decline labels rendered from the blocks the real channel produces. This is a documentation-only terminal rendering, not Slack’s UI (`docs/screenshot_fixture.py`, `showcase.share` and `message_view`; `src/heinzel_slack/_blocks.py`).
4. **See decisions checked — CLI.** Show the owner’s accepted click alongside refused stranger, stale-draft, typed-reply, replay and expired examples. The fixture calls the real decision code with synthetic payloads; it does not demonstrate a live Slack click (`docs/screenshot_fixture.py`, `showcase.answers`; `src/heinzel_slack/_decide.py`).

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap and its isolated capture profile. Mira, Jonas, Lotte, the workspace, IDs, notice and weekly report are fictional. The UI uses a loopback Slack stand-in; the CLI uses an in-memory transport. The two `showcase` commands are documentation-only fixture operations, not advertised plugin commands. No fixture or provider screen needs to be invented.

## Source-bound UI surface inventory

- **Declared entrypoints:** `pyproject.toml` declares both `heinzel.modules: slack` and `heinzel.connected_sources: slack` as `heinzel_slack`. Their target declares `module` in `src/heinzel_slack/_module.py` and registers settings, transport, service and channel in `src/heinzel_slack/__init__.py`. The source also defines a separate conditional `links` module and `SlackReviewedLinks` service in `src/heinzel_slack/links/__init__.py` and `src/heinzel_slack/links/_reviewed_link.py`. The README describes a `slack.links` module record, but no separate entrypoint for it appears in the provided `pyproject.toml`; how it is discovered remains unresolved.
- **Core feature UI:** The channel’s notice/approval ports and reviewed targets are declared by `SlackChannel` in `src/heinzel_slack/_channel.py`. The existing fixture stages a genuine Core chat proposal and confirmation at `/`, including the exact destination and receipt (`docs/screenshot_fixture.py`, `stage_notice`). These two states supply the feature UI scenes; the absence of a plugin Page or View declaration would not establish that no UI exists.
- **External provider UI:** Slack receives message blocks with notice text or draft buttons (`src/heinzel_slack/_blocks.py`, `src/heinzel_slack/_service.py`). Slack’s actual DM is an external provider surface. The fixture’s Rich rendering is terminal output and must not be presented as a Slack screenshot.
- **Operations and generic Core surfaces:** `src/heinzel_slack/__init__.py` declares `manifest`, `notify`, `ask`, `status`, `wait`, `listen`, private `info`, scheduled `listen_job`, health checks, optional setup and `@module.info` metadata. These can contribute command, setup, health or information surfaces through Core; the provided sources do not establish their exact generic web routes or renderings. No plugin navigation, page, view or footer contribution is declared in the inspected first-party module sources. Do not infer a plugin route or terminal-only status from that absence.
- **Reviewed links:** The conditional reviewed-link channel can contribute to a host review flow, but the supplied fixture does not stage that flow. `README.md` says live account delivery and installed acceptance remain unverified; do not fabricate a scene for it. The README also marks released-SDK installed acceptance and a new gallery review as pending. `manifest()` references `src/heinzel_slack/manifest.json`, which is not among the provided files, so its contents and successful rendering cannot be verified here.

## Privacy pitfalls

Use only the isolated fictional profile and inspect every image and transcript for credentials, real account or workspace identifiers, local paths, hostnames, message contents and other identifying details. Normal presentation fictionalization is explicitly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail; independent review must inspect every image and transcript.

## Acceptance criteria

- Preserve the four existing distinct scenes and their source-supported behavior; the two Core UI states are genuine, useful feature scenes, with applied light and dark appearances. The two CLI results show different useful fixture operations.
- Capture the real Core interface and actual terminal output. Reject forged HTML, terminal output presented as feature UI, duplicate captures and caption-only variations. Label every scene as demo data.
- Before confirmation, the full fictional notice and account, destination and scope must be legible. After confirmation, the receipt must accurately describe delivery to the local stand-in and must not imply approval of a captured write.
- The draft and decision scenes must remain faithful to the fixture’s real rendered blocks and decision results. Do not claim live Slack delivery, live button interaction, released-SDK acceptance or privacy acceptance.
- Capture only after explicit authorization to run the existing bootstrap. Independently review every resulting image and transcript; fail on unknown identities or unsupported redactions. The plan below preserves the existing TOML and is structurally checked against the requested format by inspection; execution and capture validation were not performed.
