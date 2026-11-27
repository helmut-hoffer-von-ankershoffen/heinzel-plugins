# AGENTS.md

Each directory in `plugins/` is an independent project. Read README.md for owning commands.

## Commands

- Create: `make new NAME=harbor` (creates only the plugin directory and lock).
- Edit loop: `make check-fast NAME=<owner>`.
- Before release: `make check NAME=<owner>`, `make build NAME=<owner>`, `make acceptance NAME=<owner>`.
- `make lock NAME=<owner>` refreshes ordinary dependencies. `CORE=<wheel>` selects a candidate SDK.
  `make tooling-check` checks shared tooling only.
- Release: `make release NAME=<owner>` previews; after a reviewed merge, `make publish NAME=<owner>` dispatches the
  owning protected workflow.
- After an interface change: `make screenshots NAME=<owner> OPEN=1`. The plan is the hand-edited
  `docs/screenshot-definition.json`; capture is deterministic (Playwright, fixture scenes, fictional data, text
  guards) and never calls an agent. Offline freshness: `make screenshots-check NAME=<owner>`; CI re-captures
  each changed plugin (`make screenshots-verify NAME=<owner>`) and fails on changed scene text
  ([guide](docs/SCREENSHOT_AUTHORING.md)).

## Rules

- Use only the public `heinzel` / `heinzel.kernel` API. Never import another plugin's implementation or core
  internals.
- Keep changes inside the owning plugin; change shared tooling only for a generic capability.
- Never run core's suite for a plugin change. Test core contract changes against a candidate core artifact.
- Versions, tests and releases are per plugin. Publish exactly the accepted wheel; never rebuild an existing version.
- Every plugin PR that bumps a version adds a non-empty top `## <new version>` CHANGELOG.md section (the release
  notes; `scripts/plugin_versions.py check` refuses otherwise). Every combine PR body has one
  `Combines #N type(scope): title` line per member.
- Private plugins use private GitHub releases and authenticated HTTPS installation, never public PyPI. Standalone
  projects use the same toolkit and need no parent edits
  ([author guide](https://github.com/helmut-hoffer-von-ankershoffen/heinzel/blob/main/docs/PLUGIN_AUTHORING.md)).
- Set exactly one level marker per pytest file.
- Use conventional commits and pull requests. Review nontrivial changes.
- Public sources contain only fictional names.
- Never weaken a screenshot guard to let a capture through; change the fixture instead.
