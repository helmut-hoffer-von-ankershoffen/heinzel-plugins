# Verified Slack SDK projection

The adapter imports a closed projection of the official Slack SDK inside `heinzel_slack._vendor.slack_sdk` so the
host captures its Python source together with the adapter. This adds no Slack dependency, runtime allowlist or
provider knowledge to core. The host still applies its original source, origin and size checks.

The upstream input is the [official Slack SDK 3.46.0 wheel](https://pypi.org/project/slack-sdk/3.46.0/#files), retained
under `vendor-provenance/`. Its SHA256 is pinned in `vendor-manifest.json` and the owning hashed dependency lock.
The manifest records the exact wheel name, distribution/version, MIT license path, namespace mapping, transform
version, and every original and projected file hash. The upstream `py.typed` and MIT copyright/license notice are
preserved. The external SDK dependency remains in the lock as an additional vulnerability-audit inventory entry;
it is not imported by the adapter's runtime path.

The subset is the static transitive import closure of `WebClient` and the built-in Socket Mode client, including
package initializers, their synchronous model and retry helpers, the typing marker and license. The unused async,
OAuth and alternative websocket implementations are outside that closure. The manifest contains 49 Python files,
one typing marker and one license; no extra or missing SDK files are accepted.

`heinzel_plugin_tools.vendor` owns generation and verification. The owning transform is
`namespace-relocation-v1+slack-sdk-3.46.0-security-v3`. It applies exact, hash-pinned source repairs before the
ordinary import-prefix relocation: frame masks use four OS entropy bytes, direct sockets always establish TLS,
and proxy credentials/request or response bodies stay out of diagnostics. The proxy environment helper still
selects the same value without logging it. The frame reader retains empty partial messages and request token selection
retains its client, query, then JSON precedence. The original upstream wheel and original member hashes are retained.

These are verifier-owned fixed statements, not manifest-provided patch parameters. Independent function-scoped
AST edits and exact pre/post hashes reject any additional logic change. The four required members cannot be omitted,
and the old namespace-only mode is refused for this owner and pin. Other SDK files retain their ordinary
namespace-only projection. Dynamic import/execution, unexpected namespace identifiers and unsupported files remain
refused. Do not format or hand-edit projected files. See the [security amendment](../../../docs/adr/0002-pinned-slack-security-repair.md).

The upstream proxy CONNECT implementation still supports authentication on its first hop, so the owning adapter
refuses authenticated proxies. It wraps a supported unauthenticated tunnel with its existing TLS context. Nonstandard direct ports also use that context; TLS
failure does not fall back to cleartext. The adapter uses Python's certificate and hostname verification and enforces a TLS 1.2 floor for the default
Socket Mode context. A stronger platform minimum is preserved. Core import policy and retry behavior are unchanged. This is not a claim that arbitrary SDK tracing of every other protocol field is safe.

The existing gallery describes the previous source and needs a fresh source-bound capture and independent review.
Offline transport fixtures prove frame construction and socket/diagnostic choices, not live Slack delivery or an
installed-wheel acceptance run. Publication remains gated on fresh gallery and installed acceptance.

From this plugin directory, the vendor-aware toolkit can reproduce the current projection offline:

```python
from pathlib import Path
from heinzel_plugin_tools.vendor import project, regenerate

root = Path.cwd()
regenerate(root)
project(root)
```

An upstream upgrade changes the wheel pin, complete static closure, manifest and generated projection together and
requires independent security review. Verification runs before formatting, checks and builds, and compares the exact
SDK inventory in the built plugin wheel with the reviewed projection. Exemptions apply only to successfully verified
listed upstream implementation files. The first-party `_vendor/__init__.py`, adapter, tests and all other owned
files keep their existing checks. Both strict type checkers accept valid SDK constructors and reject invalid
credential argument types; dependency implementation handling does not replace their annotations with `Any`.

Installed acceptance boots the actual SDK and plugin wheels without a manual runtime preload. It confirms notices
and approval requests through the ordinary authenticated human review surface, then passes a synthetic owner click
through the real Slack decision/store code and the real host consumer to an independently captured fixture writer.
The Slack Web API is a loopback stand-in; it uses the actual projected Web API client. Wrong scope/account,
non-owner and unauthenticated attempts, repeated confirmation/consumption and captured-source tampering refuse
without an extra post or write. The fixture evidence covers the offline approval and delivery boundaries.

Malformed proxy CONNECT response parsing raises a fixed diagnostic with its exception context suppressed, so raw
status tokens and decoding errors cannot be copied into caller exception logs. This parser repair alone does not promise general SDK
debug-log secrecy; the owning adapter boundary separately isolates logging and refuses unsupported proxy schemes.

## Owning adapter credential boundary

The owning Web API and Socket Mode adapters pass a private disabled, non-propagating SDK logger to both clients,
including the WebClient used to obtain Socket Mode tickets. Host DEBUG settings cannot expose SDK response bodies
through this logger. The plugin continues to report its own fixed, credential-free operation errors.

The adapter snapshots the SDK's documented proxy environment precedence before constructing clients. Direct
connections and unauthenticated `http://host[:port]` CONNECT proxies remain supported. HTTPS/SOCKS proxy URIs,
userinfo (including authenticated HTTP proxies), malformed ports, paths, queries and fragments are refused before
SDK construction. This intentionally removes previously accepted configurations: the builtin transport cannot protect
proxy credentials on its plaintext CONNECT first hop. An `HTTPS_PROXY` variable containing an unauthenticated
`http://` URL is supported; the variable names the destination protocol, not the proxy transport.

Clients retain that snapshot. SDK constructor fallback is overwritten before requests, and the pinned no-proxy Web
API branch uses a local opener with an empty ProxyHandler instead of urllib's ambient/global opener. Later environment
or OS proxy changes cannot redirect these clients. No process environment, global logger or global opener is mutated.
These guarantees cover this plugin's constructed clients, not arbitrary direct use of the upstream SDK.
