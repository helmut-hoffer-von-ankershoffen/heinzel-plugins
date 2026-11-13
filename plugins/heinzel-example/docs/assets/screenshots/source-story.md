## Audience

Plugin authors evaluating a small, working reference for Heinzelmännchen extensions.

## Outcome

See one value move from an operation into the Today widget, sidebar status, and an inspector pane; then see a typed greeting and a seeded notification. The examples show integration points to explore, not a production business workflow.

## Scenes

1. **Widget and status, light:** The Today widget and sidebar both show the sample value, 42. `src/heinzel_example/__init__.py` declares `sample`, `@module.widget(source="sample")`, and `@module.status(source="sample", slots={"footer": True, "sidebar": True})`.
2. **Inspector, dark:** The real Example pane displays 42. `module.nav`, `module.action`, and the status effect navigate to `/?panel=example:inspector`; `module.view(..., name="inspector", source="sample")` owns that pane, rendered by `src/heinzel_example/views/index.js`.
3. **Greeting in the app terminal:** Run the fictional Mira greeting with JSON output. This is a native terminal result, not a feature UI. `src/heinzel_example/hello/__init__.py` declares the collapsed `hello` operation; `_service.py` constructs the greeting.
4. **Notification:** Open the shared notification panel to see the seeded “Example is ready” notice. The `notify` operation in `src/heinzel_example/__init__.py` emits it; `docs/screenshot_fixture.py` seeds it in the isolated capture profile.
5. **Greeting CLI:** Show the same fictional greeting as a direct CLI result.
6. **Sample JSON CLI:** Show the source value as structured output, connecting the CLI to the widget and inspector.

## Fictional fixtures and presentation

Use the existing `docs/screenshot_fixture.py` bootstrap and its isolated profile; do not create fixture files. Mira is fictional, and 42 is the actual constant returned by `sample`. The notice is seeded demonstration data. Captions identify demo data.

Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript.

## Privacy pitfalls

The bootstrap disables native, Doctor, and release notifications and invokes the plugin notice in an isolated profile; it does not by itself prove that captures contain no personal information. Inspect paths, hostnames, account names, notifications, timestamps, terminal output, and other incidental content. Do not conceal unknown identities with assumed substitutions.

## Source-bound UI surface inventory

- **Plugin entrypoint:** `pyproject.toml` declares `heinzel.modules` entry `example = "heinzel_example"`. `src/heinzel_example/__init__.py` declares the root `Module("example", ...)`; `src/heinzel_example/hello/__init__.py` declares the discovered `Module("hello", ...)` submodule.
- **Genuine feature UI:** The Core-rendered Today metric and footer/sidebar status come from the widget and status declarations. The plugin-owned inspector is a real view at the declared panel target, implemented in `src/heinzel_example/views/index.js`. Its loading state and value are rendered using SDK React; it declares no action row. The same actual value across these surfaces is intentional, but the overview and inspector must remain visually and functionally distinct captures.
- **Other Core-rendered contributions:** `module.action` and `module.nav` open the inspector. `notify` contributes a plugin notice to the shared notification UI. `module.settings(ExampleSettings)` registers the `greeting` setting in `src/heinzel_example/_models.py`; `@module.info` contributes details to system info. The non-read-only `notify` operation declares an ordinary confirmation. These declarations can give rise to generic Core surfaces, but their precise layouts are not supplied here and must not be invented. No channel or setup contribution is declared in the supplied entrypoints.
- **Operations and terminal:** Root operations are `info`, `sample`, and `notify`; the hello submodule declares `hello`. CLI output is genuine terminal output, including when displayed in the app terminal, and is not evidence of a feature UI. `README.md` documents `hz example hello`, `hz example info`, JSON output, and system info; the source also declares `sample` and `notify`.
- **External provider UI:** None is declared in the supplied plugin source. No external provider screen is needed for this story.
- **Unresolved evidence:** `README.md` describes a health check, but the supplied module declarations contain no explicit health-check contribution; do not invent one. The README also references `tests/contributions_test.py`, which is not among the supplied files. Core implementation and the screenshot author guide are not supplied, so generic surface details and capture behavior require observation during explicit capture. The existing plan is preserved because it already covers two real feature UI scenes, a notice, and useful CLI results.

## Acceptance criteria

- Capture all six planned scenes from the real app or CLI with the existing bootstrap, and confirm the light overview and dark inspector have their requested appearances applied.
- Verify the overview and inspector each show the actual sample value and are distinct views, not duplicates or caption-only variants. Verify the notification is present and the greeting and sample commands produce useful results.
- Treat terminal scenes as terminal results; do not substitute terminal output for feature UI or forge HTML. Do not invent routes or screens.
- Independently inspect every image and transcript for privacy and truthfulness, including the narrowly defined presentation mappings above. Unknown identities fail review.
- Confirm the plan against the actual capture tooling at capture time. Its TOML structure has been checked against the supplied field rules by inspection; no parser, plugin code, capture, or network call was run.
