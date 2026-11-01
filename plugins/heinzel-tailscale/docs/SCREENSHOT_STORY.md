**Audience**
People who already use Tailscale and want private access to their authenticated Heinzelmännchen workspace. The adapter is included in the standard app; Tailscale must already be installed and signed in, with the required HTTPS consent.

**Outcome**
A private link, with a clear off switch. Show the explicit enable action, verified readiness in the owning web app, a compact view of the link, useful CLI diagnostics, and confirmed shutdown. Authentication remains required.

**Scenes**
Preserve the existing five-scene sequence, names, routes, bootstrap, and CLI commands. The footer control is the plugin's useful interface; the source declares no dedicated plugin panel route.

1. **sharing-ready:** Open the footer's Tailscale region, enable sharing, and capture the ready message and Copy URL control. Crop to the region so the state and action are legible.
2. **phone-sharing-ready:** Inspect the same ready state at 390 × 844. This demonstrates the compact layout; it does not demonstrate a connection from another device. Leave Copy URL unclicked.
3. **sharing-request-cli:** Run `hz tailscale status --json` in a separate process. Expect saved intent and a matching mapping, with `state: apply-required`, `desired_enabled: true`, and `mapped: true`. Only the authenticated owning web instance can verify its live readiness.
4. **sharing-off:** Switch sharing off and capture “Private web sharing is off.”
5. **sharing-off-cli:** Repeat the status command and show `state: off`, `desired_enabled: false`, and `mapped: false`.

The changes address gaps in deterministic capture and truthful captions: add a fixed browser time, explicitly wait for readiness, identify fictional demo data, and clarify the narrow viewport and separate-process CLI result.

**Fictional fixtures**
Reuse the existing `docs/screenshot_fixture.py` during explicit capture only, in a fresh isolated temporary profile. It supplies `workstation.tail-example.ts.net`, fictional client discovery, and a loopback LocalAPI server. The real plugin performs its sharing transactions against that server. The fixture also retains an unrelated `svc:notes` service on port 8443 and checks its preservation. Start with sharing off and retain the same isolated state throughout the ordered scenes. No additional fixture files are required.

**Privacy pitfalls**
Copy URL may include a password-equivalent `#token=...` session fragment. Do not activate copying or sign-in-link actions during capture. Keep real hostnames, peer information, credentials, session fragments, and unrelated personal content out of every frame, including the full mobile-width view. Use only the isolated fictional profile. A ready local deployment does not establish actual remote reachability or grant a paired browser owner operations or terminal access.

**Acceptance criteria**
- All five scenes complete in order; the three UI views show working sharing controls and meaningful states.
- Both ready views contain the exact ready message and Copy URL control; the off view contains the explicit off message.
- CLI results show the expected pending-verification and off states without credentials.
- The existing fixture's unrelated-service preservation checks pass during capture.
- Every caption identifies fictional demo data and stays within 180 characters.
- The plan uses the existing bootstrap, supported local route, accessible targets, and shell-free argument arrays.
- Static validation against the supplied contract covers TOML table structure, unique lowercase scene names, allowed surfaces/actions, ISO8601 browser time, and scene count. No imports, product execution, network requests, or captures were performed; runtime acceptance remains to be verified during explicit capture.
