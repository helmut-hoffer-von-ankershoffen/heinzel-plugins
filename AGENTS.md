# AGENTS.md

Plugins use only the public `heinzel` / `heinzel.kernel` API. Each directory in `plugins/` is an independent project.
Keep changes inside the owning plugin; improve shared tooling only for a generic capability. Never import another
plugin implementation or core internals. Versions, tests and releases are per plugin. Every pytest file has exactly
one level marker. Core contract changes are tested against a candidate core artifact, never by running all core tests.
Use conventional commits and pull requests. Review nontrivial changes. Public sources contain only fictional names.

Read README.md for owning commands. Use `make new NAME=harbor` to create only the new plugin directory and lock.
While editing run `make check-fast NAME=<owner>`; before release run `make check NAME=<owner>`, `make build NAME=<owner>`
and `make acceptance NAME=<owner>`. `make lock NAME=<owner>` refreshes ordinary dependencies. `CORE=<wheel>` selects
an explicit candidate SDK. `make tooling-check` checks shared tooling only. Never run core's suite for a plugin change.

`make release NAME=<owner>` previews; `make publish NAME=<owner>` dispatches the owning protected workflow after a
reviewed merge. Publish exactly the accepted wheel; never rebuild an existing version. Standalone public/private
projects use the same toolkit and need no parent edits; see the
[custom plugin author guide](https://github.com/helmut-hoffer-von-ankershoffen/heinzel/blob/main/docs/PLUGIN_AUTHORING.md).
Private plugins use private GitHub releases and authenticated HTTPS installation, never public PyPI.

After an interface change, run `make screenshots NAME=<owner> OPEN=1`. An agent defines a source-bound feature
story before capture; an independent agent inspects every image and transcript before gallery/README publication.
Use `hz-plugin screenshots <owner> --plan` for the editable definition and `--check --json` for offline freshness.
See [the capture guide](docs/SCREENSHOT_AUTHORING.md). Never manufacture an approval receipt to bypass either review.
