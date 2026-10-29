# AGENTS.md

Plugins use only the public `heinzel` / `heinzel.kernel` API. Each directory in `plugins/` is an independent project.
Keep changes inside the owning plugin; improve shared tooling only for a generic capability. Never import another
plugin implementation or core internals. Versions, tests and releases are per plugin. Every pytest file has exactly
one level marker. Core contract changes are tested against a candidate core artifact, never by running all core tests.
Use conventional commits and pull requests. Review nontrivial changes. Public sources contain only fictional names.
