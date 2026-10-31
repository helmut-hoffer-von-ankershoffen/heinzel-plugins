# Show the useful feature, then publish the approved gallery

One command defines the plugin's screenshot story, captures its real UI and CLI with fictional data, asks an
independent agent to check every image and transcript, and publishes the approved gallery:

```sh
make screenshots NAME=clock OPEN=1
make screenshots-check NAME=clock
```

The source-analysis agent reads a bounded copy of the owning source and documentation before the plugin runs.
Its story explains the audience, useful outcome, distinct scenes, fictional fixtures, privacy pitfalls and acceptance
criteria. The editable plan is `docs/screenshots.toml`; `docs/SCREENSHOT_STORY.md` and
`docs/screenshot-definition.json` record what was analyzed. Source, fixture or plan changes require renewed analysis.
An existing plan is preserved when it already tells the useful feature story.

The normal command runs both agents through the local Codex CLI. Install and sign in to Codex first. Neither
agent can edit source or approve an interface that it has not inspected. Agent logs and arbitrary provider errors
are kept out of command output. If an agent cannot finish, the command stops with an actionable error; it never
silently substitutes help screenshots or publishes unreviewed images.

## Define, capture, review

Humans and agents use the same command:

```sh
hz-plugin screenshots clock --plan --json       # define or refresh the source-based story only
hz-plugin screenshots clock --draft --open     # capture privately; ask another agent to review later
hz-plugin screenshots clock --json             # define if needed, capture, independently review, publish
hz-plugin screenshots clock --check --json      # validate published source/plan/image/review hashes offline
```

`--generate` is an alias for `--plan`. `--init` writes an editable starter plan without executing the plugin; it
still needs source analysis and image review before publication. Inside a standalone plugin, omit the name.
`--headed` shows the capture browser. `--open` opens the local contact sheet, including for private drafts.
`CORE=/path/to/core.whl` selects a candidate SDK through the owning environment's ordinary setup contract.

For an existing governed project that already has a prepared environment, use:

```sh
hz-plugin screenshots --python /absolute/path/to/.venv/bin/python --draft --open
```

The interpreter must contain the owning distribution at its declared version and a compatible Heinzel SDK.
This skips environment setup; it does not change the project's lock format, skip source analysis, or bypass review.
Only the owning plugin's frontend build runs when it declares one. This workflow never runs core's test suite.

A successful JSON result contains absolute `preview`, `plan` and `manifest` paths, the screenshot metadata,
`fresh: true`, and the approving reviewer. A private draft instead returns `review_required: true` and its draft path.
Progress goes to stderr; stdout remains JSON. The first capture installs pinned browser tools as needed.
Linux requires Chromium's system libraries; CI installs them in its dedicated screenshot job.

## Plan real UI and CLI scenes

Keep three to eight scenes, with at least two different useful UI views and one CLI result. Use a feature's
populated page, a detail or expanded pane, and its useful terminal output. A CLI-only plugin can show useful command
results in the native app terminal. A theme needs applied light and dark views. Settings and installed-plugin cards
can supplement a story, but cannot replace a feature that the plugin actually provides.

```toml
format = 1
browser_time = "2026-11-02T10:00:00+01:00"

[[scenes]]
name = "world-clock"
surface = "ui"
route = "/?panel=clock:world-clock"
caption = "World Clock with fictional team locations"
reduced_motion = "no-preference"
steps = [
  {action="wait", role="region", name="World clock"},
  {action="wait-webgl"},
]

[[scenes]]
name = "clock-detail"
surface = "ui"
route = "/?panel=clock:world-clock"
caption = "Clock details for the fictional team, dark appearance"
appearance = "dark"
reduced_motion = "no-preference"
steps = [{action="wait", role="region", name="World clock"}, {action="wait-webgl"}]
focus = {role="region", name="World clock"}

[[scenes]]
name = "cli"
surface = "cli"
command = ["clock"]
caption = "The same fictional team's local times in the CLI"
```

Routes stay inside the local app, without fragments. Commands are arrays of `hz` arguments, never shell strings.
The plan does not accept browser source, raw selectors or `evaluate` actions. Steps support:

- `click` or `hover`: accessible `role` and exact `name`, or a bounded `name_regex`; optional `within_role` scopes it.
- `fill`: exact `label` and `value`.
- `press`: a keyboard `key`.
- `wait`: exact `text`, or `role` and `name`.
- `terminal`: `command = ["harbor", "hello"]`, showing actual output in the app's terminal.
- `wait-webgl`: wait for a painted canvas rather than capturing an empty globe.

