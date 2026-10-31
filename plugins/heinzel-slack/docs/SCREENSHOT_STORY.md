**Audience.** People who already work in Slack and want helpers to bring drafts to their own DM for a clear, accountable answer.

**Outcome.** See the draft before deciding, then understand why only the owner's button press counts. Installation requires a private Slack app, two tokens and a core version carrying the channel ports; the README explicitly excludes core 0.9.8 itself.

**Scenes.**

1. **Read before saying yes** (`draft-in-slack`). The app terminal shows the existing fixture's readable draft preview, rendered from the plugin's Slack message blocks. Keep the fictional weekly report, fingerprint, expiry and printed Approve/Decline labels visible. This is a terminal representation, not a Slack screenshot or working Slack buttons.
2. **Watch the boundary hold** (`who-can-approve`). The app terminal shows synthetic clicks processed by the real decision code: Jonas is refused, a mismatched fingerprint is refused, a typed reply is refused, Mira's approval is recorded, a replay is refused and a late click expires. The host receives one approval reply. Approving the preview does not demonstrate sending the report.
3. **One answer stays one answer** (`answers-cli`). Rerun the same synthetic clicks in the CLI against the shared fixture state. Mira's previously accepted click is now refused as already approved; the host still receives one reply, and the late request is already expired. Label this explicitly as a replay demonstration.

**Fictional fixtures.** Use only the existing `docs/screenshot_fixture.py`: helper Lotte, owner Mira, teammate Jonas, the November weekly report and its fixed demonstration identifiers. Its clock starts at 2026-11-02 09:00 UTC. `DemoSlack` records posts locally, and synthetic payloads replace real Slack clicks. Start each complete capture with fresh isolated state, then retain that state across all three scenes in order.

**Privacy pitfalls.** Keep personal configuration, real Slack identifiers, tokens and unrelated terminal history out of frame. Real use sends draft content to Slack and stores it locally in the approval database. These screenshots prove neither Slack connectivity nor report delivery. Control of the owner's Slack account or machine remains control of their approvals.

**Acceptance criteria.**

- Two useful app-terminal views and one useful CLI result; every caption identifies demo data.
- The draft is readable, and the first verdict table includes one recorded approval, one host reply and an expired late click.
- The CLI replay retains one host reply and shows the approval and expiry were already recorded. Add no waits for individual table cells.
- Run `share` exactly once: its fixed request ID suppresses a second post, while its renderer expects a newly recorded post. Remove the existing final `share-cli` scene for this reason; preserve the other scene names and useful behavior.
- Bootstrap runs only during explicit capture, without real Slack credentials. Reset isolated state before repeating the complete capture.
- TOML syntax and requested field constraints were checked statically against the supplied files. No plugin code or capture was run. The supplied snapshot omits the imported `_blocks.py`; successful bootstrap and visual verification remain capture acceptance gates.
