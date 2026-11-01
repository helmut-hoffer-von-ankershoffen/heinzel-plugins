## Audience
Plugin authors deciding whether to install a small, working reference for extending Heinzelmännchen.

## Outcome
Follow the constant value 42 through a Today widget, sidebar status, plugin inspector and CLI result. Then see a typed greeting and a plugin notice. The benefit is an inspectable extension example, not a business dashboard.

## Scenes
1. **Widget and status:** show the demo value 42 in the Today widget and sidebar together.
2. **Inspector:** open the source-declared panel and show “The value is 42.” This connects a plugin-owned view to the same operation.
3. **Greeting terminal:** run `hz example hello --name Mira --json` in the native app terminal. With default settings, the result contains `{"text":"Hello, Mira!"}`.
4. **Plugin notice:** open Notifications and show the fixture-seeded “Example is ready” notice.
5. **Greeting CLI:** show the ordinary CLI result for the same fictional name.
6. **Sample JSON:** show `hz example sample --json` returning 42, completing the connection between UI and command output.

Preserve the existing six scenes, routes, commands and interactions. Only captions change to identify demonstration data explicitly.

## Fictional fixtures
Reuse the existing `docs/screenshot_fixture.py` bootstrap unchanged during explicit capture. It seeds the plugin notice and configures in-app notification behavior. Use the documented temporary fictional profile without connected accounts and retain the default greeting setting. Mira is fictional; 42 is the source's constant sample value. No additional fixture files are needed.

## Privacy pitfalls
Run the bootstrap only in the isolated capture profile: it loads configuration and emits a notice. Its native-notification suppression does not remove personal information already present in an existing profile. Check the shared sidebar, notifications and terminal for real account names, unrelated notices, paths or command history before accepting captures. Do not describe the seeded notice as evidence of desktop notification delivery.

## Acceptance criteria
- All six scenes render real supported surfaces, including two distinct useful UI views and completed CLI results.
- The widget and sidebar show 42; the inspector shows “The value is 42.”
- Both greeting results contain “Hello, Mira!” under the default setting; the native terminal displays structured output.
- The notification panel contains the seeded “Example is ready” notice, and the sample JSON result is 42.
- Every caption calls out demo data; no screenshot implies customer activity or production metrics.
- Screens are legible and free of personal data, errors and loading overlays.
- The plan was statically checked against the supplied contract for TOML structure, unique lowercase names, caption lengths, existing bootstrap path, supported actions, local routes and argument arrays. No code, imports, parser or captures were executed; runtime capture remains unverified.
