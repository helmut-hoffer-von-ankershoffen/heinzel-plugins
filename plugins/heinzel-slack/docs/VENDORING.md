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

`heinzel_plugin_tools.vendor` owns generation and verification. Its fixed `namespace-relocation-v1` transform changes
only absolute import module prefixes. Relative imports, annotations, string literals, comments and program logic
stay unchanged. Independent AST equivalence rejects edits outside that mapping; dynamic import/execution,
unexpected namespace identifiers and unsupported files are refused. Do not format or hand-edit projected files.

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
