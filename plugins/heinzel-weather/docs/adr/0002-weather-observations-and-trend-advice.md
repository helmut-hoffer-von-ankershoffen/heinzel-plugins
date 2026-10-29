---
status: proposed
date: 2026-10-28
related: 0001
---

# 0002: Weather observations and trend advice are read-only plugin inputs

## Context and Problem Statement

The weather plugin already fetches observations, caches app data for 15 minutes and detects rain, temperature
swings and alerts. Its watch job also records notices and remembers which changes it has noticed. A durable
workflow needs that weather evidence without consuming the job's deduplication state or creating a second notice.
Interpretation belongs in a plugin skill, using the core's checked `module.skill` API.

## Considered Options

- **A read-only observation operation and a packaged trend skill** (chosen).
- **Call the watch job from a workflow**: it changes notice state and can emit notices owned by the job.
- **Reimplement weather fetching or thresholds in the core**: this would couple the engine to one plugin and let
  the app and workflow disagree about the same observation.

## Decision Outcome

Chosen option: **a read-only observation operation and a packaged trend skill**, because the plugin owns weather
semantics while the engine owns grants, scheduling, durable drafts and approval.

- `weather.observe` returns the primary location's report, provider, fetched timestamp, stale state and candidate
  changes from the existing detector. It shares one in-process 15-minute observation with the app. A refresh failure
  retains the original timestamp and report, marks it stale and offers no actionable changes.
- Candidate windows are reassessed against the current clock on every read, including cache hits. An expired alert
  or forecast window cannot remain actionable until the next fetch; an entering window becomes visible without a
  provider request. This does not change the report or its original fetch timestamp.
- Cache expiry uses both monotonic attempt age and forward wall attempt age: a rollback cannot extend the elapsed
  deadline, and suspend cannot retain fresh status merely because the monotonic clock paused. Failed refreshes
  retain their own attempt timestamps, so old report timestamps do not cause retries on every app read.
- Missing location is explicit; no initial provider observation still raises the existing actionable error.
- Candidate change keys identify weather signals, not delivery receipts or approval authority. Reading does not
  emit a notice, consume a change, write a draft, run a model or alter the independent watch job.
- `weather-trend` is checked text shipped in the wheel. It asks for evidence, attribution and uncertainty, and
  distinguishes proposed Sheets and Docs edits from approved mail. It grants no operations or recipients.
- The public core stays generic. Scheduling this operation still requires a reviewed operation grant and engine
  integration; neither the skill nor plugin installation grants it. Durable deduplication, exact draft/recipient
  snapshots, human approval and external writes remain separate engine/adapter responsibilities.

### Consequences

- Good: an app and workflow in one process read the same evidence without duplicating provider requests.
- Bad: the cache remains process-local. A fresh process may fetch again; candidate signals are not a durable
  delivery guarantee. Open-Meteo provides no severe alerts, and an empty alert list is not a safety assurance.

### Confirmation

`observation_test.py` checks the cache boundary, stale/missing behavior and unchanged watch state.
`workflow_test.py` exercises the real CLI/API and checked Skills service with fake provider HTTP.
`skill_wheel_test.py` builds the wheel, then installs and reads it offline to verify packaged skill resources.
Building may fetch the declared build backend; the test is marked end-to-end.
