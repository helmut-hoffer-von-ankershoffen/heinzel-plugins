## Audience

A person who already uses Tailscale and wants to decide whether to share their authenticated Heinzelmännchen web app privately with another device.

## Outcome

Show the owner turning sharing on, what the plugin's own status command reports, turning sharing off, and the status afterwards. The demo shows local configuration and readiness, not proof that a phone can connect: the remote device still needs Tailscale access and its own browser authentication. Tailscale must already be installed and signed in; the plugin does not perform vendor login or grant HTTPS consent (`README.md`).

## Scenes

1. **Sharing ready — dark UI.** In the genuine footer Tailscale control, turn on **Share over Tailscale** and wait for the **Open** link. On Core 0.9.40 the control offers **Copy link** and **Open**.
2. **Requested sharing — CLI.** `hz tailscale status --json` right after scene 1. It shows the saved request and the mapping to the web app's backend port. It reports `apply-required` with the summary *Turning on…*: a separate CLI process has no web runtime, so it cannot verify the web listener and only the web app finishes the transition (`src/heinzel_tailscale/_service.py`, `Sharing._mapping` comment and `Sharing._state`). This is the plugin's real behaviour and must be shown as is.
3. **Sharing off — light UI.** In the same control, turn sharing off and wait for the switch to read *Off*.
4. **After switching off — CLI.** `hz tailscale status --json` right after scene 3: state `off`, not mapped. The target now shows the configured hz web port, default 8737 (Core `Settings.ui_port`), because without an enabled intent there is no backend port to keep (`Sharing._mapping`: `self.readiness.runtime.port or (old.backend_port if old and old.enabled else self.settings.ui_port)`). The port difference between scenes 2 and 4 is therefore expected, not a sign of a different fixture.

## Capture lifecycle (verified against the capture tool source)

`src/heinzel_plugin_tools/capture.py` (`capture`, about lines 933-1140) runs all scenes of one plan inside ONE temporary HOME (`demo_environment`), starts ONE backend process for that HOME, and runs the scenes strictly in plan order. CLI scenes call `hz` with the same environment (`hz(interpreter, scene["command"], env, work)`, about line 986), so they read the same application and fixture state the UI scenes left behind. The fixture state file `fictional-tailscale.json` lives under that HOME's state directory. Scene order and shared state are therefore established by the capture tool, not merely assumed.

## Fictional fixtures

`docs/screenshot_fixture.py` supplies the fictional `workstation.tail-example.ts.net` node and a loopback-only LocalAPI. It exercises the real plugin mapping logic and holds an unrelated fictional `svc:notes` service. Every fixture process checks on exit that `svc:notes` is unchanged and raises otherwise (`"The fictional unrelated service must remain unchanged"`), and every Serve write is refused if it alters that service. A capture that completes therefore preserved it. The documentation-only LocalAPI credential must never appear in an image or transcript.

## Privacy pitfalls

Normal presentation fictionalization is explicitly limited to verified owning-interpreter paths becoming `/demo-profile/.venv`, and only the verified whole hostname detail in the genuine Doctor row becoming `demo-host`. These mappings change no SDK health status or remaining detail and establish no privacy acceptance. Unknown identities still fail, and an independent reviewer must inspect every image and transcript. A copied sharing link can contain a session `#token` (`README.md`), so the plan never copies or shows the clipboard. Do not capture credentials or a real connected account.

## Acceptance criteria

- The dark image shows the genuine Tailscale control On with Open; the light image shows the same control Off. Both appearances are applied.
- Both CLI transcripts are genuine output of the declared status operation in the shared capture state. Scene 2 shows `apply-required` / *Turning on…* (the CLI cannot see the web listener); scene 4 shows `off` with the default port. Captions must state these limits truthfully and must not claim the CLI proves web readiness.
- No duplicate captures, caption-only differences, forged HTML, invented screens, unknown identities, real credentials, or unreviewed images or transcripts.
- Each image and transcript is reviewed independently, including the Doctor-row and interpreter-path substitutions.

## Source-bound UI surface inventory

- `pyproject.toml`, `[project.entry-points."heinzel.modules"]`: the sole entry point is `tailscale = "heinzel_tailscale"`; its declarations are in `src/heinzel_tailscale/__init__.py`.
- `@module.status(source="status", slots={"footer": True, "sidebar": False})`: Core renders the footer status item and the **Share over Tailscale** toggle (genuine feature UI; no custom Page or View is declared).
- `module.nav(... settings=NavSettings(sections=("tailscale",), group="computer"))` and `module.settings(TailscaleSettings)`: settings contribution (HTTPS port, hidden intent), not needed for this story.
- Private operations `status`, `enable`, `disable`, exposed through CLI and authenticated API/MCP; the footer toggle invokes enable and disable.
- Tailscale app, login, certificate consent and OS permissions are external provider UI, not plugin screens (`README.md`).
