# Screenshot authoring: a hand-edited definition, deterministic capture, review in the PR

Taking screenshots needs no AI. Each plugin's checked-in `docs/screenshot-definition.json` is the whole plan: its
scenes, their captions, an optional fixture bootstrap and a fixed browser clock. Edit it like any other file.
Capture runs Playwright against the plugin's fixture scenes with fictional data only and never plans, and no agent
approves anything: deterministic guards refuse unsafe text, and the pull request diff shows the images for the
normal review.

```sh
hz-plugin screenshots clock --init          # write a starter definition (only when there is none)
make screenshots NAME=clock OPEN=1         # capture and publish the gallery, catalog metadata and README block
hz-plugin screenshots clock --draft --open # capture privately into .preview/screenshots/draft, publish nothing
make screenshots-check NAME=clock          # offline freshness: no browser, plugin run, build or agent
hz-plugin screenshots-check --all --json   # every gallery; stale ones with the exact command that regenerates each
```

Inside a standalone plugin, omit the name. `--headed` shows the capture browser. `--open` opens the local contact
sheet. `CORE=/path/to/core.whl` selects a candidate SDK through the owning environment's ordinary setup contract.
For an existing governed project with a prepared environment, `--python /absolute/path/to/.venv/bin/python` uses
that interpreter as it is; it must contain the owning distribution at its declared version and a compatible SDK.
Only the owning plugin's frontend build runs when it declares one. This workflow never runs core's test suite.

A successful JSON result contains absolute `preview`, `plan` and `manifest` paths, the screenshot metadata and
`fresh: true`. Progress goes to stderr; stdout remains JSON. The first capture installs the pinned browser once; if
that fails, the error names the exact install command and then the capture command to run. Linux requires
Chromium's system libraries; CI installs them in its dedicated screenshot job.

## Plan real UI and CLI scenes

Keep three to eight scenes, with at least two genuine, useful feature UI scenes and one CLI result. Use a feature's
populated page, a detail or expanded pane, and its useful terminal output. Different meaningful states of the same
actual view or flow qualify; distinct routes are not required. Duplicate captures, caption-only changes, terminal
output presented as feature UI and forged HTML do not qualify. A CLI-only plugin can show useful command
results in the native app terminal. A theme needs applied light and dark views. Settings and installed-plugin cards
can supplement a story, but cannot replace a feature that the plugin actually provides.

```json
{
  "format": 1,
  "browser_time": "2026-11-02T10:00:00+01:00",
  "bootstrap": "docs/screenshot_fixture.py",
  "scenes": [
    {
      "name": "world-clock",
      "surface": "ui",
      "route": "/?panel=clock:world-clock",
      "caption": "World Clock with fictional team locations",
      "reduced_motion": "no-preference",
      "steps": [{"action": "wait", "role": "region", "name": "World clock"}, {"action": "wait-webgl"}]
    },
    {
      "name": "clock-detail",
      "surface": "ui",
      "route": "/?panel=clock:world-clock",
      "caption": "Clock details for the fictional team, dark appearance",
      "appearance": "dark",
      "reduced_motion": "no-preference",
      "steps": [{"action": "wait", "role": "region", "name": "World clock"}, {"action": "wait-webgl"}],
      "focus": {"role": "region", "name": "World clock"}
    },
    {"name": "cli", "surface": "cli", "command": ["clock"], "caption": "The same fictional team's local times in the CLI"}
  ]
}
```

Routes stay inside the local app, without fragments. Commands are arrays of `hz` arguments, never shell strings.
The definition does not accept browser source, raw selectors or `evaluate` actions. Steps support:

- `click` or `hover`: accessible `role` and exact `name`, or a bounded `name_regex`; optional `within_role` scopes it.
- `fill`: exact `label` and `value`.
- `press`: a keyboard `key`.
- `wait`: exact `text`, or `role` and `name`.
- `terminal`: `"command": ["harbor", "hello"]`, showing actual output in the app's terminal.
- `wait-webgl`: wait for a painted canvas rather than capturing an empty globe.

