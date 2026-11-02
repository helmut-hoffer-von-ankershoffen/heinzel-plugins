**Audience**

Owners who already use Tailscale and want explicit private sharing of their authenticated Heinzelmännchen app. The adapter is included in the standard app; Tailscale installation, login and HTTPS consent remain prerequisites.

**Outcome**

“Share deliberately, see what is ready, switch off cleanly.” Show the real footer sharing control producing a verified local readiness result, a usable compact layout and an honest CLI inspection. Readiness confirms the local setup; it does not prove that a remote phone can connect.

**Scenes**

1. **sharing-ready:** Open the Tailscale footer region on `/`, explicitly enable sharing, and capture the readiness message, enabled control and Copy URL action. Crop to the region so the result is easy to read.
2. **phone-sharing-ready:** Show that same ready state at 390 × 844. This is a responsive local browser preview, clearly captioned as fictional and without a remote connection test.
3. **sharing-request-cli:** Run `hz tailscale status --json` in a separate CLI process. Show the saved request and matching mapping with web verification pending. The distinction between requested and verified state is useful product behavior.
4. **sharing-off:** Explicitly turn sharing off through the same footer control and capture the off message.
5. **sharing-off-cli:** Inspect JSON status again to confirm that the request is off and the matching mapping is absent.

Preserve the existing five-scene plan unchanged: it already demonstrates useful behavior through two ready UI views, an explicit off result and two meaningful CLI results. The supplied navigation declaration exposes settings; the story uses the existing `/` footer control rather than assuming a dedicated plugin panel route.

**Fictional fixtures**

Use the existing `docs/screenshot_fixture.py` only during explicit capture, in the temporary isolated profile described by the supplied docs. It supplies `workstation.tail-example.ts.net`, emulates Tailscale discovery, and exercises the real sharing transactions against an authenticated loopback-only fictional LocalAPI. Its existing unrelated `svc:notes` service must remain intact; the fixture checks that preservation. Do not present that check as information visible in the status screenshots.

Keep the existing frozen browser time and scene order. The ready views and first CLI result depend on enabling first; the final CLI result depends on the preceding disable action. No additional fixture files are needed.

**Privacy pitfalls**

- Every caption identifies the fictional local demo. Keep real hostnames, accounts, peer information and personal workspace content out of the capture profile.
- Copy URL can include a session-bearing `#token=...` fragment. Show the action without clicking it, exposing clipboard contents or publishing a sign-in link.
- Tailnet membership does not replace app authentication or grant backend-owner operations and terminal authority.
- A phone-width preview must not imply device pairing, completed HTTPS consent or successful remote access.

**Acceptance criteria**

- Preserve all five scene names, captions, commands and ordering.
- The ready UI displays the exact readiness message and Copy URL action after explicit enabling.
- The phone view keeps the readiness information and sharing controls readable without clipping.
- The first CLI result reports `state = apply-required`, `desired_enabled = true` and `mapped = true`; it does not claim web readiness from a separate process.
- The off UI displays the exact off message. The final CLI result reports `state = off`, `desired_enabled = false` and `mapped = false`.
- The unrelated fictional service survives both transactions.
- Captures show actual rendered UI and completed CLI output, with no invented screens, external navigation or secret-bearing links.
- Static review confirms the supplied TOML structure, allowed fields, unique lowercase scene names, caption lengths, local routes and existing relative bootstrap path. Parser validation and capture verification were not run under the no-code-execution constraint.
