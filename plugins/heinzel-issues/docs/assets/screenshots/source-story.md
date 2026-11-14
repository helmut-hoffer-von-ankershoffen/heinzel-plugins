## Audience
People who use Heinzel and want to report a problem or request something without leaving the app, then follow it to the release that shipped it. Maintainers also need to know that the built-in tracker is a Beads database on this computer that they can write to; the plugin is optional and off until a tracker is set up (`README.md`, `[tool.heinzel.catalog]` in `pyproject.toml`).

## Outcome
The tracker is usable from within the app, with no terminal step: set it up, send a report, read the list with plain states, open one report for what was sent and its history, and see open reports on Today. The gallery shows the real plugin view and Core's Today with fictional data only. It must not claim that anything was sent: the demonstration tracker refuses sending.

## The UI flows in the source
All of this is one view, `src/heinzel_issues/views/index.js`, at the route `/?panel=issues:requests` (`ROUTE` in `_service.py`), reached from the sidebar entry Issues (`module.nav`, `module.action`, `module.view(name="requests", source="list")` in `__init__.py`).

1. **Setup form.** While `data.ready` is false the view renders the form "Set up issue tracking": the status line "Issue tracking is not set up." (or the tracker's own problem text), the required field "Tracker folder", and under "More options" the fields "More labels" and "Release clones". The button "Set up issue tracking" runs the view action `connect` (operation `connect`), which checks that the folder holds a Beads database and that it answers before anything is saved, then works without a restart. The form says "Checking the folder…", then "Issue tracking is set up." or the reason nothing was saved.
2. **Submit with confirm.** When ready, the composer "Report or request" has a text area ("What happened, or what would you like?"), an optional chooser "Screenshot or file (optional)" for a PNG, JPEG or text file up to 2 MiB, a line that says how it is stored ("Sent to the tracker under your login name …, with the labels …"), and the button Send. Send runs the view action `send` (operation `submit`, declared `read_only=False`, `private=True`). Core shows the call and asks before it runs; that confirmation is Core-rendered, not plugin UI. Cancelling keeps the typed text ("Not sent; your text is still here."); success says "Received. You will see here when someone is on it." The chooser appears only when Core reports the SDK feature `form-long-values`.
3. **List with states.** The list "Your reports and requests" has one row per report: its title, and its state as a mark and a word, never colour alone: ○ Received, ◐ Being worked on, ✓ Done, or ✓ Released in 0.9.27 on 7 Nov 2026 once a release is found. An empty tracker shows "Nothing reported yet."
4. **Detail and history.** A row is a button; selecting it expands the text sent after the title, "Sent with:" and the attachment names, and the ordered list "History": Sent, Being worked on, Done, Released in, each with its day.
5. **Today cards.** `@module.widget(source="list")` puts a list card "Your reports and requests" on Core's Today at `/` with up to eight reports that are not done, each with its state and a link to the Issues page. It is absent while tracking is off or everything is done.

Beyond the app: the CLI commands `hz issues list`, `submit`, `show` and `connect`, the prompted `hz setup issues`, a Doctor check `tracker`, and a five-minute job that emits Core notices on a state change or release. These are Core or terminal surfaces, not further plugin pages. No external provider UI is declared; Beads is reached through a local command and releases through local git clones.

## Scenes
1. **issues-page (UI, light):** flows 2 and 3 at rest. Three fictional reports, one per state, the done one as "Released in 0.9.27 on 7 Nov 2026", above the composer with its storage line and Send. The caption's "a form to send another" is accurate for the form being present; it is not a sent report.
2. **report-history (UI, light):** flow 4. The fictional weather report is opened: its text, "Sent with: today-rain.png", and the history Sent 4 Nov 2026, Being worked on 4 Nov 2026, Done 5 Nov 2026, Released in 0.9.27 7 Nov 2026. A meaningful expanded state of the same real view.
3. **today-open-reports (UI, dark):** flow 5. Core's Today with the two open fictional reports; the released one is absent.
4. **cli-list (CLI):** `hz issues list` as a table with the columns Report or request, Status and Sent, for the same three reports. A real CLI result, not a substitute for the UI.

What the plan does not capture: the setup form (flow 1) and Core's confirmation or a successful send (the rest of flow 2). The fixture forces a ready tracker and its `submit` raises "Sending is off in this demonstration.", so neither can be shown by this plan and no caption may imply them. Showing them needs further scenes with a fixture state that is not set up and a plan step that presses Send; that is a change to the plan and needs a new definition.

## Fictional fixtures
`docs/screenshot_fixture.py` replaces the built-in tracker with one in memory holding three fictional tasks (demo-1 to demo-3), one fictional attachment name with no file behind it, and a temporary local git clone with empty commits and the tags v0.9.26 and v0.9.27, so that "Fixed in #7" resolves to 0.9.27 on 7 Nov 2026. It sets the tracker and the release clone through environment settings and then runs the real app. No Beads database is read or written and nothing is sent anywhere. Browser time is fixed at 8 Nov 2026.

## Privacy pitfalls
- The composer prints the login name of whoever runs the capture (`reporter()` in `_beads.py` reads the operating system's login name) together with the label `heinzel-issues`. The image is acceptable only if that name is the capture profile's fictional one; a real login name on scenes 1 or 2 is a rejection.
- The release clone lives in a temporary folder whose path is in the settings. It must not appear in any image or transcript; the list and the table do not print it, the JSON output would.
- The setup form's "Tracker folder" is prefilled from settings and would show a real path if it were ever captured from a real profile.
- Report titles, body and the attachment name must be exactly the fixture's; any text from a real tracker, a real bead id or a pull request of a real repository is a rejection. The view and the table do not print tracker ids.
- Core chrome around the view (sidebar, account name, version, Doctor card, footer, notices, chat) comes from the capture profile; check it for real names, host names, paths, e-mail addresses and tokens. The toolkit's own presentation mapping is limited to the owning interpreter path shown as `/demo-profile/.venv` and the Doctor hostname shown as `demo-host`; neither is a privacy acceptance.

## Acceptance criteria
- Four distinct captures from the real app and CLI through the fixture; no forged HTML, duplicates or caption-only variants. Scenes 1 and 2 are genuine feature UI states, scene 3 is a Core feature surface fed by the plugin, scene 4 is identified as CLI.
- Scene 1 shows all three rows with mark and word, and the composer; scene 2 shows the body text, "Sent with: today-rain.png" and all four history steps with dates; scene 3 shows exactly the two open reports in an applied dark appearance; scene 4 lists the same three with the same states.
- Light and dark are actually applied. Text is readable, nothing clipped, the state marks are visible.
- Do not describe the file chooser as shown unless it is in the image; it depends on the captured Core.
- Captions say the data is fictional and claim nothing about setup, confirmation or a successful send.
- An independent reviewer opens every image and reads every transcript for privacy and accuracy before publication.

This analysis read the staged source, README, plan and fixture; it ran no plugin code and captured nothing.
