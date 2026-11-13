# ADR 0003: A plugin lock is valid by contract, not by Core's dependency list

Status: accepted with the toolkit release that implements it; flips in that one release, no side-by-side period.

## Context

Each plugin commits a full hash lock (`requirements.lock`) and a record (`plugin-lock.json`). Until now the toolkit
refused a lock unless the selected Core wheel's `Requires-Dist` list was byte-equal to the copy in the record, extras
included. The locks were also inputs of the screenshot gallery digest, and `requirements.lock` counted as shipped
content. One Core dependency edit or one upstream advisory therefore became, for every plugin: relock, recaptured
gallery, privacy review, version bump, changelog and release. Adding one package to a Core extra that no plugin
installs failed ten consumer jobs; one advisory meant eight bumps, eight recaptures and eight releases.

The equality check was a staleness heuristic. Integrity comes from installing the lock with
`uv pip sync --require-hashes --no-build` and from `uv pip check` after Core is installed without dependencies. The
lock never reaches users: a plugin wheel carries only its own version ranges, and the app installs against Core's
constraints. Plugins import `pydantic` and `rich` without declaring them, because Core provides both.

## Decision

1. **The contract.** A plugin declares exactly one `core:plugin-api@N` in `[tool.heinzel.plugin] requires` and a
   Core version range in `project.dependencies`. The toolkit defines what each API number promises; for
   `core:plugin-api@1` that is pydantic 2 and rich 15, the libraries plugins import through Core. Core enforces the
   same majors in its own metadata (`pydantic<3`, `rich>=15,<16`) and tests that its base requirements stay inside
   them, so neither its app lock nor a fresh install can move a plugin onto a new major without a new API number.
2. **A lock is valid** when its dependency inputs are unchanged, its recorded Core is in the declared range, it pins
   pydantic and rich inside the contract's majors, and the selected Core (a candidate wheel or the installed Core) is
   in the declared range and every pin the lock holds for Core's requirements satisfies them. A Core requirement
   the lock does not pin at all fails. A requirement counts when any supported target needs it (macOS arm64, Linux
   x86_64 and aarch64, Python 3.12); the host running the check never decides. Core's extras are not part of the
   contract: plugins install Core without extras. Extras of a base requirement and transitive requirements are
   checked by `uv pip check` after installation, which stays the backstop.
3. **Which Core a plugin's own checks test.** Without `CORE=`, `check`, `audit` and `acceptance` install the newest
   released Core in the declared range, never the lock-time Core. The recorded Core version is only where the lock
   was resolved. A lock the newest Core breaks fails there and is relocked, as tooling.
4. **What still fails:** a Core that raises a floor above a locked pin (for example a security floor), adds a base
   dependency, or moves pydantic or rich to a new major; a relock that drifts into a new pydantic or rich major;
   changed inputs; a Core outside the range. Hash-locked installs and `uv pip check` stay unchanged.
5. **Locks are tooling.** `requirements.lock` and `plugin-lock.json` are not shipped content. The gallery digest
   covers what renders. It leaves out the plugin's own version, the version specifiers of its dependencies, its
   dependency groups and the lock. It keeps the names of every declared and every locked distribution, and the locked
   version of every `heinzel*` distribution, because a new plugin dependency, direct or transitive and whatever its
   name, adds pages, sidebar entries or notices to the captured app. A relock that only moves versions of other
   packages leaves the gallery fresh; one that adds or drops a locked distribution (for example when a Core
   dependency gains a requirement) needs a recapture. For a plugin with a build hook it also keeps the hook file, the build requirements and their locked
   versions, because they build the views. The gallery check fails if a published transcript renders the plugin's
   own version. A relock alone needs no version bump, changelog section or release, and no recapture unless the set of
   locked distributions changes.
6. **Security relock path.** Relock every affected plugin in one pull request; no bump, no recapture. Then bump a
   plugin only when the fixed version is not already forced for its users by Core or by the plugin's declared
   ranges:
   - the vulnerable package is a declared dependency whose floor admits the vulnerable version: raise the floor;
   - the vulnerable package reaches users only through one of the plugin's own dependencies: add a direct floor
     (`pkg>=fixed`);
   - the package reaches users through Core: Core's release fixes it; no plugin bump.

   Each bumped plugin gets a patch version and a changelog section in the same pull request. The merge releases
   every bumped plugin in one pass (`Release bumped plugins`); the galleries stay fresh. Older releases whose floors
   admit the vulnerable version are not yanked; the app's update installs the new release.
7. **Standing audit.** A scheduled workflow runs the toolkit's audit (pip-audit on the installed lock closure) for
   every public plugin daily, so a vulnerable plugin-only pin fails without waiting for a Core change or a pull
   request. For each finding the audit names the case of rule 6 that applies.
8. **Migration.** Lock records of format 1 stay valid; the toolkit reads only their Core version and writes format 2
   (no dependency list) on the next relock. An older toolkit cannot read format 2; toolkit and locks move together,
   also in standalone projects. A gallery or screenshot definition reviewed under the old digest is accepted in two
   ways. This repository pins the old-to-new digest of every such gallery at the flip (`_digest_migration.py`), so
   a later relock does not make it stale; a test keeps every pinned value equal to the digest of the committed
   tree. Standalone projects have no pinned entries: their old digest is recomputed and accepted while it still
   matches; their first change after that needs one recapture.

## Consequences

- A Core dependency change costs nothing for plugins unless it actually breaks a lock; then only that plugin
  relocks, as tooling.
- A new pydantic or rich major is a new plugin API number: the toolkit learns `core:plugin-api@2`, Core moves its
  caps, and plugins opt in by declaring it and relocking.
- Core does not advertise its plugin API number in its wheel; its declared range and its capped majors stand for it.
- Galleries may drift visually between recaptures when a library minor changes tables or error text, as they already
  do between Core versions. Library upgrades add no private data, so the privacy review is unaffected.
- A relock that changes the locked build tools of a plugin with a build hook makes its gallery stale, because they
  build its views. Released versions are never rebuilt; the next bump ships the new build tools.
- Core CI checks consumers with the toolkit at a pinned plugins commit. It gets these rules when Core moves that pin
  to a commit after this change.
- `hz system update` and installed plugins are unaffected: users never receive the lock, and Core does not read
  `plugin-lock.json`.
