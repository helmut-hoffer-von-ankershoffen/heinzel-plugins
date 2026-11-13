## Audience

Someone deciding whether Zoom meeting summaries can become useful, private-by-design context for Heinzelmännchen workflows without a Zoom API credential.

## Outcome

Show a fictional workflow that declares a need for meeting summaries, then show what the real Zoom adapter can extract from two fictional summary emails. A summary is not a verbatim transcript, and the workflow contract does not prove a report was generated. Zoom must email summaries to a mailbox served by a bound mail adapter. See `README.md` (Set up and Use), `src/heinzel_zoom/__init__.py` (`module.provides`) and `src/heinzel_zoom/_adapter.py` (`ended`, `transcripts`, `transcript`).

## Scenes

1. **Workflow context, light:** Open the fictional Meeting notes contract and show its meeting-summary input and Markdown output. This is Core workflow UI populated by the fixture, not a Zoom-owned screen or a completed report.
2. **Workflow discovery, dark:** Show the same fictional workflow in the Core workflow graph. This is a meaningful discovery state before opening its details; it is not a duplicate detail capture.
3. **Weekly decision:** In the native app terminal, use the fixture requester to show the fictional Thursday decision and three next steps parsed from Weekly sync.
4. **Recent meetings:** In the native app terminal, show the fictional October meeting list, including Weekly sync and Launch review.
5. **Launch decision:** In the native app terminal, use the other meeting argument to show the fictional ten-percent rollout decision and owners.
6. **Summary CLI:** Show the Weekly sync result as a CLI capture, including parsed sections and the source link.
7. **Meeting list JSON:** Show typed fictional meeting metadata as JSON, making clear that it is not a verbatim transcript.

The three app-terminal scenes are useful terminal results, not feature UI. The first two are genuine Core feature UI states. The existing plan already covers these distinct purposes, so it is preserved.

## Fictional fixtures

`docs/screenshot_fixture.py` provides an isolated documentation-only mailbox, a `showcase` requester, and the Meeting notes contract. Its `one`, `ended`, and `said` operations call the real installed meetings adapter; the plan uses `one` with both `sync` and `launch`, and `ended` in human-readable and JSON forms. The mailbox includes an unrelated newsletter; do not claim its exclusion is visible unless the capture demonstrates it. The contract is fixture data and declares a workflow; it does not execute one. `docs/SCREENSHOTS.md` describes the temporary fictional profile and capture process.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited to these mappings: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript.

Use only the local fictional fixture and inspect all visible names, addresses, paths, hostnames, links, terminal history, and surrounding app chrome. `src/heinzel_zoom/_summary.py` and `_text.py` describe address filtering and URL query/fragment removal, but those protections do not establish that an entire screenshot is private. The fixture contains example addresses and a fictional Zoom URL; do not imply that real mail was accessed. Do not alter health statuses or invent a successful connection.

## Acceptance criteria

- Capture the two distinct Core workflow states with light and dark appearance actually applied, plus the useful terminal and CLI results in the plan. Confirm the detail route and both rendered states during capture; stop and report any route or rendering mismatch rather than substituting a fabricated screen.
- Show the fixture's actual decisions and owners, with captions identifying demo data and the fixture-only requester. Do not imply that the contract generated a report or that summary segments are verbatim transcripts.
- Preserve the real adapter output and SDK health details apart from the narrowly disclosed presentation mappings. Independently review every image and transcript for unknown identities and sensitive surroundings.
- Reject duplicate captures, caption-only changes, terminal output labeled as feature UI, forged HTML, and screens or fixture files unsupported by the supplied source.
- Validate the plan with the capture tooling and review the resulting images before publication. This proposal was inspected as TOML text; no code, imports, network calls, or capture tooling were run, so runtime routes and captures remain unverified.

## Source-bound UI surface inventory

- `pyproject.toml` declares the sole `heinzel.modules` entry point, `zoom = "heinzel_zoom"`. `src/heinzel_zoom/__init__.py` registers settings, a service, the `meetings` read adapter, `info` operation, system info, offline health, and live connector health. `src/heinzel_zoom/_module.py` declares the `mail:read` requirement. No plugin Page, View, navigation, channel, approval, setup, or footer contribution is declared in these supplied files; that absence alone does not rule out Core-rendered surfaces.
- The operation, settings, info, health and connector declarations can contribute to generic Core surfaces. Their actual Core rendering and available controls are not specified by this plugin's supplied source. `README.md` documents `hz zoom info`, `hz system doctor`, and `hz system connector test zoom`; `_service.py` distinguishes offline checks from the on-demand mail-listing live check. Do not infer that these are terminal-only, or invent a plugin route from the name.
- `docs/screenshot_fixture.py` declares the fictional `showcase` operations and a local Meeting notes contract. The existing `docs/screenshots.toml` identifies `/contracts` and `/contracts/meeting-notes` as Core workflow surfaces; the supplied Core implementation is absent, so the detail route and its rendering need capture-time confirmation. The fixture requester commands have native terminal renderers, but the supplied source does not establish whether Core also exposes their operations elsewhere.
- Zoom's web portal is an external provider UI referenced by `README.md` and `src/heinzel_zoom/_models.py` (`SUMMARY_SETTING`); it is not a plugin or Core screen and is not included in the plan. The existing catalog's `ui` labels for app-terminal captures in `pyproject.toml` describe their capture surface, not a separate Zoom feature UI.
