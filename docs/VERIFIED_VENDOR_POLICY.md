# Verified upstream implementation policy

This policy requires developer toolkit 0.3.1 or later. Toolkit checks validate an owning plugin against its
declared SDK and lock; this toolkit version does not establish compatibility with a newer core SDK.

An owning project may carry a closed, pure Python upstream subset when it needs
an isolated namespace. This changes development diagnostics for verified upstream
implementation files only. It grants no runtime capability, origin, transport,
capture, approval, or trust exception.

`heinzel_plugin_tools.vendor` is the policy implementation. Schema 1 supports one
upstream distribution and one package mapping per owning project. Normal checks
are offline: they do not fetch wheels, resolve upstream dependencies, execute
upstream generators, or import upstream source.

## Provenance and generation

Commit `vendor-manifest.json`, the original pure Python wheel under
`vendor-provenance/<wheel-basename>`, and the projected source. Obtain the wheel
SHA256 independently from the upstream artifact publisher and bind it to the
owning hashed dependency lock when that dependency remains installed. RECORD is
not an integrity authority. Review the wheel pin, selected paths, license, manifest,
transformer, and policy together. A new pin is a supply-chain change requiring
independent security review before publication.

The exact schema has these keys; unknown keys fail:

```json
{
  "format": 1,
  "transform_version": "namespace-relocation-v1",
  "upstream": {
    "distribution": "example_sdk",
    "version": "1.2.3",
    "wheel": "example_sdk-1.2.3-py3-none-any.whl",
    "sha256": "<64 lowercase hexadecimal digits>",
    "license_expression": "MIT",
    "license_paths": ["example_sdk-1.2.3.dist-info/licenses/LICENSE"]
  },
  "package": {"source": "example_sdk", "target": "owner._vendor.example_sdk"},
  "files": [{
    "source": "example_sdk/__init__.py",
    "target": "src/owner/_vendor/example_sdk/__init__.py",
    "original_sha256": "<64 lowercase hexadecimal digits>",
    "projected_sha256": "<64 lowercase hexadecimal digits>"
  }]
}
```

The illustrative inventory is incomplete: production inventories must also name
every selected module, upstream typing marker when present, and each pinned
license file. Available companion `.pyi` files for selected implementation files
and internal modules referenced by selected stubs must also be retained.
License files project unchanged to the package root. Distribution,
version and license must match upstream METADATA. The target must belong to an
owning public entry-point namespace, never a first-party adapter location.

`generate_manifest(root, wheel, *, distribution, version, sha256,
license_expression, license_paths, source, target, paths)` verifies the explicitly
supplied SHA256 before opening the archive, writes the pin and projection, and
verifies the result. `regenerate(root)` deterministically regenerates the reviewed
pin without deleting unexpected files. Both functions accept local files only.

Version 1 rewrites only absolute `from` module prefixes and explicitly aliased
absolute `import` prefixes. Relative imports, executable statements, annotations,
strings, comments and all other bytes stay unchanged. A separately transformed
AST must equal the projected AST. Bare namespace imports, namespace identifier
rewrites, shadowing, recognized dynamic import/execution facilities, native files,
unsafe paths and unsupported transformations fail closed. This is a deliberately
restricted namespace transform, not a sandbox for executing upstream code. A
different upstream shape requires a reviewed new transform version, never a
manual patch to exempt source.

## Fixed Slack 3.46.0 security amendment

[ADR 0002](adr/0002-pinned-slack-security-repair.md) adds one closed transform:
`namespace-relocation-v1+slack-sdk-3.46.0-security-v1`. It applies only to distribution
`slack_sdk` version `3.46.0`, the exact approved upstream wheel, and owning target
`heinzel_slack._vendor.slack_sdk`. The verifier selects it from that identity; both
generation and verification reject a downgrade to namespace-only for the affected pin.
All unaffected projects keep `namespace-relocation-v1` unchanged.

There are no new manifest fields, patch arguments, source callbacks, or executable
patch files. Code-owned constants bind the wheel name/hash and three member paths,
preimage/postimage hashes, function identities, and fixed statement replacements.
Byte replacement and independent scoped AST transformation must agree. All repaired
members are mandatory. Original manifest hashes still identify genuine upstream
bytes; projected hashes identify the repaired and relocated bytes. The immutable
upstream wheel remains unmodified. On-disk, quality-policy, build and accepted-wheel
verification all use this same projection.

The allowed delta repairs frame-mask entropy, removes direct plaintext fallback,
and removes proxy credential-bearing request/response and URL diagnostics. It does
not add Core runtime permissions, arbitrary patch support, or a security-scanner
exclusion. Broader patches and upstream upgrades require a new independent review.

## Verification and diagnostics

