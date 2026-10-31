# Security

Report a vulnerability privately through [GitHub's security advisory form](https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins/security/advisories/new). Please do not open a public issue.

In scope: the code in `plugins/` and `src/`, and the packages built from them. Examples are leaked credentials, commands run
from untrusted input, and plugins reaching data they were not granted.

Out of scope: weaknesses in the Heinzelmännchen core (report those to the core), and in tools the plugins call, such as `gh`, `acli`, `gws` and Tailscale.

The core's policy applies here too: [SECURITY.md](https://github.com/helmut-hoffer-von-ankershoffen/heinzel/blob/main/SECURITY.md).
