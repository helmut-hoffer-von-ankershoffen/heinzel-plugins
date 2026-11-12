## Audience
People who already use Tailscale and want to reach their authenticated Heinzelmännchen web app privately from another device, while retaining control over when sharing is enabled.

## Outcome
Show the opt-in journey: enable sharing, inspect the locally verified link controls at desktop and phone widths, check status from the CLI, and turn sharing off. The gallery should make clear that local readiness does not prove that a remote phone can connect or authenticate.

## Scenes
1. **Sharing ready:** In a light desktop view, turn on sharing and show the Tailscale pane with its Copy link and Open controls.
2. **Phone-width controls:** Show the same sharing pane in a dark, phone-sized view, illustrating how the controls fit on a smaller screen.
3. **CLI status while requested:** Show JSON status from a separate CLI process, including saved intent and mapping and any pending web verification.
4. **Sharing off:** Turn sharing off in the pane and show the resulting Off state.
5. **CLI status after removal:** Show JSON status after the off action, so the viewer can inspect the request and owned mapping state.

## Fictional fixtures
Use the existing `docs/screenshot_fixture.py` bootstrap and its isolated fictional Tailscale LocalAPI, example node name, and unrelated example service. Capture the scenes in plan order so the on and off status views reflect the corresponding actions. The fixture demonstrates local behavior; it does not establish a real tailnet connection.

## Privacy pitfalls
Use only the fictional profile and example data. Do not expose a real node name, account information, session token, sign-in link, or copied authenticated URL. A link containing a session token is a credential. The phone-width scene demonstrates layout, not a successful connection from a phone. Tailscale must already be installed and signed in for real use, and the remote browser still needs authentication.

## Acceptance criteria
- The desktop and phone-width views show the real Tailscale sharing pane in applied light and dark appearances, respectively.
- The ready view shows the Copy link and Open controls; the off view visibly reads Off.
- Both CLI captures show actual status output for their respective points in the sequence, without claiming that a separate CLI process verified the web owner.
- Captions identify the data as fictional and do not imply remote connectivity was tested.
- The unrelated fictional service remains intact, and no real credentials or personal network details appear.
- The TOML below preserves the existing five-scene plan. It was checked by inspection against the requested format; no parser or capture was run because execution was prohibited.
