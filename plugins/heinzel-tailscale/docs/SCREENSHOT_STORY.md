# Share the running app privately, then stop sharing it.

Show the actual sharing state machine: enable a private link, inspect/copy its address, use the control on a phone,
and turn it off. The point is convenient private access with clear ownership, not a settings field for a port.
This plugin contributes a real footer popover and toggle through the host's UI contracts; use those controls.

## Runtime and command boundary

The actual operations are `hz tailscale status`, `hz tailscale enable` and `hz tailscale disable`. They are declared
private API operations and are used by the footer control. `enable` and `disable` change state; capture them only
against a local fixture. The private/read-only declarations do not add a generic CLI `--confirm` flag. Never run the developer's Tailscale client, Serve configuration or network.

## Required scenes, in gallery order

| Scene | Surface and actual action | Visible result and caption | Why it matters |
| --- | --- | --- | --- |
| Private sharing ready | UI: open the footer Tailscale popover; enable switch “Share over Tailscale”; wait for ready | Actual checked switch, ready state, fictional HTTPS host and “Copy URL” control. Redact the session fragment before saving. Caption: “Share the running app privately — local Tailscale fixture; session token hidden.” | Shows the feature's central benefit in one image. |
| Useful on the phone | UI: at 390 × 844, open the same sharing popover in its measured location | The same ready switch and copy action fully inside the viewport. Caption: “Inspect and copy the private link on a phone — local simulated network.” | Shows the control remains practical on the second device. |
| Saved request in a shell | CLI: `hz tailscale status --json` against the same fixture | Actual separate-process status with desired_enabled true and a safe fictional origin; it may correctly be apply-required because only the authenticated web owner can prove readiness. Caption: “Inspect the saved sharing request from the CLI — fictional local network.” | Shows observability for power users and automation. |
| Stop explicitly | UI: disable the same switch and wait for final off state | Unchecked switch, off message, no Copy URL action. Caption: “Stop the app's sharing while preserving unrelated services — local fixture.” | Shows clear control over the lifecycle. |
| Confirm the final state | CLI: `hz tailscale status --json` after disabling | Actual off state with `desired_enabled` false and no usable session URL. Caption: “Verify sharing is off from the shell — local fixture.” | Makes the visible switch change verifiable. |

The checked-state and off-state screenshots must represent actual successful local fixture operations, not seeded
JSON pasted into the browser. At least one UI scene shows the complete compact footer/popover context, not just an
isolated switch. If the current runner restarts the bootstrap for each CLI command, persist only its local fixture
state within the capture session so CLI and UI phases agree; otherwise use explicitly separate ready/off fixtures
and label them as such.

## Fixture entry points

[tests/fixtures/tailscale_web.py](../tests/fixtures/tailscale_web.py) already runs the real host with fake vendor
reads, an authenticated loopback LocalAPI, conditional ServeStore writes and restart handling. Its vendor identity
is `workstation.tail-example.ts.net`. Adapt that fixture into an owning documentation bootstrap; retain actual
`Sharing`, `SharingActions`, `SharingReadiness`, `ServeStore`, lock and host policy. Keep an unrelated existing
service in the fixture and assert it survives both transitions. The sample's local API password must never appear
in output or images.

The [mounted browser test](../tests/browser/web_test.py) and
[actual browser driver](../web/e2e/tailscale.mjs) verify enable, copy, phone layouts and disable without OS changes.
Reuse their readiness and geometry assertions, not their use of a live visible session fragment in a screenshot.

## Accessible actions

- On desktop, open the footer control named **Tailscale**; if it is in the compact overflow, first use `button`
  **More status items**. Confirm `region` **Tailscale** is visible. If the footer trigger's name differs in the
  installed host, inspect its computed accessible name and use that actual name in the plan.
- Toggle `switch` **Share over Tailscale**, wait for the final checked state with no busy indicator, then wait for
  `button` **Copy URL**. An enabled setting by itself is not proof of readiness.
- At phone width the switch and Copy URL button must remain visible, keyboard-reachable and inside the viewport.
  Do not capture before font/layout measurement finishes.
- Disable and wait for the switch to be unchecked and settled and Copy URL to disappear; verify API state is off.

## Privacy and acceptance

The real host deliberately displays and copies an authenticated URL containing `#token=...`. **Never publish that
fragment**, even for a temporary capture server. Replace the visible fragment with an explicit `[session token
hidden]` presentation redaction before every screenshot, including diagnostic captures, and record that redaction
in provenance. Do not alter the underlying host operation or pretend the redacted URL is directly usable. Never
serialize clipboard content, announced session addresses, local API passwords or browser storage into metadata.
Stop the capture server before staging artifacts; review OCR/plaintext and images for tokens as well as paths.

All traffic stays on loopback and all vendor operations hit the fake LocalAPI. Assert exactly the expected enable
and disable writes, unrelated service preservation, actual ready/off responses, and no real vendor executable.
Use the fictional hostname only; reject real tailnet names, device names, account names, IPs and absolute paths.
The complete gallery includes desktop ready, phone ready, off, and CLI evidence; settings and help do not count.

## Implemented fixture boundary

The documentation bootstrap binds `DemoCli` for vendor discovery only. The production `ServeStore` still performs
authenticated conditional HTTP transactions against a loopback LocalAPI, and production sharing actions persist
the actual requested state and update the live host origin policy. An unrelated fictional service is asserted
unchanged after each write and at shutdown. State is shared only within this temporary capture profile.
The standalone CLI correctly cannot claim authenticated web readiness; the ready UI frame is the evidence for that
state. No vendor executable, OS network setting or real tailnet is used.
