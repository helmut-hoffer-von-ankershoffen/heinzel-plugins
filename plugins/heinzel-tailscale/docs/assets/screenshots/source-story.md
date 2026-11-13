## Audience

Someone who wants to reach their authenticated Heinzel web app privately from another device and needs to understand what Tailscale adds, what it requires, and how to stop sharing.

## Outcome

Show the real sharing control becoming ready, the corresponding honest CLI status, and the control being turned off. The fictional example demonstrates local configuration and readiness; it does not prove that a remote phone can connect. Tailscale must already be installed and signed in, and the remote browser still needs authentication (`README.md`).

## Scenes

1. **Sharing ready — dark.** In the genuine footer Tailscale pane, turn on **Share over Tailscale** and wait for **Open**. Show the requested choice and the ready link together, using the fictional local node.
2. **Status after enabling — CLI.** Run `hz tailscale status --json`. Show the mapped target and `apply-required` if that is the actual separate CLI result: a CLI process cannot verify the web listener and must not claim web readiness.
3. **Sharing off — light.** Return to the same genuine pane, turn sharing off, and show **Off**. This is a meaningful second state of the actual feature, not a duplicate capture.
4. **Status after disabling — CLI.** Run `hz tailscale status --json` again to show the resulting unmapped state. Treat the target port and all other values as observed output, not a guarantee imposed by the caption.

Capture in this order with shared isolated fixture state. The existing plan already demonstrates the useful on/off flow and both applied appearances, so it is preserved. If capture isolation resets state between scenes, or the observed state differs from the captions, resolve that before publication rather than staging a result.

## Fictional fixtures

`docs/screenshot_fixture.py` supplies a fictional `workstation.tail-example.ts.net` node, a loopback-only LocalAPI, and an unrelated example service. It uses the plugin's real sharing operations and checks that the unrelated service remains unchanged. Its bootstrap is for an explicit capture only; it was inspected, not run. The fixture does not establish real Tailscale login, remote access, or phone pairing.

Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript.

## Privacy pitfalls

A copied URL may contain a session token and must be treated like a password (`README.md`). Do not capture or publish real tokens, credentials, user paths, hostnames, tailnet identities, peers, account details, or unrelated private content. The fixture's local credential is demonstration data, but should not be featured. Review every image and transcript independently, including Doctor and surrounding Core UI; stop on unknown identities rather than assuming they are fictional.

## Acceptance criteria

- Four distinct captures show genuine product surfaces, in sequence: ready and off in the feature pane, with the two corresponding useful CLI results. No forged HTML, terminal output masquerading as feature UI, duplicate captures, or caption-only state changes.
- The ready pane visibly reaches the real **Open** link; the off pane visibly reaches **Off**. Dark and light appearances are actually applied. Capture waits for real outcomes and does not manufacture them.
- CLI results agree with their captions and preserve the distinction between a mapped request and authenticated web readiness. If they do not, correct the capture or caption based on observed output.
- Captions identify demo data; all images and transcripts pass the independent privacy review described above. A successful local demonstration is not represented as proof of remote access.
- Use the existing bootstrap and plan; no invented fixture files or product screens. The plan below is structurally checked against the supplied format and existing declarations; no parser, project code, or capture was executed, so runtime validation remains required.

## Source-bound UI surface inventory

- `pyproject.toml`, `[project.entry-points."heinzel.modules"]`: the sole declared plugin entrypoint is `tailscale = "heinzel_tailscale"`. `src/heinzel_tailscale/__init__.py` declares `module.nav` with `NavSettings(sections=("tailscale",), group="computer")`, `module.settings(TailscaleSettings)`, and `module.status(source="status", slots={"footer": True, "sidebar": False})`. Core therefore renders a Settings contribution and a footer status pane; a missing plugin Page/View does not make this feature terminal-only. The supplied declaration does not establish a specific plugin navigation route, so the plan uses the existing `/` route and footer control.
- `src/heinzel_tailscale/__init__.py`, `sharing`: the footer contribution declares the Tailscale status item and **Share over Tailscale** toggle, with `enable` and `disable` operations, readiness-dependent URL, status/problem and Details data. The exact presentation depends on the installed Core's `ToggleControl` fields; older Core receives a shorter detail fallback. `README.md` describes Settings and footer entry points and the ready, retry, and Details experience. The plan requires the observed Core UI to support its named controls rather than assuming every Core version renders them identically.
- `src/heinzel_tailscale/_models.py`, `TailscaleSettings`: Core can render the **Private web sharing** settings section and HTTPS sharing port; the intent field is marked hidden and private. Settings is a real contribution but is not substituted for the two useful feature states.
- `src/heinzel_tailscale/__init__.py`, private `status`, `enable`, and `disable` operations: these support the Core control and CLI; the README also describes authenticated API and stdio MCP access, absent from unauthenticated REST and HTTP MCP heads. The supplied declarations show no channel, approval, setup, info, separate page, or separate view contribution. Generic Core surfaces beyond the declared settings and footer are not evidenced as plugin feature screens here.
- `README.md` documents `hz tailscale status --json`, `enable --json`, and `disable --json`. CLI results are genuine terminal output, not feature UI. `src/heinzel_tailscale/_readiness.py` and `_service.py` distinguish authenticated web readiness from a separate CLI's inability to verify the listener; the two status scenes deliberately show different states, not two parameters of a single operation because three operations are declared.
- The Tailscale application and its sign-in, HTTPS consent, and OS permission screens are external provider UI, not plugin screens (`README.md`). No such screen is invented or captured. `web/build.py` is a frontend build helper, not an additional declared module entrypoint or evidence of a product screen.
