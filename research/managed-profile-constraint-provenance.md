# Managed composition constraint provenance

The app 0.9.16 composition at main `53218549a225089a7c8fd0c315f05f57b89926cc`
failed in run 42020635931, job 127222379947. Independent plugin acceptance,
installed discovery and UI views passed. The managed installer installed all
69 packages, including the five selected release wheels and uv 0.13.7.

The first subsequent mutation in `verify_managed_profile` is
`hz system plugin develop <isolated-root>/probe --json`. Its constraint-policy
validation combines the harness's `UV_CONSTRAINT` entries with the installed
checkpoint's preserved wheel sources. The harness named the original download
locations. The installer correctly retained the same bytes in its private
`app-artifacts/<sha256>/<filename>` store and installed hash-bound URLs there.
The SDK correctly rejects two different direct URLs for one distribution,
before invoking uv. The final error is the SDK's deliberate constraint refusal,
not a failed uv dependency solve. The job does not print the internal managed
commands; command attribution follows the preserved harness and SDK call path.

The repair retains the initial source constraints during installation. After
installation it independently hashes every retained wheel against the original
selected bytes, then constrains every distribution to the retained URL including
its SHA-256 fragment. The explicit local update uses the identical hash-bound
core URL. No constraints, lifecycle operations, startup checkpoints, daemon
quiescence, offline launches or artifact-integrity checks are removed. The
published SDK and plugin releases do not change.

## Evidence and limits

- The actual installed 0.9.16 SDK policy, with all five released wheels, rejects
  the original plus retained URL constraints, accepts identical retained
  constraints, and still rejects a genuine `heinzel==0.9.15` conflict.
- Owning installation and composition tests: 21 passed. Regression coverage
  checks the initial constraints, retained hash-bound constraints, exact local
  update source, missing/corrupt retained bytes, and existing lifecycle negatives.
- Repository Python lint and format checks passed.
- Independent strongest source review approved the final implementation,
  explicitly finding no weakened policy, provenance, constraints, checkpoint,
  daemon boundary or lifecycle step.
- A fresh macOS managed acceptance attempt stopped at the genuine daemon
  absence boundary. This is preserved as a failure; it does not establish the
  full lifecycle. No absence check was mocked or bypassed.

The next required evidence is an independently reviewed, bounded Linux installed
before/after study using these same immutable releases and the unmodified normal
managed lifecycle. A new full composition or publication is not justified by
source review or the focused policy counterfactual alone.
