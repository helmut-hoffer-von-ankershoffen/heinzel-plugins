## Audience

Plugin authors evaluating a small, working Heinzelmännchen extension and curious users who want to see what installing it adds.

## Outcome

Show how one sample value travels from an operation into the Today widget, sidebar and plugin-owned inspector, then show a typed greeting, a notification and machine-readable CLI output. The plugin is a teaching reference; the value 42 and the greeting are demonstrations, not claims about a production integration.

## Scenes

1. **Widget and status, light:** The Today widget shows “Example value” and the sidebar shows “Example: 42.” This establishes the shared sample data in two Core-rendered contributions.
2. **Inspector, dark:** The actual Example pane displays 42. This is a second useful feature UI state and demonstrates the navigation target and plugin-owned view.
3. **Greeting in the native terminal:** Run the greeting with fictional Mira and JSON output inside the app. This is an app-terminal result, not a plugin feature view.
4. **Notification:** Open the shared notifications panel to show the fixture-seeded “Example is ready” notice. The panel is Core UI populated by the plugin contribution.
5. **Greeting CLI:** Show the typed greeting for fictional Mira in a standalone CLI capture.
6. **Sample CLI JSON:** Show the sample operation's JSON result, connecting the CLI to the value in the UI.

The light and dark scenes must show the requested appearance actually applied. Reject duplicate captures, caption-only changes, terminal output presented as feature UI, and forged HTML.

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap with an isolated demonstration profile. It disables native and several system notification sources and seeds the plugin's own notice; it does not define a separate fixture file. Mira is a fictional greeting input, and 42 is the actual constant returned by `sample`. The notice is seeded rather than evidence of a user completing the notification confirmation flow.

## Source-bound UI surface inventory

- `pyproject.toml` declares the sole `heinzel.modules` entry point, `example = "heinzel_example"`. `src/heinzel_example/__init__.py` declares `Module("example", ...)`, settings, service, `info`, `sample`, and the state-changing `notify` operation. `src/heinzel_example/hello/__init__.py` declares the discovered `hello` submodule and its typed `hello` operation; the README documents its collapsed `hz example hello` command.
- `src/heinzel_example/__init__.py` declares a Core-rendered Today `widget` and footer/sidebar `status`, both sourced from `sample`; its `action` and `nav` navigate to `/?panel=example:inspector`. Its `view` declares that actual panel route, and `src/heinzel_example/views/index.js` renders its Example region and data. The widget and inspector are genuine feature UI, not terminal substitutes.
- The same module's `notify` emits a plugin notice to the shared notification UI after ordinary operation confirmation. The fixture invokes it directly to seed the notice, so the capture must not imply the confirmation was exercised. `system_info` contributes plugin details to `hz system info`; settings are declared by `ExampleSettings` in `src/heinzel_example/_models.py`. Core may render operation, confirmation, settings or information surfaces, but these provided files do not establish their precise routes or layouts; none is invented in the plan.
- No channel, setup or external-provider UI is declared in the supplied plugin sources. The CLI and app terminal are output surfaces, not evidence that an operation has no Core-rendered UI. The README mentions a health check, but no plugin health-check declaration appears in the supplied module sources; that discrepancy remains unresolved. The README also references tests and a wider author guide that were not provided, so their behavior is not assumed.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript. Inspect for account names, paths, hostnames, credentials, notification contents and other identifying data; dismissing Doctor where offered is not proof that the remaining capture is private.

## Acceptance criteria

- Capture the six distinct planned scenes from the real app and CLI using the existing bootstrap and fictional profile. Verify the widget and sidebar, inspector, seeded notice and both CLI results against their actual outputs.
- Confirm that light and dark appearances are applied, that the inspector and Today/status captures are useful feature UI, and that the app-terminal capture is labeled as such. Do not substitute fabricated screens or caption changes for distinct states.
- Verify commands complete successfully, the greeting and JSON output match the installed plugin, and the notification is represented as seeded. Investigate any mismatch rather than editing the displayed result.
- Independently review every image and transcript for privacy, including the narrowly permitted path and Doctor hostname mappings. Unknown identities fail review. The source-only plan is structurally checked against the requested format; capture, runtime behavior and privacy acceptance remain to be verified during explicit capture.
