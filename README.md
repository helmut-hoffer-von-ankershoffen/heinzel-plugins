# Heinzelmännchen plugins

Independent public plugins for [Heinzelmännchen](https://github.com/helmut-hoffer-von-ankershoffen/heinzel).
Each project under `plugins/` owns its code, assets, dependency locks, tests, version and artifacts.
Adding a project changes only its own directory. Core remains independently buildable and testable.

## Work on one plugin

You need git, make and uv. No core checkout or sibling plugin environment is needed.

```bash
make list
make check NAME=resource
make preview NAME=clock
make build NAME=clock
make acceptance NAME=clock
make release NAME=clock
```

Until the compatible core is released, add `CORE=/path/to/heinzel-0.9.0-py3-none-any.whl`.
CI can download a candidate wheel from an official core Actions run with the `core_run` input or
`CORE_CANDIDATE_RUN` repository variable. It installs the artifact and never builds or tests core.
Once 0.9 is released, remove the bootstrap variable; each project's lock selects its compatible released core.

`check` runs the owning plugin's formatting, lint, strict mypy/Pyright, Python tests and coverage (at least 90%),
plus its declared frontend checks. `acceptance` installs built core/plugin wheels into a separate environment
and runs the owning browser tests. `release` checks and builds one plugin and prints its independent tag/artifacts.
It publishes nothing. The Release workflow previews by default; its explicit publish option creates that plugin's
tag, GitHub release and PyPI artifacts with build provenance, behind the publishing environment.

`preview` uses isolated application state under the owning `.preview/`. It preserves your normal configuration.
Restart after rebuilding loaded view assets; Ctrl-C stops the preview.

## Add a plugin

Create a normal standalone project under `plugins/<distribution>/` with a `heinzel.modules` entry point.
Use `hz system plugin new <directory>` to generate a starter with status, navigation, Today widget,
notification and local view examples. Each Python operation becomes a CLI command, MCP tool and API operation.
`hz system plugin sdk <new-directory>` exports the versioned browser SDK and types for bundled views.
The starter's static view needs no JavaScript tooling.

Copy an appropriate owning project's tool configuration, then create its independent dependency lock:

```bash
make lock NAME=<distribution> CORE=<compatible-built-core-wheel>
make check NAME=<distribution> CORE=<compatible-built-core-wheel>
```

Commit both `requirements.lock` and `plugin-lock.json`. Checks enforce the lock's hashes, refuse changed dependency
inputs, and reject incompatible core metadata. Dependencies on concrete plugin implementations are rejected.
Plugins may implement and consume public interfaces, capabilities and lets from the SDK or an implementation-free
contract package. Provider selection happens through contracts and bindings. Declare versioned `requires` and
`provides` contract identifiers in `[tool.heinzel.plugin]` so the planner also selects affected consumers.

```bash
make plan BASE=origin/main
make plan CONTRACT=core:plugin-api@1 CORE=<candidate-core-wheel>
```

The work plan and command timings are visible in CI. Plugin-only changes select no core tests, core build or native
app jobs. A standalone external repository works equally: add its `heinzel-plugin` GitHub topic and a valid root
project. Core's catalog reads metadata automatically, including new plugin directories in configured source repos.

## Standard app

Only locally reviewed metadata can enroll a plugin in the `standard` profile. Topic discovery never enrolls defaults.
The composition workflow verifies an official core release's provenance, runs the selected default plugins' own
checks and browser tests, and proves installation into a fresh environment before publishing a digest-pinned profile.
Clock, Resource and Tailscale are included and active by default; sharing stays off until explicitly enabled.
User disable/removal choices survive a profile refresh. Minimal core has no plugin dependencies.

```bash
make profile CORE=<built-core-wheel>
```

This writes a local profile from already-built owning artifacts. The approved composition workflow produces the
release profile consumed by `uvx --from heinzel hz-install`. Plugin releases remain independent of app composition.

## Migration provenance

The initial migration moves Clock, Tailscale, Atlassian, GitHub, Google and Zoom from
[heinzel](https://github.com/helmut-hoffer-von-ankershoffen/heinzel), and Weather and Example from
[heinzel-contrib](https://github.com/helmut-hoffer-von-ankershoffen/heinzel-contrib).
Resource is the only built-in module extracted for 0.9. Sound, Theme and the other core modules remain in core.
Their earlier history and attribution remain in the original repositories. Existing public distribution names stay
stable; the migration versions advance independently before publishing the changed artifacts.
