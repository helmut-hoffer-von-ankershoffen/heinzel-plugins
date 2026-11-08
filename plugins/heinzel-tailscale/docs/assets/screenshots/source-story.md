## Audience

A Heinzelmännchen user deciding whether private access to their authenticated web app is worth setting up, and whether they can understand and reverse that choice.

## Outcome

Show the real sharing control turning on, the saved request inspected from the CLI, and the same control turning off. The story demonstrates an opt-in local sharing workflow; it does not claim that a remote phone can connect. Tailscale must already be installed and signed in, and a remote browser still needs network access and authentication (`README.md`).

## Scenes

1. **Ready, dark:** Open the footer’s Tailscale control and turn sharing on. Capture the genuine control once it exposes **Open**, with the fictional address and the switch’s resulting state. The control distinguishes the requested choice from verified readiness (`src/heinzel_tailscale/__init__.py`, `sharing`; `src/heinzel_tailscale/_readiness.py`, `SharingReadiness.verifies`).
2. **Request, CLI:** Run `hz tailscale status --json` after enabling. Show the actual returned request, mapping and explanation; a separate CLI cannot verify the authenticated web listener and must not be captioned as independently confirming browser readiness (`src/heinzel_tailscale/_service.py`, `Sharing._state`; `README.md`).
3. **Off, light:** Use the same real footer control to turn sharing off. This is a meaningful changed state of the feature, not a duplicate with a different caption. The operation removes only its still-matching owned mapping and plugin-added origin permission (`src/heinzel_tailscale/__init__.py`, `disable`; `src/heinzel_tailscale/_service.py`, `SharingActions.disable`).
4. **Off, CLI:** Run the same read-only status command after switching off, showing the changed result. These two CLI captures preserve the existing useful plan and illustrate two state cases; the plugin actually declares three operations, so there is no basis to invent parameter cases for a single operation.

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap and isolated profile. Its fictional node is `workstation.tail-example.ts.net`; it emulates vendor discovery and a loopback LocalAPI while exercising the real sharing adapter. Its unrelated fictional notes service is checked for preservation. Run the bootstrap only as part of an explicitly requested capture. Scene ordering and shared isolated state are essential: on → status → off → status. The supplied sources do not establish that capture orchestration preserves that state, so verify it during capture and reject the sequence if it does not.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited as follows: verified owning-interpreter paths become `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becomes `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and independent review must inspect every image and transcript.

Do not expose session fragments, sign-in links, real hostnames, account identities, LocalAPI credentials, paths, or unrelated personal data. **Copy URL** can include a session token and must be treated as a password (`README.md`). The fixture’s documentation-only password is not a license to show credentials. Review the complete frame and transcript, including Doctor and footer content; dismissing Doctor in the planned scenes does not replace review.

## Acceptance criteria

- Capture genuine Core-rendered feature controls in both applied dark and light appearances, showing distinct on and off states; retain the useful CLI result after each state transition.
- The ready scene must actually reach the **Open** link; do not substitute a pending or error state or claim remote access was tested. The CLI scene must preserve the actual status and message, including any `apply-required` result.
- Use the existing fixture and real app/terminal output. No fabricated HTML, terminal output presented as feature UI, duplicate captures, or caption-only state changes.
- Confirm the unrelated fictional service survives both transactions, and inspect every image and transcript independently for privacy before publication.
- The plan below preserves `docs/screenshots.toml`. It has been checked against the supplied format and declarations by inspection; capture behavior and runtime validation remain unverified because code execution was prohibited.

## Source-bound UI surface inventory

- `pyproject.toml`, `[project.entry-points."heinzel.modules"]`: the sole declared plugin entry point is `tailscale = "heinzel_tailscale"`. Its actual declaration is `module = Module(...)` in `src/heinzel_tailscale/__init__.py`.
- `src/heinzel_tailscale/__init__.py`, `module.nav(..., settings=NavSettings(sections=("tailscale",), group="computer"))` and `module.settings(TailscaleSettings)`: Core can render a settings contribution. `src/heinzel_tailscale/_models.py`, `TailscaleSettings`, declares the HTTPS sharing port and a hidden, private intent. The supplied sources do not establish the nav panel’s actual route, so the plan does not invent one.
- `src/heinzel_tailscale/__init__.py`, `@module.status(source="status", slots={"footer": True, "sidebar": False})` and `sharing`: a genuine Core-rendered footer feature control supplies the switch, status/problem, explanation and ready URL. The README also describes this control in Settings. Older Core versions may render only the short detail line; the exact Details presentation depends on the installed Core.
- The private `status`, `enable` and `disable` operations are declared in `src/heinzel_tailscale/__init__.py`; Core exposes CLI and authenticated API/stdio MCP access as documented in `README.md`. The supplied plugin sources do not prove a separate generic operation screen or approval flow. No channel, setup, info, Page or View contribution is declared in that module. Absence of a Page or View does not negate the footer feature UI.
- The Tailscale application and its login/HTTPS consent are external provider UI, not plugin screens (`README.md`). `TailscaleCli` invokes vendor commands internally (`src/heinzel_tailscale/_cli.py`); those commands are distinct from the `hz tailscale` CLI result in this story. The supplied source establishes no further plugin-owned frontend entry point; `web/build.py` is build tooling, not a declared product screen.