`project(root)` verifies the entire wheel SHA256 before reading members, then
each original hash, deterministic projection, projected hash and byte equality.
The target tree must contain exactly the reviewed files. Missing, extra, modified,
symlinked, hardlinked and nonregular files fail. Do not generate bytecode inside
that tree; checks set `PYTHONDONTWRITEBYTECODE=1`. A vendor tree without a manifest
fails. Exemptions are ephemeral verified file lists, never `_vendor/**` patterns.

The toolkit runs verification before fix, check, build and installed acceptance,
and re-verifies before applying each diagnostic policy. Build and acceptance also
verify the exact vendor inventory and bytes in the owning wheel, independently
of its RECORD. A wheel introducing a vendor namespace without a verified source
manifest fails even when the source project contains no vendor code. Upstream
and built archives reject every explicitly nonregular file mode; unspecified ZIP
modes remain compatible. Parent package initializers remain first-party code.
An owning wheel may additionally carry a manifest-approved license at its
canonical `.dist-info/licenses/<source-target>` path only when its own matching
METADATA declares that exact `License-File` and the copy equals the pinned source
bytes. This allowance grants no additional import namespace or source exemption;
undeclared, altered, missing or foreign metadata copies fail.
The owning canonical dist-info directory must be the only metadata authority and
contain both METADATA and WHEEL. Required identity and WHEEL singleton headers
must appear exactly once, and the WHEEL version, pure-library flag, tags and
optional build field must satisfy the supported format. Conflicting or repeated
identity headers, nested/foreign authorities and an incomplete pair fail closed.
Case aliases cannot introduce a second metadata authority or an unverified vendor
namespace on a filesystem that ignores filename case.
Both original and built archives reject path collisions after Unicode canonical
normalization and case folding, including METADATA/WHEEL basename aliases.

`quality_command(root, command, verified_inventory)` derives temporary settings. These are intentional, narrow
diagnostic and coverage policy exceptions for verified upstream files:

* Ruff and spelling omit the exact verified files only.
* Mypy suppresses errors for exact verified modules and omits those exact files
  from recursive discovery. Import analysis remains enabled; it does not use
  `follow_imports=skip`, missing-import suppression, stubs that replace types, or
  `Any` substitutions.
* Pyright ignores diagnostics for exact verified files while retaining analysis
  and all owning strict settings. Settings come from the owning pyproject; an
  alternate Pyright config fails closed.
* Coverage omits the exact verified Python files from collection and reporting.
  The owning first-party source settings and coverage floor stay unchanged.

Adapters, generators, verifiers, tests and other first-party code retain their
existing lint, strict typing and coverage requirements, including the owning 90%
floor. Retain upstream annotations, `.pyi` files and `py.typed`; negative consumer
checks must prove both type checkers still reject invalid typed SDK calls.

## Security and publication

The ordinary dependency license/vulnerability audit still runs. In addition,
audit reads the successfully verified manifest: its exact upstream version is
always sent to vulnerability auditing, even if the original distribution is
absent or another version is installed. Its upstream license must satisfy the
same owning license allowlist through an exact, case-sensitive whole-expression match. A compound `AND` or `OR`
expression needs its own explicitly reviewed entry; an allowed component or substring does not approve it.
The installed dependency classifier audit retains its existing partial-match behavior. The audit prints the
upstream version, license and complete file inventory. Ordinary security and secret scanners retain the
source; there is no vendor security-scanning exclusion.

Keeping the original dependency installed is permitted and its lock must match
the vendor pin. Removing it does not remove the vendor audit record. No default
network access is added to normal offline checks; the existing explicit audit
command retains its advisory queries and existing private-project behavior.

Review manifest, transformer and exemption-policy changes as security-boundary
changes. Publication follows the owning release priorities and normal required
gates after independent review. A passing projection proves byte provenance and
the limited relocation; it does not establish upstream safety or live-provider
behavior.

The canonical owning project `heinzel-slack` or protected `heinzel_slack._vendor.slack_sdk` target makes the security repair mandatory before upstream
identity is inspected. A raw distribution-name alias, version change, or coherently repacked wheel and lock cannot
select namespace-only mode. Changing the approved upstream identity requires a separately reviewed verifier change.

Malformed proxy CONNECT response parsing raises a fixed diagnostic with its exception context suppressed, so raw
status tokens and decoding errors cannot be copied into caller exception logs. This parser repair alone does not promise general SDK
debug-log secrecy; the owning adapter boundary separately isolates logging and refuses unsupported proxy schemes.

The same pinned policy includes the exact `slack_sdk/web/base_client.py` direct-route repair documented in ADR 0002.
Its no-proxy branch uses a local empty ProxyHandler, preventing ambient proxy rediscovery without global mutation.
The owning adapter separately refuses credentialed or unsupported proxy URIs and isolates SDK logging. The new
class/method-scoped fixed statement is verifier code, not a manifest-supplied transform.
