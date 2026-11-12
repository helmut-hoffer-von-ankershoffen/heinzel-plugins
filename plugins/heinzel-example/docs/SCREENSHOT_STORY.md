## Audience

Plugin authors evaluating a small, working reference for extending Heinzelmännchen.

## Outcome

Show how one example value appears across the host app and a plugin-owned view, alongside a typed greeting, JSON output, and a plugin notification. The gallery should make clear that this is a reference plugin, not a production data source.

## Scenes

1. **Widget and status:** The Today widget and sidebar both show the example value, 42.
2. **Inspector:** The plugin-owned panel displays the same value, demonstrating a custom view.
3. **Greeting in the app terminal:** Greet fictional Mira and show the structured JSON result without leaving the app.
4. **Notification:** Open the shared notification panel to show the seeded “Example is ready” notice.
5. **Greeting in the CLI:** Show the typed hello operation with fictional Mira as its parameter.
6. **Sample JSON:** Show the sample operation returning 42 in JSON, tying the CLI result back to the UI.

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap in an isolated demonstration profile. It seeds the plugin's own notice and disables native notifications. Mira is a fictional name; 42 is the plugin's constant example value.

## Privacy pitfalls

Capture with no connected accounts or real personal data. Inspect the app background, terminal, notification panel, and any host-provided labels for private paths, account names, credentials, or unrelated notifications before publishing.

## Acceptance criteria

- The six existing scenes remain recognizable and use actual plugin behavior and the declared inspector route.
- The widget, sidebar, inspector, and sample result consistently show 42; the greeting uses fictional Mira.
- The seeded notice is visible in the shared notification panel, and terminal commands finish with useful results.
- Captions identify the material as demo data; captures contain no private information.
- The TOML is structurally valid by inspection. Capture and runtime validation remain to be performed during an explicit capture; no code was executed here.
