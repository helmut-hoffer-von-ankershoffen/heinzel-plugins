## Audience

Plugin authors evaluating a small, working reference for Heinzelmännchen extensions.

## Outcome

Show how one sample value travels from an operation into the Today widget, sidebar and plugin-owned view, alongside a greeting operation and an in-app notification. The plugin is a teaching example, not a source of real metrics.

## Scenes

1. **Widget and status:** See the sample value 42 in the Today widget and sidebar.
2. **Inspector:** Open the plugin-owned view and see the same value.
3. **Greeting in the app:** Run a greeting for fictional Mira in the native terminal and show its JSON result.
4. **Notification:** Open the shared notification panel to see the seeded example notice.
5. **Greeting in the CLI:** Show the same greeting as a command-line result.
6. **Sample JSON:** Show the sample operation returning 42 in JSON for scripts and agents.

## Fictional fixtures

Mira is a fictional name; 42 is the plugin's constant sample value. The existing `docs/screenshot_fixture.py` seeds the plugin's notice in an isolated profile and configures notifications for the demonstration. The plan preserves the existing scenes and bootstrap.

## Privacy pitfalls

Capture only with a temporary profile and no connected accounts. Check the app, terminal output and notification panel for real names, paths, credentials, unrelated notifications or other personal data before publishing. The bootstrap disables native notifications for the capture profile.

## Acceptance criteria

- The widget, sidebar and inspector visibly agree on 42.
- The native terminal and CLI show the fictional greeting; the sample CLI scene shows JSON output.
- The notification panel shows the seeded example notice.
- Captions identify demonstration data, and no screenshot implies that 42 is a real metric.
- Review the rendered captures and contact sheet for readability and private data before publication.
- The plan has been checked against the supplied field rules and source; capture and runtime validation were not performed because code execution was excluded.
