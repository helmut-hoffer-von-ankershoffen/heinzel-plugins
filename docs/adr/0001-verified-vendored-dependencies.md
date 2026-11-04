# ADR 0001: Exact verified upstream files define vendor diagnostics

Status: proposed; independent security review required before publication.

## Context

An isolated upstream package namespace can preserve a dependency's typed API while
preventing imports from using an ambient package. Applying first-party style and
coverage requirements to unchanged upstream implementation is inappropriate, but
a directory-wide exclusion can hide local code, patches, or an untracked upgrade.
Removing a runtime dependency can also accidentally remove vulnerability and
license visibility.

## Decision

Adopt [the generic verified vendor policy](../VERIFIED_VENDOR_POLICY.md). Pin a
local immutable upstream wheel with publisher SHA256, metadata identity, license,
exact source and target paths, original/projected hashes and transform version.
Verify the archive before reading it, regenerate a closed import-only namespace
projection, compare independent ASTs and exact bytes, and reject inventory drift.

Only successful verification may produce exact diagnostic exemptions. Keep
first-party strict settings and coverage floors. Preserve upstream type data and
prove invalid consumer calls remain errors in both type checkers. Keep the exact
upstream version and license in the audit even without its external installation.
Verify before format/check/build and again inside each built/accepted wheel.

## Consequences and limits

The repository carries original wheel bytes as offline provenance. Upgrades and
new transform shapes require explicit review. This adds no core runtime trust,
permission, origin, transport or approval exemption. It deliberately rejects
unsupported dynamic import and identifier rewriting shapes rather than patching
upstream logic. A verified subset is not a security endorsement of its upstream.
Publication remains held for independent review and the owner's release order.
