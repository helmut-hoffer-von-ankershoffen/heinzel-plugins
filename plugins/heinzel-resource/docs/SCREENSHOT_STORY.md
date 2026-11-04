## Audience

People deciding whether they want a quick view of the machine running their Heinzel helper, plus people who may use the same measurements in automation. The plugin is included in the standard app.

## Outcome

Show how CPU, memory and load are available at a glance, how to inspect their meaning, and how to retrieve the same sample as readable output or JSON. The measurements describe the helper's host, which may differ from the device viewing the app.

## Scenes

1. **Expanded monitor:** A focused view of the fictional workstation's CPU, memory, one-minute load and logical cores, including the explanation of the scaled load bar.
2. **Today:** The CPU summary in context, with the resource status control in the footer.
3. **Phone:** The expanded resource details at a narrow viewport.
4. **CLI:** The readable resource table with the same fictional measurements.
5. **App terminal:** The readable resource result in the native terminal.
6. **App terminal JSON:** The structured result for someone considering automation.

## Fictional fixtures

The existing `docs/screenshot_fixture.py` supplies `demo-workstation`, CPU 36%, memory 62%, one-minute load 0.65, eight logical cores and a fixed sample time. The plan uses that existing bootstrap and a matching browser time. No additional fixture files are needed.

## Privacy pitfalls

Real samples expose the helper host's hostname and resource usage. Capture only with the fictional bootstrap and temporary profile, and inspect every image and terminal result for real hostnames, account details or other unrelated private data before publication.

## Acceptance criteria

- All six scenes show the intended view or completed result, with readable demo data and no unrelated private information.
- The expanded monitor identifies raw one-minute load separately from the scaled footer bar; captions do not imply the expanded panel contains scaled-load bars.
- Today, phone and terminal scenes communicate useful behavior without relying on settings or plugin cards.
- The two native-terminal cases show the readable and JSON forms of the single resource operation.
- The plan preserves the existing routes, actions and fixture. Its TOML and requested fields have been checked by inspection; capture and runtime validation were not performed.
