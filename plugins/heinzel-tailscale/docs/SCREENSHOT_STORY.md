## Audience

Someone who already uses Heinzelmännchen and Tailscale and wants to reach their authenticated web app privately from another device.

## Outcome

Show how an explicit sharing choice becomes locally verified, how it looks at phone width, and how to turn it off. Make clear that local readiness does not prove a remote phone can connect or authenticate. Tailscale must already be installed and signed in; the adapter is included in the standard app and sharing starts off.

## Scenes

1. **Sharing ready:** In the light desktop view, enable sharing and show the verified readiness message and Copy URL control.
2. **Phone-width view:** In the dark view, inspect the same ready state at a phone viewport. This is a responsive local view, not a remote connection test.
3. **CLI request status:** Show JSON status from a separate CLI process, including saved intent and mapping while web-owner verification remains pending.
4. **Sharing off:** Turn sharing off in the desktop control and show the resulting off state.
5. **CLI off status:** Show JSON status after the owned mapping is removed and the request is off.

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap and its temporary fictional profile. It simulates a signed-in node named `workstation.tail-example.ts.net` and an unrelated notes service, using a loopback-only LocalAPI. Capture scenes in plan order so the ready and off states follow the explicit UI actions.

## Privacy pitfalls

Do not capture real tailnet names, peers, account details, LocalAPI credentials, session tokens, or sign-in links. Copy URL can include a bearer token in its fragment; do not expose a copied link. The fixture demonstrates local behavior and preservation of an unrelated service, not actual remote access.

## Acceptance criteria

- Both light desktop and dark phone-width views show useful sharing controls and the ready message; the phone scene makes no remote-access claim.
- The separate CLI status distinguishes saved intent and mapping from verification by the owning web app.
- The off UI and subsequent CLI result show the change after the explicit toggle; the fictional unrelated service remains intact.
- Captions identify the demonstration data, and captures contain no real credentials or account information.
- The existing plan is preserved: its five scenes already cover the useful workflow. The TOML was checked against the requested structure by inspection; capture and runtime validation were not performed.
