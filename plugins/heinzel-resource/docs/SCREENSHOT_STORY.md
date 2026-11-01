Audience: People who want to check the machine running their helper from Today, a phone, or the terminal. This plugin is already included in the standard app.

Outcome: Move from a quick CPU glance to the underlying CPU, memory, load and core-count measurements. Make clear that these describe the host running hz, which may differ from the viewing device.

Scenes:
1. **The numbers behind the meters.** Preserve the expanded resource monitor, including its hostname and explanation of scaled load.
2. **A glance during everyday work.** Preserve Today’s CPU summary and compact footer meters.
3. **The same host on a phone.** Preserve the narrow viewport and expanded resource details.
4. **A readable CLI result.** Preserve the table showing hostname, CPU, memory, raw one-minute load and logical cores.
5. **Check from the app terminal.** Run `hz resource` in the native terminal to show the readable result in context.
6. **Numbers for automation.** Run `hz resource --json` in the native terminal to expose the structured sample, including its timestamp and problems list.

Fictional fixtures: Reuse only `docs/screenshot_fixture.py`. It supplies `demo-workstation`, CPU 36%, memory 62%, raw one-minute load 0.65, eight logical cores, no problems, and sampling time `2026-10-31T10:00:00Z`. Set the browser clock to that same instant. The load bar scales against twice the logical core count; it is not another CPU percentage. The existing fixture supports a healthy sample only, so do not stage warnings, history, or additional machines.

Privacy pitfalls: Real samples reveal the host’s name and resource measurements; JSON also reveals sampling time. Use the documented temporary profile without connected accounts and the existing bootstrap during explicit capture. Review surrounding Today content and terminal output for personal information. A phone capture must not imply that the phone itself is being measured.

Acceptance criteria:
- Retain the four existing useful scenes and their names; add only the two required native-terminal parameter cases.
- All six captions explicitly identify fictional or demonstration data. The expanded monitor, Today overview and mobile details must be readable.
- Both terminal cases and the standalone CLI capture must use the fixture. Reject captures containing live host values.
- Human-readable output shows the five documented table rows; JSON reflects the fixture’s fields. Terminal actions need no additional cell-text waits.
- Use only the existing `/` route, accessible interactions, and supported terminal actions. Do not invent a plugin panel or installation screen.
- The returned TOML was checked statically against the requested structure. Capture and executable validation were not run. The unsupported focus padding field was removed; the remaining existing interactions were preserved.
