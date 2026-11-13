## Audience

Someone who wants to reach their authenticated Heinzel web app privately from another device and wants to understand both the convenience and the limits before installing the plugin.

## Outcome

Show the owner explicitly turning sharing on, inspecting the saved request, and turning it off again. The ready state demonstrates a verified local configuration, not proof that a phone can connect: the remote device still needs Tailscale access and its own browser authentication (`README.md`; `src/heinzel_tailscale/_readiness.py`, `SharingReadiness.verifies`).

## Scenes

1. **Ready, dark:** In the genuine footer Tailscale panel, turn on **Share over Tailscale** and wait for **Open**. The fictional address and the switch make the result tangible; **Copy URL** and **Open** are available when ready. The fixture simulates Tailscale, so this is not evidence of a real tailnet connection.
2. **Request, CLI:** Show `hz tailscale status --json` after the UI action. The result exposes the saved request and mapping for the fictional node. A separate CLI process cannot itself verify an arbitrary web listener, so its readiness must be reported exactly as returned, not made to match the UI by editing output.
3. **Off, light:** Return to the same real panel and turn sharing off. This is a meaningful second state of the feature: the user's explicit choice and the removal outcome. The plugin removes only its still-matching owned mapping and its added origin permission.
4. **After off, CLI:** Show `hz tailscale status --json` again, preserving the actual result and making the change in request and mapping inspectable. These two CLI captures have the same command but different transaction states; retain both only if the output demonstrates that difference.

Capture the scenes in plan order with shared isolated fixture state. If the capture runner resets state between scenes or the ready/off transitions do not appear as described, stop and resolve the evidence rather than relabeling a capture. Light and dark must actually be applied and visible.

## Fictional fixtures

`docs/screenshot_fixture.py` supplies the existing bootstrap: a loopback-only fictional LocalAPI, a simulated signed-in node `workstation.tail-example.ts.net`, and a separate fictional notes service whose configuration must remain unchanged. It uses the real plugin operations and conditional Serve store against that fixture. Do not create a substitute fixture or present the simulated node as a real account.

Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail; independent review must inspect every image and transcript.

## Privacy pitfalls

A copied sharing link can contain a session token and must be treated like a password (`README.md`). Do not capture or expose tokens, real hostnames, usernames, account data, local API credentials, private paths, or unrelated real services. The fixture's documentation-only credential is not an invitation to expose credentials. Review the full image, cropped area, terminal transcript, and any generated metadata independently; reject unknown identities and accidental real data.

## Source-bound UI surface inventory

- `pyproject.toml`, `[project.entry-points."heinzel.modules"]`: the sole declared module entrypoint is `tailscale = "heinzel_tailscale"`. `src/heinzel_tailscale/__init__.py` declares the actual module and its contributions.
- **Core-rendered feature UI:** `module.status(source="status", slots={"footer": True, "sidebar": False})` declares a footer status item with a `ToggleControl` named **Share over Tailscale**, `enable` and `disable` operations, a ready-only URL, and status/problem/explanation details where supported. This is a real feature surface, not a terminal substitute. The same declaration explicitly disables the sidebar slot. The README describes the footer sharing icon and Settings control.
- **Core settings UI:** `module.nav(... settings=NavSettings(sections=("tailscale",), group="computer"))` and `module.settings(TailscaleSettings)` contribute settings navigation. `src/heinzel_tailscale/_models.py`, `TailscaleSettings`, declares the HTTPS sharing port and hides the private intent. The declaration does not establish a specific panel route here; the plan uses the documented root and footer rather than guessing one.
- **Operations and other Core surfaces:** `status`, `enable`, and `disable` are private operations; the latter two are mutating. Their declarations support CLI, authenticated API and stdio MCP exposure as described in `README.md`; the footer binds the operations to its control. No channel, approval, setup, info, Page, or View contribution is declared in the module. Absence of Page/View alone would not rule out Core-rendered UI, as the footer and settings contributions demonstrate.
- **External provider:** Tailscale installation, login, HTTPS consent, OS permissions and its own configuration are external prerequisites, not invented plugin screens (`README.md`).
- **Terminal:** `hz tailscale status --json`, `enable --json`, and `disable --json` are documented CLI operations. The native CLI status result is useful supporting evidence, not a feature UI scene. The fixture intercepts vendor discovery and uses a local HTTP endpoint; it does not show a genuine external Tailscale UI.
- **Compatibility and unresolved evidence:** `src/heinzel_tailscale/__init__.py` checks whether the installed Core's `ToggleControl` has `status`, `problem`, and `explanation`; older Core versions receive a short detail line instead. Actual rendered labels, applied themes, focus crops, scene-to-scene state persistence, and CLI output require capture-time verification. `web/build.py` is a build helper, not a declared plugin UI entrypoint; no frontend assets or route declarations are supplied here.

## Acceptance criteria

- Four distinct captures use the existing fixture and genuine application/terminal surfaces; ready and off visibly differ, as do the two status results. No duplicate images, caption-only changes, forged HTML, or terminal output presented as feature UI.
- The ready scene reaches the actual ready control and the off scene shows the completed off state. Neither a requested toggle nor a simulated response alone is presented as verified remote access.
- Both applied appearances are visible; captions identify demo data. The unrelated fictional service remains preserved.
- No unverified identity or secret appears. Apply only the two specified presentation mappings, without changing SDK health or other detail, and obtain independent image and transcript review.
- Validate the TOML against the capture tool and inspect its rendered results before publication. This plan was checked against the supplied format and declarations by inspection; no code, capture, or runtime validation was executed.
