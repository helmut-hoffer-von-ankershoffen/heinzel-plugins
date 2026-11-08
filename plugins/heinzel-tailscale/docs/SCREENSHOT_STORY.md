## Audience

Someone who wants to reach an authenticated Heinzelmännchen web app over their private Tailscale network and wants to understand both the setup and how to turn it off.

## Outcome

Show a fictional local sharing request progressing to a confirmed ready control, an inspectable CLI status, and an explicit return to off. The demo does not establish that a remote phone can connect: Tailscale login, network policy, and the remote browser’s authentication still matter. Tailscale must already be installed and signed in; the plugin does not perform login or grant HTTPS consent (`README.md`).

## Scenes

1. **Sharing ready, dark:** Open the genuine footer sharing pane and turn on **Share over Tailscale**. Capture its ready state with the fictional address and **Open** action. Readiness is a verified web-owner state, not merely the requested switch value (`src/heinzel_tailscale/__init__.py`, `sharing`; `src/heinzel_tailscale/_readiness.py`, `SharingReadiness.verifies`).
2. **Saved request, CLI:** Inspect `hz tailscale status --json` after enabling. Show the actual result, including the requested state, mapping and explanation. A separate CLI cannot itself verify the owning web listener, so do not relabel an `apply-required` result as ready (`src/heinzel_tailscale/_service.py`, `Sharing._state`; `src/heinzel_tailscale/_readiness.py`, `SharingReadiness`).
3. **Sharing off, light:** Return to the same real pane and explicitly switch sharing off. This is a different useful state of the feature, not a second caption on the ready image. The operation removes only its still-matching owned mapping and the origin permission it added (`src/heinzel_tailscale/_service.py`, `SharingActions.disable`).
4. **Off, CLI:** Repeat the status command after switching off to show the changed request and mapping state. Preserve the actual output and its explanation.

These scenes retain the useful ready/off and CLI sequence in `docs/screenshots.toml`. The existing phone-width ready scene is omitted because it repeats the same feature state without adding a distinct behavior. Capture in the listed order against the same isolated fixture state; verify that the capture runner preserves that state between scenes before relying on the sequence.

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap only during explicit capture. It supplies the fictional node `workstation.tail-example.ts.net`, a loopback-only LocalAPI, and a pre-existing fictional `svc:notes` service. Its `DemoCli` substitutes vendor discovery reads while the real Serve store performs conditional local HTTP transactions; the fixture checks that the unrelated service remains unchanged. It does not demonstrate a real Tailscale account, an external provider screen, or a remote connection.

## Privacy pitfalls

Normal presentation fictionalization is expressly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and an independent reviewer must inspect every image and transcript.

Do not expose session fragments, sign-in links, real hostnames, usernames, paths, credentials, peer information, or unrelated profile data. **Copy URL** can include a session token and must be treated like a password (`README.md`). A fictional fixture password is not a reason to publish credentials. If a surface or identity cannot be verified and safely handled, reject the capture rather than guessing or masking additional content.

## Acceptance criteria

- All four captures come from the genuine app or CLI using the existing bootstrap; no forged HTML, terminal output presented as feature UI, duplicate images, or caption-only changes.
- The ready and off panes show their actual corresponding states; the CLI transcripts reflect the actual output at each point, including any lack of web-owner readiness. The unrelated fictional service remains intact.
- Light and dark appearances are actually applied and visibly checked. Captions identify demo data and make no remote-access claim.
- Independently inspect every full image, crop, and transcript for privacy and truthful state before publication. Reject unknown identities and any unexpected real data. Presentation mappings alone do not constitute privacy approval.
- Verify accessibility targets and state persistence during capture; fail visibly if the pane, switch, expected link, or off state is unavailable. No capture or runtime validation was performed in preparing this plan.

## Source-bound UI surface inventory

- **Plugin entrypoint:** `pyproject.toml`, `[project.entry-points."heinzel.modules"]`, declares `tailscale = "heinzel_tailscale"`; `src/heinzel_tailscale/__init__.py` defines `module = Module(...)`. The actual declarations are a settings navigation contribution, settings model, services, three private operations, and a footer status contribution. No plugin Page or View is declared; that fact alone would not rule out Core-rendered UI.
- **Core-rendered feature UI:** `module.status(source="status", slots={"footer": True, "sidebar": False})` and `sharing` declare a `StatusItem` with a `ToggleControl`, enable/disable `RunOperation`s, and a URL only when ready. This is the feature surface used by the plan. The declaration supports requested versus checked states and, depending on Core compatibility, status/problem/explanation or a fallback detail line. Exact rendering and accessible names remain capture-time evidence (`src/heinzel_tailscale/__init__.py`).
- **Core settings UI:** `module.nav(... settings=NavSettings(sections=("tailscale",), group="computer"))` and `module.settings(TailscaleSettings)` contribute settings. `TailscaleSettings.https_port` is the visible HTTPS port choice; `intent` is marked hidden and private (`src/heinzel_tailscale/_models.py`). No specific settings route is established by the supplied declaration, so the plan does not invent one. `README.md` also describes the sharing control in Settings; the exact Core rendering and route remain unverified here.
- **Operations and other generic surfaces:** `status`, `enable`, and `disable` are private operations, with the latter two mutable (`src/heinzel_tailscale/__init__.py`). The README describes authenticated API and stdio MCP access and their absence from unauthenticated REST and HTTP MCP heads. No channel, approval, setup, info, custom page, or additional footer contribution is declared in the supplied module. Generic Core rendering beyond the declared status and settings contributions is not established by these sources.
- **CLI and external provider:** The documented `hz tailscale status|enable|disable --json` commands are CLI access to the same operations (`README.md`); they are not evidence that the feature is terminal-only. Tailscale’s own app, login, certificate consent, and Serve tooling are external provider surfaces, not plugin screens. `web/build.py` is build tooling and supplies no evidenced product screen. The CLI status may differ from the authenticated web pane because only the owning web runtime can confirm the listener and loaded origin; this is a documented boundary, not a contradiction to hide (`src/heinzel_tailscale/_readiness.py`).
