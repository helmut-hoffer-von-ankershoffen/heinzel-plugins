## Audience

People deciding whether Zoom meeting summaries can feed their Heinzelmännchen workflows without granting a Zoom API credential.

## Outcome

Show how a workflow can request meeting context, then show actual parsed decisions and next steps from two fictional emails. The result is a summary, not a verbatim transcript. Zoom must email the summaries, and a mail adapter must be bound; the plugin reads through that adapter (`README.md`, `src/heinzel_zoom/_adapter.py: Zoom`).

## Scenes

1. **Workflow list, light:** the fictional Meeting notes contract appears among Core workflows. It demonstrates a declared need for meeting summaries, not a completed report.
2. **Workflow context, dark:** the same contract's detail shows its summary input and Markdown output. This is a meaningfully different state of the workflow, with no generated report implied.
3. **Weekly sync:** the fixture requester's native CLI result shows the parsed recap, named next steps and source link.
4. **Launch review:** the same operation with a different meeting ID shows a different rollout decision and next steps.
5. **Meeting list JSON:** the fixture requester's windowed result shows fictional meeting metadata, distinguishing the list from the summary sections.

The two UI scenes use applied light and dark appearances. Capture them as genuine Core views, not recreated HTML or terminal output. The existing detail route is retained from `docs/screenshots.toml`; its availability and rendered content must be confirmed during capture because Core's routing implementation is not among the provided sources.

## Fictional fixtures

`docs/screenshot_fixture.py` declares the local `inbox` mail adapter, `showcase` requester and Meeting notes contract. Its two fictional summaries name Mira, Jonas and Priya Example; a newsletter exercises filtering. `showcase.one` calls the real meetings adapter for `sync` or `launch`, while `showcase.ended` lists the fixed October window. The contract is a declaration only. Bootstrap runs only during explicit capture, in an isolated profile with no connected accounts.

## Source-bound UI surface inventory

- `pyproject.toml` declares one `heinzel.modules` entry point, `zoom = "heinzel_zoom"`. `src/heinzel_zoom/__init__.py` registers settings, service, the read-only `meetings` provider, the `info` operation, system info, offline health and live connector health. `src/heinzel_zoom/_module.py` declares its `mail:read` requirement. No plugin Page, View, navigation, channel, approval, setup or footer contribution is declared in these provided files; that absence alone does not rule out Core-rendered UI.
- Core workflow list and contract detail are feature UI using the fixture's actual contract declaration (`docs/screenshot_fixture.py: CONTRACT`; `docs/screenshots.toml: workflow-list, workflow-context`). The provided source does not establish that the detail route currently resolves, so capture must verify it. These views demonstrate workflow configuration, not a parsed meeting or generated report.
- The `info` operation and `system_info` contribution expose plugin, version, modules, source and query (`src/heinzel_zoom/__init__.py: info, system_info`; `src/heinzel_zoom/_service.py: ZoomService.about`; `src/heinzel_zoom/_models.py: ZoomAbout`). Health contributes summary source, mail and meetings binding checks; live health lists recent matching messages on demand (`__init__.py: health, live`; `_service.py: checks, live`). Core may render these contributions in generic UI; the provided files do not establish its routes or presentation. Do not claim they are terminal-only or invent a screen.
- The fixture's `showcase.one`, `ended` and `said` are operations, with custom Rich renderers for the first two (`docs/screenshot_fixture.py`). Their CLI output is useful and genuine, but possible Core rendering of operations is unresolved. The plan does not present their terminal output as feature UI.
- Zoom's settings portal is external provider UI (`README.md: Set up`; `src/heinzel_zoom/_models.py: SUMMARY_SETTING`), not a plugin or Core screen. The plugin's query setting is a Core-facing settings contribution (`__init__.py: module.settings`; `_models.py: ZoomSettings`); no route is established here. The provided source declares no plugin-owned navigation route.
- The README calls the returned object a transcript while explaining that it contains summary sections, not a verbatim record; captions must preserve that distinction. The fixture contract's goal describes a review, but its own text explicitly says no report has been generated.

## Privacy pitfalls

Use only the isolated fictional mailbox and contract. Parser protections include address replacement, removal of addresses from names, and stripping query strings and fragments from Zoom links (`src/heinzel_zoom/_summary.py`, `src/heinzel_zoom/_text.py`); they do not establish that screenshots or transcripts are private. Normal presentation fictionalization maps verified owning-interpreter paths to `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row to `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail. Independent review must inspect every image and transcript for identities, paths, tokens and other sensitive content before publication.

## Acceptance criteria

- Capture both genuine workflow states with their stated applied appearances, and verify the detail route and meaningful content. Stop and resolve any missing route or surface instead of fabricating it.
- Show the two different `showcase.one` parameter cases and the windowed list as genuine completed CLI results. Confirm fictional decisions, next steps and metadata match the fixture; do not describe them as verbatim transcripts.
- Reject duplicate captures, caption-only changes, terminal output presented as feature UI, and forged HTML. Every caption identifies demo data; no scene implies a report was generated or a real mailbox was consulted.
- Independently inspect every image and transcript, apply only the verified presentation mappings above, and fail on unknown identities. Verify health status and all remaining Doctor detail are unchanged.
- The TOML below preserves the existing five-scene plan. Its syntax and declared fields have been checked by inspection only; capture, route resolution, appearance application and privacy acceptance remain unverified.
