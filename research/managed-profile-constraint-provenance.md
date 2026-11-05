# Managed composition constraint provenance

The app 0.9.16 composition at main `53218549a225089a7c8fd0c315f05f57b89926cc`
failed in run 42020635931, job 127222379947. Independent plugin acceptance,
installed discovery and UI views passed. The managed installer installed all
69 packages, including the five selected release wheels and uv 0.13.7.

## Actual installed failures

A bounded diagnostic study exercised two fresh Linux runners with genuine user
managers, exact bootstrap Python 3.14.4 and uv 0.13.7. Both arms independently
verified all five wheel hashes, GitHub/PyPI byte equality and attestations, then
passed the normal managed installation, startup checkpoint and offline inventory.
Both failed at the first actual command:

`hz system plugin develop <isolated-root>/probe --json`

The baseline used source `53218549`; the candidate used `0d78dbcb`. The candidate's change of the current constraints after
installation did not fix the failure. Both actual `uv-receipt.toml` files still
contained five original download-path constraints. The candidate's environment
instead named the retained `app-artifacts/<sha256>/<filename>#sha256=<digest>`
URLs. The normal SDK preserves receipt constraints and verified installed wheel
provenance, so correctly refused those different sources before invoking uv.

The earlier policy-only counterfactual omitted persisted receipt constraints.
Its narrow success was insufficient and is superseded by these installed results.
An earlier diagnostic study was invalid setup: neither lifecycle ran. Every
original failed run and artifact remains preserved.

## Necessary harness preparation and remaining SDK prerequisite

The harness now pins the SDK's future content-addressed wheel URLs, including
SHA-256 fragments, before installation. Its constraints remain identical across
installation and every mutation. The normal SDK still owns copying and verifying
all wheels; the harness independently hashes every retained wheel afterward.
The explicit local update names the identical hash-bound core URL. No receipt
is hand-edited, constraint removed, or lifecycle/checkpoint/daemon check bypassed.

This preparation does **not** make the immutable SDK 0.9.16 pass. uv 0.13.7
serializes local-wheel constraints as fragmentless path entries in its receipt.
SDK 0.9.16 reconstructs that path as a fragmentless file URL, then compares it
against the preserved hash-bound URL by exact string equality. Even identical
paths therefore conflict solely because one URL carries the hash fragment.
The SDK already documents uv's hash-dropping behavior in its transient-wheel
receipt matching, but its selected constraint-policy comparison does not account
for it.

A new SDK needs a source-identity round trip that preserves both the immutable
receipt policy and the strongest verified hash identity for the same local
wheel. Different paths, conflicting hashes, changed bytes, ambiguous metadata,
foreign ownership and version conflicts must remain refusals. Merely dropping
fragments, constraints or checks is insufficient. Existing SDK releases remain
immutable; this finding is a next-SDK requirement, not a successful app release.

## Evidence and limits

- The actual Linux receipts prove why changing only current constraints fails.
- A separate isolated, explicit normal uv 0.13.7 tool installation of all five
  selected immutable wheels, without overrides, independently captures its receipt serialization and asks the unchanged installed SDK 0.9.16
  parser and constraint validator to round-trip that policy. It does not run a
  daemon, native profile or installed application, and is not lifecycle acceptance.
- Owning harness tests require the initial constraints already to name every
  retained URL/hash and to remain identical afterward. Existing missing/corrupt
  artifact, checkpoint, offline inventory, update and source-integrity negatives
  remain.
- Source preparation and passing unit tests cannot qualify the full Linux
  lifecycle. The next SDK repair requires owning regressions, independent source
  review and a fresh bounded installed Linux before/after study before composition
  or publication.

## Subsequent candidate-SDK lifecycle qualification

A second installed comparison showed that repairing same-wheel receipt source
identity allowed the first development operation, but a later local Core update
still lost the verified local-wheel hashes for all five distributions. That
intermediate candidate was therefore insufficient. The updater now forwards the
checkpoint-authorized unchanged wheel hashes alongside the explicitly selected
Core hash; it preserves the identical receipt-derived constraint policy.

A fresh paired Linux study ran the unchanged managed lifecycle with the same
published standard plugin wheels, bootstrap versions and harness. The intermediate
control failed at the update. The repaired, explicitly unpublished source
candidate completed install, development, update, probe removal and reinstall,
including every startup checkpoint, offline inventory, selected-byte integrity
check and daemon-off assertion. Both complete result archives and original
failures were retained. This is installed Linux diagnostic evidence for the
combined harness and candidate SDK repairs, not a registry release, native Mac
result or combined application acceptance.

The harness implementation and owning tests in this branch remain unchanged
when incorporating the newly reviewed Google provider on main. Its source
qualification must still pass ordinary current-head CI; the original Zoom test
timeouts remain unresolved. Published SDK 0.9.16 cannot pass this lifecycle. The
new SDK and composed app require their normal publication and both-OS acceptance.
