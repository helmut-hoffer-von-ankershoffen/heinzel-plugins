# ADR 0002: Pin the Slack SDK transport security repair

Status: proposed; independent security review and installed acceptance required before publication.

## Context

The verified Slack SDK 3.46.0 builtin transport uses a pseudorandom frame mask where WebSocket requires strong
entropy. It also logs proxy authentication/request and response data when tracing, includes a credentialed proxy URL
in a connection failure, logs proxy environment URLs at debug level, and returns a plaintext socket on direct ports
other than 443. The owner enables this builtin transport. Its default verified TLS context is already secure on
supported Python versions; changing TLS defaults is unnecessary.

The alternative websocket-client transport uses OS entropy, but its external/optional imports and additional
namespace do not satisfy the current Core source-capture and vendor projection contracts. Expanding those contracts
would be a larger unrelated trust change. Namespace-only projection cannot honestly describe security patches.

## Decision

Amend ADR 0001 with one verifier-owned transform, `namespace-relocation-v1+slack-sdk-3.46.0-security-v1`, for only
`heinzel_slack._vendor.slack_sdk` and the exact `slack_sdk` 3.46.0 wheel
`slack_sdk-3.46.0-py2.py3-none-any.whl`, SHA256
`6286d89da97ea193c853609131515e6f1b3edf86866d6e5aad0dba9dcf1cb72d`.

The original wheel is retained. Fixed member identities are:

| Upstream member | Original SHA256 | Repaired SHA256 |
| --- | --- | --- |
| `slack_sdk/socket_mode/builtin/internals.py` | `e98b873e92e58f5909229030441e78da4820f47c74ed4e5eea9717917a5ed861` | `aad42b74ddebd7f4e0870f263c09747e0f50995ab35d61bb4b33e675528ac2f3` |
| `slack_sdk/proxy_env_variable_loader.py` | `bf08e211ae42dff0d784f12e957e1ffd1b00db546c2e938fd7976f0faf48f4d3` | `457ae15cab87ff86b02e0062e7a5a3d3551330c7c9f095ca60aa5fc53e790fa7` |

The approved statements change only frame-mask generation to `list(os.urandom(4))`, remove the non-443 plaintext
branch, and replace proxy request/response and URL diagnostics with session/status or fixed text. Proxy authentication
remains in the CONNECT request sent to the configured proxy. Both direct and proxied destinations use the existing
TLS wrapper, including legitimate nonstandard TLS ports; failed TLS has no plaintext fallback.

The verifier requires original and repaired hashes, exact function-scoped statement identities, independent AST
agreement, complete inventory and final projected bytes. The manifest cannot supply edits or select custom policy.
Generation chooses the mandatory repair, and namespace-only downgrade is refused for this pin. Other projects retain
the original namespace-only transform. The original SDK pin, MIT license, audit inventory and type annotations remain.

## Consequences and limits

This is an explicitly patched upstream projection. Documentation and provenance must say so. Source and wheel
verification keep the same exact inventory and tamper checks. First-party tests, formatting and typing remain strict;
no Sonar/CodeQL findings are closed by this change, and no Core import or capability rule changes.

Offline tests cover actual SDK text, ping, pong and acknowledgement frames, deterministic entropy-source calls,
proxy wire authentication without credential diagnostics, default TLS properties, direct TLS on alternate ports,
TLS refusal, and integrity mutations. They do not prove live Slack behavior. A fresh source-bound gallery, independent
review and installed-wheel acceptance remain required. The prior gallery cannot authorize the patched source.

The TLS alerts require separate evidence-based review: Python 3.12 through 3.15 default contexts observed during
review require TLS 1.2, `CERT_REQUIRED` and hostname verification. This amendment leaves those defaults unchanged.

The canonical owning project `heinzel-slack` or protected `heinzel_slack._vendor.slack_sdk` target makes the security repair mandatory before upstream
identity is inspected. A raw distribution-name alias, version change, or coherently repacked wheel and lock cannot
select namespace-only mode. Changing the approved upstream identity requires a separately reviewed verifier change.

Malformed proxy CONNECT response parsing raises a fixed diagnostic with its exception context suppressed, so raw
status tokens and decoding errors cannot be copied into caller exception logs. This parser repair alone does not promise general SDK
debug-log secrecy; the owning adapter boundary separately isolates logging and refuses unsupported proxy schemes.

## Additional direct-route boundary

The owning adapter validates and pins direct or unauthenticated HTTP proxy configuration and supplies a private SDK
logger to both client types. To prevent urllib from independently rediscovering ambient proxies after a direct route
was selected, the same closed transform additionally repairs `slack_sdk/web/base_client.py`:

- Original SHA256: `fd7beafe11ec7a0661005c96617378ad4ff0873b5f095205ac993f1a762b88ae`.
- Repaired pre-relocation SHA256: `66bf86b8841a666edff4c0f22dbe74c8e0d76136815e83b082840e4f79fbffcd`.
- Only `BaseClient._perform_urllib_http_request_internal`'s no-proxy `urlopen` statement becomes a local opener
  using `ProxyHandler({})`, the existing `HTTPSHandler(context=self.ssl)` and the same request and timeout.

The exact class/method scope, original/postimage and projection hashes are checked. All three fixed repair members
must be present. Unaffected projects retain namespace-only projection. This does not enable general manifest patches.
