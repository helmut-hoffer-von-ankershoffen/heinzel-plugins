# Heinzelmännchen plugins

Independent public plugins for [Heinzelmännchen](https://github.com/helmut-hoffer-von-ankershoffen/heinzel).
Each project under `plugins/` owns its code, assets, dependency locks, tests, version and artifacts.
Adding a project changes only its own directory. Core remains independently buildable and testable.

For macOS and Linux, start with the [standard app installation guide](https://helmut.hoffer-von-ankershoffen.me/heinzel/guides/install/).
Use `uvx heinzel@latest` if uv is available, or its guided curl/wget installer to install prerequisites automatically.
Windows may work, but is not supported.

## Work on one plugin

You need git, make and uv. No core checkout or sibling plugin environment is needed.

```bash
make list
make check-fast NAME=resource
make check NAME=resource
make preview NAME=clock
make build NAME=clock
make acceptance NAME=clock
make release NAME=clock
```

Each project's lock selects its compatible released SDK. For a candidate SDK, add `CORE=/path/to/core.whl`.
CI can download a candidate wheel from an official Core Actions run with the `core_run` input or
`CORE_CANDIDATE_RUN` repository variable. It installs the artifact and never builds or tests Core.

`check-fast` runs owning lint and offline unit/integration tests. `check` runs the owning plugin's formatting, lint, spelling, strict mypy/Pyright, Python tests and coverage (at least
90%), plus its declared frontend checks. `acceptance` installs built core/plugin wheels into a separate environment
and runs the owning head and browser tests. `release` checks and builds one plugin and prints its independent tag/artifacts.
It publishes nothing. The Release workflow previews by default; its explicit publish option creates that plugin's
tag, GitHub release and optional PyPI artifacts with build provenance. `make publish NAME=<name>` dispatches that
workflow from clean, current main. Public PyPI publication uses its protected environment and trusted publisher.

`preview` uses isolated application state under the owning `.preview/`. It preserves your normal configuration.
Restart after rebuilding loaded view assets; Ctrl-C stops the preview.

## Add a plugin

Create the complete owning project with one command:

```bash
make new NAME=harbor
make check-fast NAME=harbor
make check NAME=harbor
make build NAME=harbor
make acceptance NAME=harbor
```

The minimal starter contains one operation and behavior test, installed acceptance and concise human/agent guides.
It adds only `plugins/heinzel-harbor/`, without a parent registration, copied workflow or embedded Git repository.
The new directory includes its own small Makefile: `cd plugins/heinzel-harbor` and use `make check-fast`,
`make check`, `make build` and `make publish` directly. Root `NAME=<owner>` commands are optional conveniences.
Use `make new NAME=harbor PRESET=contributions` when a richer example is useful.
Each Python operation becomes a CLI command, MCP tool and API operation.
`hz system plugin sdk <new-directory>` exports the versioned browser SDK and types for bundled views.
The starter's static view needs no JavaScript tooling.

The scaffold creates its independent dependency lock. After changing dependencies, refresh it:

```bash
make lock NAME=<distribution> CORE=<compatible-built-core-wheel>
make check NAME=<distribution> CORE=<compatible-built-core-wheel>
```

Commit both `requirements.lock` and `plugin-lock.json`. Checks enforce the lock's hashes, refuse changed dependency
inputs, and reject incompatible core metadata. Dependencies on concrete plugin implementations are rejected.
Plugins can add ordinary runtime and development dependencies in their own `pyproject.toml`, then regenerate their
own lock. This requires no core dependency change or sibling environment.
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
Commit and push hooks select the owning plugin and declared contract consumers through `hz-plugin check-changed
--git-hook`, including deleted paths. Unrelated changes are a no-op; shared-tooling changes still check tooling.

## Custom public and private repositories

Plugins do not have to live here. Follow the
[custom plugin author guide](https://github.com/helmut-hoffer-von-ankershoffen/heinzel/blob/main/docs/PLUGIN_AUTHORING.md)
to scaffold a standalone repository with `hz system plugin new heinzel-harbor --defaults --data plugin_name=harbor`.
Its `make setup`, `check-fast`, `check`, `preview`, `build`, `acceptance`, `release` and `publish` commands use the
same versioned developer toolkit. No checkout of this repository or core is needed.

Choose `gh repo create ... --public` or `--private`; add topic `heinzel-plugin` for catalog discovery. Private
discovery and HTTPS Git installation use the installing person's `gh auth login`. A private plugin publishes to
private GitHub releases, never public PyPI. Public packages can choose GitHub-only publication with
`REGISTRY=github`; default public publication uses the distribution's PyPI trusted publisher. Every release is
immutable. `TAG=<distribution>/v<version> REGISTRY=pypi` resumes an existing public GitHub release after verifying
its original commit, digests and provenance, without rebuilding it.

Private repositories skip public advisory queries to keep private package names local. An owning
`tool.heinzel.plugin.audit_command` can run an internal audit tool; without it, private checks verify locks and
installed compatibility but do not run a vulnerability advisory audit. Set repository variable
`PRIVATE_ATTESTATIONS=true` only on a GitHub plan supporting private attestations. The author guide explains both
release paths and their prerequisites.

The toolkit is a development dependency, independently released as a GitHub wheel under `tools-v<version>`.
It has no plugin entry point and needs no additional PyPI publisher. Root `make tooling-check` checks the shared
toolkit; use `NAME=<owner>` for plugin commands. `make preflight NAME=<owner>` includes that plugin's full checks,
build, audit and installed acceptance. Toolkit tests do not run core's suite.

## Standard app

Only locally reviewed metadata can enroll a plugin in the `standard` profile. Topic discovery never enrolls defaults.
The composition workflow verifies an official core release and independently released plugin artifacts, runs
installed acceptance on those exact wheels, and proves installation into a fresh environment before publishing a
digest-pinned profile. It does not rebuild plugin releases. Every fifteen minutes it checks for a newly published
SDK without a complete standard app, verifies GitHub/PyPI artifact identity, and composes the missing release.
An existing complete composition is a no-op. The public quick start is always `uvx heinzel@latest`; versions stay in
machine-readable release metadata and locks.
Clock, Resource, Tailscale and the Heinzelmännchen theme are included and active by default. Sharing stays off until
explicitly enabled. An unconfigured app uses its theme recommendation; saved theme choices stay authoritative and installation starts no playback.
User disable/removal choices survive a profile refresh. Minimal core has no plugin dependencies.

```bash
make profile CORE=<built-core-wheel>
```

This writes a local profile from already-built owning artifacts. The approved composition workflow produces the
release profile consumed automatically by `uvx heinzel@latest`. Plugin releases remain independent of app composition.

## Migration provenance

The initial migration moves Clock, Tailscale, Atlassian, GitHub, Google and Zoom from
[heinzel](https://github.com/helmut-hoffer-von-ankershoffen/heinzel), and Weather and Example from
[heinzel-contrib](https://github.com/helmut-hoffer-von-ankershoffen/heinzel-contrib).
Resource is the only built-in module extracted in this migration. Sound, Theme and the other core modules remain in core.
Their earlier history and attribution remain in the original repositories. Existing public distribution names stay
stable; the migration versions advance independently before publishing the changed artifacts.