A `click`, `hover` or `wait` can set `"optional": true` for an unrelated dismissible card; optional waits are bounded
to one second. Required feature waits still fail. A `focus` with accessible `role` and `name` or `name_regex` crops a
useful detail view without replacing or inventing UI. Optional focus `padding` (16–160 pixels, default 40)
keeps a bounded margin around the native element without imposing a wide minimum canvas. `"viewport": {"width": 390, "height": 844}` adds a phone view.
`timeout_ms` defaults to 15000 and permits 1000–30000. Motion defaults to `reduce`; animated canvases may need
`no-preference`. An ISO8601 `browser_time` fixes browser wall-clock dates while animation frames continue running.
Set `"theme": "harbor"` to apply an installed owning theme.
Capture dismisses an empty first-Heinzel pane through the app's close control. A scene can open chat from the toolbar.

Wait for **every surface promised by the caption**, including lazily mounted sidebar tickers, footer controls and
secondary panes. A ready Today widget or main region does not prove those contributions have loaded. Require their
actual visible accessible controls before saving; then move the pointer to a neutral heading or region so hover
underlines and temporary tooltips are not mistaken for feature state. For a WebGL globe, explicitly select
`"reduced_motion": "no-preference"` and `wait-webgl`; the default reduced-motion flat map is a different valid view
and needs its own accurate caption.

## Use deterministic fictional fixtures

Optional `"bootstrap": "docs/screenshot_fixture.py"` names an owning, source-bound Python fixture. It can seed the
isolated profile or run the real installed kernel with public plugin declarations and local demonstration adapters.
Use names such as Mira Example, `mira@example.com`, `demo-workstation`, and fictional example domains. Show populated
weather, tracker, calendar or document results from local fixtures when a real account is unnecessary. Captions must
identify demonstration data accurately. Never fabricate a product page or edit a screenshot to simulate a feature.

The app and scene subprocesses use fresh HOME, XDG, application and vendor state, an environment credential backend
and a neutral shell prompt. They receive a limited environment that excludes the caller's credentials. The fresh
browser keeps requests on the isolated app's origin. Preparing the owning plugin can execute its build tooling with
the caller's environment. Treat the scene definition, fixture and owning plugin as executable project content. Review
them before capture. An application command can still write files or contact services with the account's operating
system permissions. Use local adapters for demonstrations and disposable operating-system isolation when evaluating
untrusted projects.
No discovered public plugin executes during catalog generation.

Authentication links and session credentials presented by the running app are redacted before **every** screenshot
save, including failure diagnostics. Other recognizable credentials, private home paths or host identity prevent an
image save.

## Deterministic guards instead of an agent review

Before every image save, the text the scene shows is scanned: the DOM text, every input and textarea value, the
document title and the URL. CLI transcripts and every caption are scanned the same way, at capture, at publication
and again by the offline check. A match refuses the capture and names the kind of finding, never the value:

