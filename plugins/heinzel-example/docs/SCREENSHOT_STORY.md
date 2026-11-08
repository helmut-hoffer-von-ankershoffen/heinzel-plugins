## Audience

Plugin authors considering a small, working Heinzelmännchen reference. The example demonstrates how one operation can feed several app contributions, alongside a typed greeting and a notification.

## Outcome

A prospective installer can see the constant `42` in the Today widget, status, and inspector; try a named greeting in the native terminal and CLI; and see a plugin notice in Core’s shared notification panel. These are examples of extension points, not claims that the plugin performs a business workflow.

## Scenes

1. **Widget and status — light.** On Today, show the demo value `42` in both the widget and sidebar status. They share the `sample` operation (`src/heinzel_example/__init__.py`: `sample`, `@module.widget`, and `@module.status`).
2. **Inspector — dark.** Open the actual `/?panel=example:inspector` view and show its larger rendering of `42`. This is a distinct, useful state of the same feature, with the route declared by `module.nav`, `module.action`, and `module.view` (`src/heinzel_example/__init__.py`; renderer in `src/heinzel_example/views/index.js`).
3. **Greeting in the native terminal.** Show the fictional name Mira passed to `example hello --json`; the typed greeting illustrates the submodule operation and structured output (`src/heinzel_example/hello/__init__.py`, `src/heinzel_example/_models.py`, and `README.md`). The terminal is presented as a terminal, not as a feature UI.
4. **Plugin notice.** Show the fixture-seeded “Example is ready” notice in Core’s shared notifications panel. The plugin emits the notice and supplies its route and command; Core owns the surrounding panel (`src/heinzel_example/__init__.py`: `notify`; `docs/screenshot_fixture.py`).
5. **Greeting CLI.** Show the same fictional named greeting in ordinary CLI output.
6. **Sample CLI.** Show `sample --json` returning `42`, tying the CLI result back to the app contributions (`src/heinzel_example/__init__.py`: `sample`).

## Fictional fixtures and presentation

Use the existing `docs/screenshot_fixture.py` bootstrap in an isolated demonstration profile. It disables native, Doctor, and release notifications and seeds the plugin’s notice; it does not establish that all other profile data is fictional. Mira is an example name, and `42` is the actual constant returned by the plugin.

Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript.

## Privacy pitfalls

Inspect the complete image and transcript, including background app chrome, notifications, terminal output, paths, hostnames, account information, and metadata. Do not generalize either approved mapping to an unverified identity or alter health results. Reject a capture if an unknown identity appears; use an isolated profile without connected accounts as described in `docs/SCREENSHOTS.md`.

## Acceptance criteria

- Capture genuine app surfaces, with the widget/status in applied light appearance and the inspector in applied dark appearance; verify the actual rendered appearance in each image.
- Confirm both UI scenes show the real `42` contribution, and the inspector is the declared plugin view. Do not substitute terminal output for either feature scene, forge HTML, or accept duplicate captures or caption-only changes.
- Confirm the native terminal and CLI results come from the stated commands and that the notice is visibly present in the shared panel. Independently inspect every image and transcript for privacy and truthfulness.
- The existing inspector plan waits for `The value is 42.`, but the supplied renderer displays `String(data)` and its heading is `Example`; the revised plan waits for `42` instead. Verify the real capture, since the supplied files do not prove Core’s full rendering or loading behavior.
- The plan is structurally reviewed against the requested format without executing code. Actual capture, applied themes, fixture behavior, and SDK compatibility remain to be verified during an explicit capture.

## Source-bound UI surface inventory

- **Discovery and submodule:** `pyproject.toml` declares the sole `heinzel.modules` entry point, `example = "heinzel_example"`; `src/heinzel_example/__init__.py` declares `Module("example", ...)`, and `src/heinzel_example/hello/__init__.py` declares `Module("hello", ...)` and `hello`.
- **Plugin-owned feature view:** `module.view(... name="inspector", source="sample", title="Example", abi=1)` loads `src/heinzel_example/views/index.js`. The declared navigation, action, and status effect target `/?panel=example:inspector`. The renderer has an `Example` region and displays loading or the raw value; it declares no actions.
- **Core-rendered feature contributions:** `@module.widget` contributes the Today metric; `@module.status` contributes footer and sidebar slots; `module.action` and `module.nav` contribute entry points. `notify` emits a plugin notice for Core’s notification UI. These declarations are in `src/heinzel_example/__init__.py`; the supplied source does not establish every surrounding Core interaction.
- **Operations and generic surfaces:** `info`, `sample`, and mutating `notify` are declared operations; `hello` is the submodule operation. `@module.info` contributes to system info, and `module.settings(ExampleSettings)` registers the greeting setting (`src/heinzel_example/__init__.py`, `src/heinzel_example/hello/__init__.py`, `src/heinzel_example/_models.py`). The README documents CLI use and JSON. A confirmation is described for `notify`, but the supplied sources do not establish its exact approval UI. Generic Core rendering of operations, settings, information, or confirmation must not be inferred from a missing Page/View declaration or represented as a verified screen without further evidence.
- **External provider UI:** No external provider integration or provider-owned UI is declared in the supplied plugin sources.
- **Terminal-only evidence:** The supplied README documents CLI invocations, but does not prove these operations are exclusively terminal-only. The CLI scenes illustrate real command output; they do not stand in for the established feature UI.
- **Unresolved claims:** `README.md` describes a health check and refers to `tests/contributions_test.py`, but no health-check declaration or referenced test file is present among the supplied files. The README also describes the inspector as showing `42` big, consistent with its renderer, while the old screenshot plan’s sentence-level wait conflicts with that renderer. The supplied files do not establish a plugin-specific setup flow or channel contribution.
