# Show what changed without opening every pull request.

The gallery should sell the useful result: a readable account of merged work and issue changes, usable in the app,
a shell, and a workflow. GitHub supplies `code-host:read` and `tracker:read`; it has no bespoke pull-request screen.
Keep the real host UI and real adapter results. A settings dialog, installed-plugin card or help page is not a hero.

## Runtime and command boundary

The owning public command is `hz github info`. There are no built-in `hz github pulls` or `hz github issues`
commands. `hz system capability list` describes bindings; it does not execute a capability method.
For useful result captures, the documentation bootstrap must register a **fixture-only** `showcase` requester using
public `Module`, `CodeHost`, `Tracker` and `Window` APIs. Adapt `digest()` from
[the integration tests](../tests/integration/capability_test.py), retaining the real GitHub adapter. Proposed
`hz showcase merged` and `hz showcase issues` commands below belong only to that demonstration profile, not to the
released GitHub CLI. The contact sheet and captions must say so.

Use repository `acme/widgets` and the fixed half-open UTC window `2026-10-01T00:00:00+00:00` to
`2026-11-01T00:00:00+00:00`. Keep two or three concise rows per result.

## Required scenes, in gallery order

| Scene | Surface and actual action | Visible result and caption | Why it matters |
| --- | --- | --- | --- |
| Merged work | UI: open the real in-app terminal, then `hz showcase merged acme/widgets` | Render actual `CodeHost.merged_pull_requests` results with number, title, author and merge date. Caption: “Merged pull requests through the GitHub adapter — fictional repository in the app terminal.” | A manager can see what shipped without opening each PR. |
| Issue changes | UI: app terminal running `hz showcase issues acme/widgets` | Actual issue key, title, state, owner and labels; no pull requests mixed into issues. Caption: “Changes and owners from the tracker adapter — fictional issue data.” | Shows the second capability and actionable ownership. |
| Shell result | CLI: run the same merged command through the installed CLI head | A readable, complete terminal result, with command visible. Caption: “Read merged work from the shell — fixture-only requester, real GitHub adapter.” | Demonstrates scripting and the same data outside the app. |
| Structured tracker | CLI: issue command with `--json` | Two complete objects with stable keys, without an enormous packet. Caption: “Typed issue results for scripts and agents — fictional data.” | Shows that automation gets structured data, not scraped prose. |
| Workflow context | UI: open a seeded read-only `weekly-code-review` contract at `/contracts/weekly-code-review` | Actual contract goal, `code-host:read` and `tracker:read` inputs, named weekly output. Caption: “Use GitHub reads in a weekly-review contract — local demonstration.” | Connects raw adapter data to a useful recurring task. |

The workflow scene is included only after the bootstrap creates a real local contract and verifies it loads.
A contract page alone is not evidence that a report was generated; do not caption it as a completed digest.

## Fixture entry points

Reuse [fake_gh.py](../tests/fake_gh.py) and the `fake_gh_cli` installation pattern from
[conftest.py](../tests/conftest.py). Route only `repos/acme/widgets/pulls` and `repos/acme/widgets/issues` to the
existing fictional [pulls](../tests/fixtures/pulls.json) and [issues](../tests/fixtures/issues.json) shapes.
Add more fictional rows only when needed to make different states readable. Bind `code_host = "github"` and
`tracker = "github"` in the isolated user configuration. Resolve only the fake executable; never fall back to `gh`
on the developer's PATH. A missing fixture route must fail the capture.

A compact Rich table supplied by the demonstration requester is acceptable; it formats values returned by the
real adapter and must not invent a GitHub-specific product screen. Keep source references and the fixture-only
command distinction in `docs/SCREENSHOTS.md` beside the resulting images.

## Accessible capture and acceptance

- Open `button` **Open a terminal**, then `button` **Full screen**. Wait for the actual command to finish and the
  expected PR title or issue key before capture; the command and every row must fit.
- Wait for `heading` **Weekly code review** on the shared contract page; use the actual seeded title consistently.
- Every required scene returns nonempty results from the real adapter. Tests assert the fake vendor was called,
  window filtering works, and issue results exclude PRs. Both UI and CLI captures are present.
- No network request leaves loopback. Only fictional names, `acme/widgets`, and fixture URLs may appear; no real
  account, local path, hostname, credential, browser token or call-log environment reaches an image or transcript.
- Review the contact sheet at actual catalog thumbnail size, then open full images. Reject help-only, loading,
  error, clipped or mostly empty terminal captures. The first two scenes must explain the plugin without prose.

## Current captured scope

The documentation bootstrap uses the test suites' in-memory vendor-runner pattern: it binds only `DemoGh` at `Gh`
while retaining the actual installed capability adapters and conversions. It never executes a vendor client.
The fixed October window lives inside the fixture requester, so the displayed commands stay concise.
The workflow scene is a real seeded, valid local contract. It declares inputs; no agent or report generation runs.
