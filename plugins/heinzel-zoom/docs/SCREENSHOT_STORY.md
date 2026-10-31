# Recover decisions and next steps from meeting summaries.

The useful story is “a meeting ended; its decisions and owners are ready for the next workflow.” The plugin reads
Zoom summary emails through the bound `Mail` capability. It does not use Zoom's API, draw a video-call UI, record a
meeting, or retrieve a verbatim transcript. Its `Transcript` values are parsed summary sections and must be labeled
as summaries throughout the gallery.

## Runtime and command boundary

The released owning command is `hz zoom info`; useful reads are the public `Meetings.ended`, `transcripts` and
`transcript` methods consumed by a workflow. There is no released `hz zoom meetings` or `hz zoom transcript` command.
Register a **fixture-only** `showcase` requester in the documentation bootstrap using the public capability API,
based on `prep()` in [the integration tests](../tests/integration/capability_test.py). Proposed `showcase ended`,
`showcase said` and `showcase one` commands below exist only in that isolated demonstration.

Use the window `2026-10-01T00:00:00+00:00` to `2026-11-01T00:00:00+00:00`, with one summary titled “Weekly sync” and
another “Launch review”. Keep each summary concise enough that recap and next steps fit on screen.

## Required scenes, in gallery order

| Scene | Surface and actual action | Visible result and caption | Why it matters |
| --- | --- | --- | --- |
| Decisions at a glance | UI terminal: `hz showcase one sync` | Real parsed summary sections: Quick recap, Next steps, named owners and a source link. Caption: “Decisions and next steps from a Zoom summary email — fictional mailbox in the app terminal.” | Shows the outcome users want after a meeting. |
| Meetings available | UI terminal: `hz showcase ended` | Two actual `Meeting` results with titles, start/end and participant names. Caption: “Find recent summarized meetings through the meetings capability — fictional data.” | Shows how workflows find the right meeting. |
| Summary in the shell | CLI: `hz showcase one sync` | Readable summary and next-action list, with command and title visible. Caption: “Read a meeting summary in the shell — fixture-only requester, real Zoom parser.” | Demonstrates utility outside the graphical app. |
| Structured sections | CLI: `hz showcase ended --json` | One concise summary's actual segments and source identity. Caption: “Parsed summary sections for workflows and agents — not a verbatim transcript.” | Makes the typed automation interface concrete without overstating it. |
| Follow-up workflow | UI: seeded `/contracts/meeting-notes` | Actual shared contract page showing meeting-summary input and the meeting-notes output. Caption: “A local meeting-notes contract reads the summaries and tracks its output.” | Connects meeting context to a persistent team task. |

The workflow scene requires a real seeded contract. Verify `hz heinzel wake meeting-notes --dry-run` produces a
packet containing the fictional recap and next steps without running an agent or contacting Zoom. A contract page
is not proof of an AI-generated final document; do not label it that way.

## Fixture entry points

[conftest.py](../tests/conftest.py) already defines `Mailbox`, `email`, `SUMMARY` and the fictional “Weekly sync”.
Use the same public in-memory `Mail` adapter and bind `mail = "inbox"`, `meetings = "zoom"` only in this profile.
Retain the actual installed Zoom service and parser. Add the second summary via the same helper. Include one
ordinary newsletter or forwarded summary in the source mailbox and assert the real adapter excludes it.
The [integration contract](../tests/integration/capability_test.py) already demonstrates the complete dry-run packet.
Do not install or contact a real Google mailbox merely to demonstrate Zoom's mail dependency.

## Accessible capture and acceptance

- Open `button` **Open a terminal**, then **Full screen**. Wait for “Weekly sync” and “Next steps” after the real
  command finishes. The source link, recap and all selected next steps must be readable.
- On the shared contract page wait for `heading` **Meeting notes**. Verify its declared meetings input is present.
- Both the single-summary and windowed methods run through the actual Zoom adapter; two useful UI and CLI scenes
  are populated. Non-summary messages are absent and addresses in body text become the parser's `[address]`.
- Use fictional people only; no account emails, passcodes, session tokens, private meeting links, local hostnames
  or absolute machine paths reach any artifact. Keep only fixture source links without query or fragment.
- Captions always say “summary” where appropriate. Reject any “transcription”, “recording” or “live meeting” claim,
  empty lists, help screens or settings-only scenes as evidence of the plugin's useful behavior.

## Current captured scope

The window is fixed inside the documentation requester. The structured CLI scene uses `showcase ended --json`
for two concise typed meeting records; `showcase one sync` shows the actual parsed summary sections. A deliberately
ordinary newsletter is excluded by the real mail-query/summary path. The local meeting-notes contract is seeded
as a real, valid contract; its page declares source inputs and does not claim a generated final document.