A `click`, `hover` or `wait` can set `optional = true` for an unrelated dismissible card; optional waits are bounded
to one second. Required feature waits still fail. A `focus` with accessible `role` and `name` or `name_regex` crops a
useful detail view without replacing or inventing UI. Optional focus `padding` (16–160 pixels, default 40)
keeps a bounded margin around the native element without imposing a wide minimum canvas. `viewport = {width=390, height=844}` adds a phone view.
`timeout_ms` defaults to 15000 and permits 1000–30000. Motion defaults to `reduce`; animated canvases may need
`no-preference`. An ISO8601 `browser_time` fixes browser wall-clock dates while animation frames continue running.
Set `theme = "harbor"` to apply an installed owning theme.

Wait for **every surface promised by the caption**, including lazily mounted sidebar tickers, footer controls and
secondary panes. A ready Today widget or main region does not prove those contributions have loaded. Require their
actual visible accessible controls before saving; then move the pointer to a neutral heading or region so hover
underlines and temporary tooltips are not mistaken for feature state. For a WebGL globe, explicitly select
`reduced_motion = "no-preference"` and `wait-webgl`; the default reduced-motion flat map is a different valid view
and needs its own accurate caption.

## Use deterministic fictional fixtures

Optional `bootstrap = "docs/screenshot_fixture.py"` names an owning, source-bound Python fixture. It can seed the
isolated profile or run the real installed kernel with public plugin declarations and local demonstration adapters.
Use names such as Mira Example, `mira@example.com`, `demo-workstation`, and fictional example domains. Show populated
weather, tracker, calendar or document results from local fixtures when a real account is unnecessary. Captions must
identify demonstration data accurately. Never fabricate a product page or edit a screenshot to simulate a feature.

The capture process uses fresh HOME, XDG, application and vendor state, an environment credential backend, a neutral
shell prompt and a fresh browser. It does not inherit tokens or normal configuration. Browser requests stay on the
isolated app's origin. Fixture commands execute with normal operating-system permissions: inspect the fixture before
running it and use local adapters instead of real accounts or seeding commands that create external resources.
No discovered public plugin executes during catalog generation.

Authentication links and session credentials presented by the running app are redacted before **every** screenshot
save, including failure diagnostics. Other recognizable credentials, private home paths or host identity prevent an
image save. The independent review remains mandatory; automated pattern checks alone cannot approve a gallery.

## Independent privacy and product review

Captures initially remain under `.preview/screenshots/draft/`. That folder contains every PNG, text transcript,
a contact sheet, `review-input.json`, `review.schema.json`, and `REVIEW.md`. The review bundle binds source and SDK
provenance, the source-analysis definition, captions and every image/transcript SHA-256.

A reviewer must open every PNG and read all transcripts and captions. They reject credentials, authentication URLs,
private paths/hostnames, personal account data, unreadable images, inaccurate captions, or scenes that do not show a
useful feature. They also verify the two-UI-plus-CLI requirement and theme appearances. Approval identifies the
reviewing agent and names every image; an incomplete, stale or rejected receipt cannot publish.

An independently reviewed private draft can be published with:

```sh
hz-plugin screenshots clock --review-receipt /absolute/path/to/privacy-review.json --json
```

A source-analysis agent working in another chat can record its actual source review with
`planning.record_definition(root, read_plan(root), story, reviewer="the reviewing agent")` before capture.
This records work the agent actually performed; authors must not generate approval receipts merely to satisfy a gate.
CI uses an explicitly labeled synthetic review fixture only for its unknown-plugin test; production has no automatic
approval switch.

Generated transcripts use LF line endings, no trailing whitespace and exactly one final newline before hashes are
computed. Contact sheets are canonical too. Commit whitespace hooks therefore leave the reviewed bytes unchanged.
For an older private draft, `privacy.canonicalize_draft(folder)` preserves every PNG, canonicalizes text, rebuilds
its bundle hash and deletes stale review receipts. Any changed transcript requires a new independent review.
Never normalize a public gallery and keep its old review hash.

Publication rechecks all hashes after review and stages the complete gallery before replacing the old one.
Symlinked inputs or output paths are refused. Approved images, transcripts, contact sheet and review manifest live in
`docs/assets/screenshots/`; catalog metadata and the owning README's generated screenshot block update together.
The README shows UI captures immediately and puts CLI images in an expandable section. Text outside
`<!-- screenshots:start -->` / `<!-- screenshots:end -->` stays author-owned.

## Keep the gallery current

Owning checks and CI verify captures offline once a plan exists. Source, frontend, packaged assets, dependency inputs,
fixture, ordinary README prose, story or plan changes invalidate the corresponding definition or capture.
The generated README media block is excluded from source hashing, so publication does not make itself stale.
Changed images or transcripts invalidate their exact review. Run capture and independent review again, then commit
all owning gallery files. Failed capture or rejected review preserves the existing public gallery.

The toolkit's dedicated CI journey creates a new unknown plugin, captures real Today and terminal output against an
installed released SDK, verifies explicit review and README publication, detects staleness, fails a scene, and recovers.
It also proves authentication presentation is removed before both success and failure image saves. Ordinary offline
checks neither import a plugin nor start a browser.
