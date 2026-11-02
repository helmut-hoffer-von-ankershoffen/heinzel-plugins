**Audience**
Heinzelmännchen users who already use Tailscale and want private access to their authenticated workspace. This adapter is included in the standard app; Tailscale must already be installed and signed in.

**Outcome**
“Ready at your desk, readable in your pocket, easy to switch off.” Show an explicit sharing action, verified local readiness, and a clear return to OFF. Preserve the existing five-scene plan unchanged: it already demonstrates useful behavior through the operational footer control and real CLI results.

**Scenes**
1. **sharing-ready:** Open the Tailscale footer control and enable sharing. Frame the ready message, enabled switch, fictional HTTPS address, and Copy URL action together.
2. **phone-sharing-ready:** Show the same ready state at 390 × 844. Demonstrate a readable mobile layout; this is a local browser viewport, not evidence of a remote phone connection.
3. **sharing-request-cli:** Run `hz tailscale status --json` in a separate CLI process. Show saved intent and the matching mapping while web verification remains pending in that process. Expected fields include `state: apply-required`, `desired_enabled: true`, and `mapped: true`.
4. **sharing-off:** Explicitly switch sharing off and capture the resulting OFF message in the same control.
5. **sharing-off-cli:** Repeat the status command after disabling. Show `state: off`, `desired_enabled: false`, and `mapped: false` as evidence that the owned mapping was removed.

**Fictional fixtures**
Use only the existing `docs/screenshot_fixture.py`, during explicit capture, with one temporary isolated profile shared across the ordered scenes. It supplies `workstation.tail-example.ts.net`, fictional signed-in node facts, and a loopback LocalAPI fixture. Real plugin transactions operate against that fixture. Its existing unrelated `svc:notes` service must remain intact. Keep the existing frozen browser time. No additional fixture files are needed.

**Privacy pitfalls**
Do not copy or expose a session-bearing URL: its token grants session access. Keep real hostnames, credentials, account details, and clipboard contents out of captures. Tailnet membership alone does not authenticate a browser. The mobile scene proves layout only; local readiness does not prove remote connectivity, network policy, or browser pairing.

**Acceptance criteria**
- Capture all five scenes in order, retaining the three useful UI views and two CLI results.
- Ready views show the authenticated-browser readiness message and Copy URL action; the OFF view shows the explicit off message.
- Separate CLI status must not claim web readiness. Status reads must not enable sharing.
- All captions identify fictional demo data, and the phone caption discloses that no remote connection was tested.
- Keep only the supplied local route, accessible interactions, existing bootstrap, and argument-array CLI commands.
- The returned TOML was manually checked against the supplied contract: valid table structure, five unique lowercase scene names, captions under 180 characters, and an ISO8601 browser time. Parser validation and capture verification were not run because execution was prohibited.
