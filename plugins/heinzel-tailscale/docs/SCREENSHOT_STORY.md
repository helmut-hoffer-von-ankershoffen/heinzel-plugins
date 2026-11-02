**Audience.** Heinzelmännchen users who already use Tailscale and want private access from another authenticated browser. This adapter is included in the standard app; Tailscale itself must already be installed and signed in.

**Outcome.** Turn sharing on, see a locally verified private address, inspect it at phone width, then turn sharing off. The story makes the distinction between requested sharing and verified readiness visible. It demonstrates the existing footer control on `/`.

**Scenes.** Preserve the existing five-scene sequence and captions:

1. **sharing-ready:** Open the Tailscale footer control and explicitly enable sharing. Frame the switch, readiness explanation and Copy URL button together: a clear reward for one deliberate action.
2. **phone-sharing-ready:** Show the same ready state at 390 × 844. This demonstrates a usable control at phone width; it does not demonstrate a remote phone connection.
3. **sharing-request-cli:** Show `hz tailscale status --json`. The separate CLI reports `apply-required`, with `desired_enabled=true` and `mapped=true`. Explain that this process cannot verify the owning web app's live listener and authentication context, even when the browser view reports ready.
4. **sharing-off:** Explicitly disable sharing and capture “Private web sharing is off.” The user can see how to end sharing as readily as they started it.
5. **sharing-off-cli:** Repeat the status command after disabling. Show `state=off`, `desired_enabled=false` and `mapped=false` as the resulting state.

**Fictional fixtures.** Use only the existing `docs/screenshot_fixture.py` bootstrap during explicit capture. It supplies the fictional node `workstation.tail-example.ts.net`, emulates vendor discovery and runs an authenticated loopback LocalAPI for the real sharing transactions. Its existing unrelated `svc:notes` service must remain unchanged. Keep one isolated profile and shared fixture state across the ordered scenes; start with sharing off. Freeze browser time at the plan's existing timestamp.

**Privacy pitfalls.** Keep Copy URL visible but unclicked: a copied URL can contain the current session token. Exclude session fragments, sign-in links, pairing credentials, LocalAPI credentials and real account or machine information from every image. Tailnet membership does not replace browser authentication or grant owner authority. Fixture readiness proves local configuration behavior; it does not prove real certificates, remote connectivity or successful phone authentication.

**Acceptance criteria.**

- Preserve all five existing scenes, their order, routes, actions, captions and bootstrap.
- The ready UI must show the exact readiness message and Copy URL; the off UI must show the exact off message.
- At phone width, the sharing control and private address remain legible without horizontal clipping.
- Both CLI images show completed status results with the state distinctions above and fictional values only.
- The fixture's existing unrelated-service preservation checks must pass during capture.
- Static review confirms format 1, an existing relative bootstrap, ISO8601 browser time, unique lowercase scene names, permitted action shapes, fragment-free local UI routes and demo-labelled captions under 180 characters.
- Validation here is static. No code, bootstrap, capture or network operation was executed; rendered-image acceptance remains for explicit capture.