- credentials: token query parameters, bearer tokens, GitHub, GitLab, OpenAI/Anthropic, Stripe, Slack, AWS and
  Google keys, JWTs, private key blocks and `api_key=`/`password=`-style assignments (in the spirit of the
  repository's gitleaks rules, which also scan every committed transcript);
- personal identity: email addresses outside the example domains, home and temporary directory paths, this
  machine's hostname and home directory;
- private networks: hostnames under `.local`, `.lan`, `.internal`, `.corp`, `.home` or `.ts.net` unless a label is
  fictional (contains `example`, or is `demo-host`/`demo-workstation`), and IPv4 addresses other than loopback and
  the documentation ranges 192.0.2.0/24, 198.51.100.0/24 and 203.0.113.0/24;
- the configured confidential terms, matched exactly as the repository's confidential-terms hook matches them.

Captions come only from the definition, so the README, catalog metadata and contact sheet say exactly what the
definition says. The images and transcripts are committed: the pull request diff shows them, and the normal PR
review looks at them like any other change.

## Publication

Publication stages the complete gallery before replacing the old one. Symlinked inputs or output paths are refused.
Images, transcripts, the contact sheet and `capture.json` live in `docs/assets/screenshots/`; catalog metadata and
the owning README's generated screenshot block update together. The README shows UI captures immediately and puts
CLI images in an expandable section. Text outside `<!-- screenshots:start -->` / `<!-- screenshots:end -->` stays
author-owned. Generated transcripts use LF line endings, no trailing whitespace and exactly one final newline, so
the commit whitespace hooks leave them unchanged.

`capture.json` (format 2) records the plugin, the SDK version the capture used, the digest of the UI inputs and the
SHA-256 of every image and transcript.

## Keep the gallery current

The freshness digest covers only what a capture renders: the definition, its fixture bootstrap, the plugin's theme
declarations and its web, static and view assets (scripts, styles, markup, images and fonts under `src/`, `web/`,
`assets/`, `static/`, `templates/` and `resources/`, as git tracks them; built output and tests are left out).
Python logic, metadata, locks, documentation and README prose are no capture input, so changing them never makes
the gallery stale. The owning checks and the `owning-plugin-checks` hook verify freshness offline; a stale gallery
fails with the exact command to run (`make screenshots NAME=<plugin>`), never by starting an agent or a browser.
In a Heinzel worktree `sm check` regenerates a stale gallery and `sm ship` takes it into the shipped commit.

The narrow local digest cannot see displayed text that comes from plugin Python, metadata or Core. CI therefore
re-captures the gallery of every plugin a pull request changes against its newest compatible released Core
(`make screenshots-render-check NAME=<plugin>`) and fails when any scene renders different text than its committed
transcript, naming `make screenshots NAME=<plugin>`. The job reports its result while the refreshed galleries are
being verified on hosted Linux. Image differences are listed:
two captures differ in antialiasing and cursor pixels even on one machine, and fonts differ between operating
systems (`--strict-images` makes them gate). Clock readings (hh:mm) are not compared, since fixtures may anchor
their data on the real time; set `browser_time` to fix the browser's clock.

The zero-secret CI render check performs the public-pattern checks and the real rendering comparison; it does
not approve confidential terms or publish images. Full local capture and verification require configured private
terms and scan on the trusted host before publication. Advanced `--python` diagnostics without terms warn once.

The toolkit's dedicated CI journey creates a new unknown plugin, captures real Today and terminal output against an
installed released SDK, publishes, detects staleness, fails a scene, and recovers. It also proves authentication
presentation is removed before both success and failure image saves. Ordinary offline checks neither import a
plugin nor start a browser.

## Fictional owning-interpreter paths

Normal setup attests the selected owning Python's actual prefix and executable against this project's real,
owned, non-writable-by-others `.venv`. A virtual-environment root or bin-directory alias, foreign-environment
interpreter alias, mismatched identity or changed filesystem evidence refuses capture. Verified Darwin system
`/var` and `/tmp` aliases are accepted only for the same canonical environment; the resolved base Python never
defines the redaction prefix.

Before each image save, that verified prefix alone is replaced in rendered text by `/demo-profile/.venv`.
The UI transcript uses the same rendered text. This is presentation redaction, not a changed SDK report: every
Doctor row, status, error and remaining detail survives. Exact directory boundaries are required; lookalikes,
dot segments, repeated separators, percent-encoded suffixes and unknown private paths are left unchanged for
the ordinary scan. URL/email-bearing text nodes are also left unchanged, including whitespace in query values.
This deliberately narrow matching rule does not normalize paths or establish a general privacy guarantee. Disclose the fictionalized paths in the captions.

External prepared `--python` mode keeps its prior behavior and receives no new owning-prefix redaction authority.
No free-form prefix allowlist or fixture hook is available. Normal setup also compares the selected owning Python's reported hostname with the controller's hostname;
changed evidence or an invalid/mismatched hostname refuses capture. On the genuine `/doctor` route only,
presentation can replace the unique `system.doctor` / `hostname` row's whole sole detail text node with
`demo-host`. The expected five-cell table structure must be unambiguous and the complete detail must exactly
match that verified hostname. No labels, status cells, attributes, inputs, URLs, emails or paths are rewritten.
A missing/duplicate/ambiguous row or mismatched detail refuses capture unchanged. Even a hostname such as `UP`
can change only that detail, never a health status. The advanced external `--python` path gains no hostname
redaction authority. Disclose both fictionalized paths and this hostname value in the captions.

Other private paths, hostnames, identities or tokens can still make a capture fail; do not treat this mapping as successful privacy acceptance.


## Canonical release-gallery environment

`make screenshots NAME=heinzel-resource CORE=/absolute/path/to/heinzel.whl` and
`make screenshots-verify NAME=heinzel-resource CORE=/absolute/path/to/heinzel.whl`
run the same pinned Playwright Linux/amd64 container on macOS and Linux CI. Docker must be running.
The first call downloads the public image; subsequent calls reuse the downloaded image. `OPEN=1` opens the
resulting local contact sheet after capture. `make screenshots-check NAME=heinzel-resource` remains an
inexpensive portable freshness check and does not start Docker.

The source is copied into a disposable directory without development environments, Node modules or host Git
metadata. A frozen list of the original source files preserves discovery across generated build output. The worker
receives no Git metadata, and host checks never execute Git against the worker-writable copy. No host application directory, credential directory, Docker socket or host tool directory is
mounted into the worker. The worker uses the fictional hostname demo-host, UTC and C.UTF-8, the pinned browser image, and the owning locked
Core/plugin environment. The renderer receives no confidential terms: it runs the public privacy-pattern checks only. The
trusted host applies the configured confidential-term policy to every returned transcript and caption
before importing or publishing anything; missing terms refuse the canonical command. No term list
is mounted into the worker or included in its arguments or image. All scene text remains required. Images
can still differ in rasterization; `--strict-images` additionally compares their bytes. The existing text
comparison permits changing `hh:mm` clock readings; full original transcripts remain stored and
scanned. This does not suppress any other scene text or turn a missing capture into a pass.

The advanced explicit `--python` path is an environment diagnostic, not canonical release-gallery proof.
It retains its caller-selected runtime; use the ordinary commands above for publication or CI comparison.

The worker runs with the author's/CI runner's numeric UID and GID, so its scratch files remain removable
on rootful Linux Docker as well as Docker Desktop. Its HOME, Python downloads and caches are private to
the run. Fork/Dependabot render checks need no confidential terms. Full private-policy proof still requires the trusted
host scan; private dependencies
that require credentials also refuse rather than mounting credentials. Use a separately prepared `--python`
environment with `--headed` only for noncanonical interactive diagnostics.

Private-policy acceptance requires a trusted host controller. Do not supply repository secrets to
editable pull-request code. A protected, base-owned scan route is a prerequisite for hosted private-policy
approval; a reusable workflow selected by an editable caller is not that authority.
Unscanned output must remain private until that scan passes. This local capture command does not
establish a protected GitHub approval or a fork-PR acceptance path.

`make screenshots-render-check NAME=<plugin>` is the secret-free CI path for ordinary and fork PRs. It
returns `render_verified: true`, `private_scan: false`, and `scope: render-only` only after a real fresh
comparison. It emits counts rather than unscanned transcripts, captions, images, or worker stderr, and
does not copy results out of the private scratch directory. It cannot publish. CI OK requires this executed rendering result for selected plugins, including fork PRs;
a missing plan or skipped selected render fails. Unselected changes retain the existing plan selection. Before public gallery
changes are admitted, the approved local tooling must run the full private-policy verification and
bind the passing scan to the exact committed gallery files. A future hosted private scan requires
separate protected authority; rendering success alone is never that approval.

Full DOM evidence (body, input/textarea values, title and URL) travels back only in private
`*.scan.txt` sidecars, bound by SHA-256 in the private draft manifest. The trusted host checks
those bytes against the private policy, including form values not present in the visible-body
transcript, before importing or publishing. Sidecars are never part of the public gallery or
public manifest. Older private drafts without this evidence must be captured again.
