## Audience

Someone who wants to reach their authenticated Heinzel web app from another device on their tailnet and wants to understand both the convenience and the limits before installing.

## Outcome

Show an explicit, reversible sharing choice: turn it on, inspect the saved request and mapping, turn it off, and inspect the result. The fictional ready state demonstrates local readiness, not proof that a phone can connect. Tailscale must already be installed and signed in, and the other browser still needs authentication (`README.md`).

## Scenes

1. **Ready, dark:** Open the genuine Tailscale footer pane and enable sharing. Show the switch on and the fictional URL with its Open action. The URL appears only once the authenticated web owner verifies the listener, origin policy and matching mapping (`src/heinzel_tailscale/__init__.py`, `sharing`; `src/heinzel_tailscale/_readiness.py`, `SharingReadiness.verifies`).
2. **Request, CLI:** Run `hz tailscale status --json` after enabling. Inspect the saved request, mapping and reported readiness without claiming that a separate CLI can verify an arbitrary web listener (`README.md`; `src/heinzel_tailscale/_models.py`, `SharingState`).
3. **Off, light:** Return to the same real footer pane and turn sharing off. This is a meaningful second state of the feature, showing the explicit stop control rather than a different caption on the ready capture.
4. **Off, CLI:** Run the same status command after disabling to inspect the changed request and mapping. These two CLI captures are different state cases, not duplicate output.

Capture in this order with shared fixture state. The existing plan already describes this useful sequence, so it is preserved. Confirm the observed CLI values and both applied appearances during capture; do not substitute an expected result for an observation.

## Fictional fixtures

`docs/screenshot_fixture.py` is the existing local bootstrap. It supplies a fictional `workstation.tail-example.ts.net` node and a loopback-only LocalAPI, while the real sharing service performs the transaction. Its unrelated fictional `svc:notes` service is required to remain unchanged. The fixture does not demonstrate a real tailnet, remote device, login or phone connection.

Normal presentation fictionalization is explicitly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail; independent review must inspect every image and transcript.

## Privacy pitfalls

The fictional origin is safe only if capture actually uses the isolated fixture. Do not expose real hostnames, account identifiers, paths, credentials, LocalAPI passwords, session fragments or copied sign-in links. The README says a copied URL may contain a bearer session token; never expose or exercise that token in the gallery. Inspect all images and transcripts independently, including surrounding Core chrome and Doctor details, and reject unknown identities rather than assuming they are fictional.

## Acceptance criteria

- All four captures come from the real application or CLI using the existing fixture and the declared sequence; no forged HTML or terminal output presented as feature UI.
- The dark ready and light off captures show the applied appearances and genuinely different switch states. Ready includes the fictional link and Open; off shows the stopped choice. Neither is a duplicate or caption-only change.
- Both CLI results are legible and show their actual, different request/mapping states. Do not claim CLI readiness beyond what its output establishes.
- Captions identify demo data. No capture implies that the plugin installs Tailscale, signs in a user, grants permissions, or proves remote access.
- Independently review every image and transcript for privacy, including any Doctor row. Any unknown identity fails review. Verify the fictional unrelated service remains unchanged and the fixture has no connected accounts.
- The plan is statically checked against the requested format and retains the existing bootstrap, scenes and commands. No capture or runtime validation was performed because the request prohibits code execution.

## Source-bound UI surface inventory

- **Core-rendered feature UI:** `src/heinzel_tailscale/__init__.py` declares `module.nav(... settings=NavSettings(sections=("tailscale",), group="computer"))`, `module.settings(TailscaleSettings)`, and `@module.status(source="status", slots={"footer": True, "sidebar": False})`. The status supplies a `ToggleControl` with enable/disable operations and a ready-only URL. The existing plan targets the Tailscale footer region on `/`; `README.md` also describes the Settings control. No separate plugin panel route is declared, so none is invented.
- **Settings contribution:** `src/heinzel_tailscale/_models.py`, `TailscaleSettings`, declares the HTTPS sharing port and a hidden, private intent. It is a Core settings surface, not evidence of a separate custom page.
- **Operations and CLI:** `src/heinzel_tailscale/__init__.py` declares private `status`, `enable` and `disable` operations; `README.md` documents their CLI and authenticated API/stdio MCP access. The Core footer control invokes the latter two, so these operations are not CLI-only. The CLI JSON results are nevertheless useful companion captures.
- **External provider UI:** Tailscale installation, sign-in, HTTPS consent and OS permissions belong to Tailscale or the operating system (`README.md`); they are not plugin screens and are not captured.
- **Other contributions:** The complete module registration in `src/heinzel_tailscale/__init__.py` declares services, navigation, settings, operations and footer status. It declares no channel, approval, setup or info contribution, and no custom Page/View. Absence of a Page/View alone would not establish absence of feature UI; the footer toggle is affirmative evidence of one.
- **Compatibility and unresolved evidence:** The status implementation branches on whether Core's `ToggleControl` supports `status`, `problem` and `explanation`; older Core receives a detail line instead. The provided source does not establish the installed Core's rendered layout or prove these captures succeed. `web/build.py` is a frontend build helper, but the provided files contain no declared frontend entrypoint or custom screen. Verify the actual rendered pane and accessibility names during capture rather than inventing either.
