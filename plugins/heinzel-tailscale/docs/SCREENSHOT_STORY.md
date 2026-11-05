## Audience

A Heinzelmännchen user considering private access from another device who wants to understand what the Tailscale plugin does, what readiness means, and how to turn sharing off.

## Outcome

Show an explicit opt-in, the authenticated web app’s verified ready state, a legible phone-width view, and an explicit off state. Pair those views with separate CLI status results so readers can see that a saved request and mapping do not by themselves prove web readiness. The demo does not establish that a remote phone connected. Tailscale must already be installed and signed in, and a fresh browser still needs authentication (`README.md`; `src/heinzel_tailscale/_readiness.py`, `SharingReadiness.verifies`).

## Scenes

Capture in plan order with the existing isolated bootstrap and shared demo state:

1. **sharing-ready:** In the dark app, open the footer’s Tailscale control, enable sharing, and wait for the genuine authenticated-browser ready message and Open link. This shows the actual control and verified result.
2. **phone-sharing-ready:** Show that same ready state at 390 × 844. This is distinct viewport coverage: inspect legibility and clipping, without claiming a phone connection.
3. **sharing-request-cli:** Run `hz tailscale status --json` in the separate CLI process. Show the saved request and mapping with web verification pending; do not portray it as the web owner’s ready state.
4. **sharing-off:** In the light app, turn sharing off and wait for the explicit off message. This is a meaningful changed state of the same feature control.
5. **sharing-off-cli:** Run the status command again after the off action to inspect the request and mapping in the changed state.

The two CLI captures use the same command against different meaningful shared states. They are CLI results, not feature UI. Do not replace any scene with a duplicate, a caption-only variation, terminal output presented as feature UI, or forged HTML. The Open links are readiness waits, not click targets; do not click credential links.

## Fictional fixtures and presentation

`docs/screenshot_fixture.py` supplies the existing isolated bootstrap: a fictional `workstation.tail-example.ts.net` node, a loopback-only LocalAPI, and an unrelated fictional notes service whose configuration must remain intact. Its demo CLI substitutes discovery reads while the real Serve store performs the local transaction. Capture uses this existing script only during explicit capture; no new fixture files are assumed.

Normal presentation fictionalization is disclosed: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript.

## Privacy pitfalls

A copied URL can contain a session token and must be treated like a password (`README.md`). Do not click or expose sign-in or credential links, LocalAPI credentials, real hostnames, user paths, account identifiers, or real network data. The fixture’s example hostname and local credential are demonstration data, not evidence that all captured material is safe. Independently inspect every image and transcript, including Doctor details and terminal output; fail on unknown identities rather than silently rewriting them.

## Acceptance criteria

- Preserve all five scenes, their actions, readiness waits, time budgets, and existing optional controls. Capture the phone scene at 390 × 844 and verify readable, unclipped content.
- The dark ready scene and light off scene show their applied appearances. Ready requires the stated message and Open link; off requires the stated off message. Neither Open link nor a credential link is clicked.
- The CLI results reflect their respective shared fixture states. The first must not claim authenticated web readiness from a separate process; the second must reflect the off request and mapping. Terminal actions already wait for completion, so do not add exact table-cell waits.
- Preserve the unrelated fictional service. Do not claim remote access, authentication, network policy, installation, or live Tailscale connectivity was tested.
- Review all captures and transcripts independently for privacy and factual fidelity. Reject duplicate captures, caption-only differences, forged UI, and unverified identities.

## Source-bound UI surface inventory

- **Plugin entrypoint:** `pyproject.toml`, `[project.entry-points."heinzel.modules"]`, declares `tailscale = "heinzel_tailscale"`; `src/heinzel_tailscale/__init__.py` declares `module = Module("tailscale", ...)`.
- **Genuine Core-rendered feature UI:** `src/heinzel_tailscale/__init__.py`, `@module.status(source="status", slots={"footer": True, "sidebar": False})` and `sharing`, contributes the Tailscale footer item, detail lines and `ToggleControl`, wired to `enable` and `disable`; its URL is supplied only when ready. The existing plan’s `/` route opens this control. Ready and off are useful states of this actual feature flow.
- **Core settings UI:** `module.nav(... settings=NavSettings(sections=("tailscale",), group="computer"))` and `module.settings(TailscaleSettings)` declare a settings contribution, not a demonstrated standalone plugin page route. `src/heinzel_tailscale/_models.py`, `TailscaleSettings`, declares the HTTPS port and a hidden private intent. `README.md` also describes Settings access. The provided files do not establish a specific settings panel route, so none is invented.
- **Operations and generic Core surfaces:** `src/heinzel_tailscale/__init__.py` declares private `status`, `enable`, and `disable` operations; the latter two are mutating. `README.md` describes authenticated API and stdio MCP exposure and exclusion from unauthenticated REST and HTTP MCP heads. These declarations establish operations, but the provided source does not establish additional operation, approval, channel, setup, info, or plugin-specific page screens to capture. The status toggle can carry `apply_settings` into a shared apply flow, but its exact rendered appearance is not established here. Absence of a Page or View declaration alone would not prove terminal-only behavior.
- **CLI:** `README.md` documents `hz tailscale status|enable|disable --json`; the plan uses status before and after the UI action. `src/heinzel_tailscale/_service.py` distinguishes `ready` from `apply-required`, while `_readiness.py` requires the authenticated owning web runtime for verification. The CLI output is a genuine command result, not a substitute for the feature UI.
- **External provider UI:** Tailscale installation, sign-in, HTTPS consent, and OS permissions belong to the external Tailscale or operating-system experience (`README.md`); no such screen is declared or captured here. `web/build.py` is a frontend build helper, not a declared product screen.
- **Evidence boundary:** The existing catalog captions in `pyproject.toml` describe the CLI scenes more specifically than the plan captions. The source supports the intended distinctions, but actual capture output and sequencing must be inspected before asserting the pictured values. The provided files do not include Core’s rendering implementation or a capture transcript, so exact additional generic surfaces and successful capture remain unverified.
