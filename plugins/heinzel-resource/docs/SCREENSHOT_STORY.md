## Audience
People who want a quick picture of the machine running their helper, and those who want the same measurements in scripts or agent workflows. The plugin is included in the standard app.

## Outcome
See the fictional workstation’s CPU, memory and load at a glance, open the footer for context, and inspect the same sample in readable and structured terminal output. Load is queued work; the footer bar is scaled against twice the logical core count.

## Scenes
1. **Resources panel:** Open the footer control for CPU, memory, one-minute load and core count, with the load explanation in context.
2. **Today:** Show the CPU summary alongside the footer control for a quick everyday check.
3. **Phone:** Open the same resource details at a narrow viewport.
4. **CLI:** Show the readable resource table.
5. **App terminal:** Run `hz resource` for the readable result.
6. **App terminal JSON:** Run `hz resource --json` to show the structured result useful for automation.

## Fictional fixtures
The existing `docs/screenshot_fixture.py` supplies a fixed `demo-workstation` sample: CPU 36%, memory 62%, one-minute load 0.65 and 8 logical cores, sampled at 2026-10-31 10:00 UTC. It replaces the sampler during capture; these values are examples, not live measurements.

## Privacy pitfalls
Capture only with the isolated fictional profile and fixture. Check the images and terminal output for real hostnames, machine metrics, account details or unrelated terminal history before sharing. Captions must identify the data as fictional or demonstrative.

## Acceptance criteria
- All six existing scenes remain represented, with at least two useful app views and a readable CLI result.
- The expanded panel, Today summary and phone view show the fictional sample consistently; the panel explains scaled load without presenting it as a CPU percentage.
- Both native terminal examples finish and show useful results, including structured JSON for the second case.
- Captions identify demo data, and captures contain no real machine or account information.
- The plan uses the existing bootstrap and supported routes and actions. Its TOML structure was checked by inspection; no parser or capture was run because code execution was excluded.
