# heinzel-slack

Slack as an extra notification channel and as a place to share a draft and get a yes or no back: a
[Heinzelmännchen](https://github.com/helmut-hoffer-von-ankershoffen/heinzel) plugin, released on its own.

- **A notice says why.** Every message carries "Why you are seeing this", because a nudge that cannot say why is noise.
- **A draft is shared with Approve and Decline.** The answer is for the exact text you saw, and only you can give it.
- **Your DM only.** It writes to your direct message with your own app. Never a channel, never anyone else.

```text
Lotte has a draft for you
Weekly report
Why you are seeing this: It is Friday and you asked for a report.
| Weekly report ...                                |
Nothing goes out until you say so. Fingerprint 3fa9c1d2b4e0 · answer by 16:00 · only your click counts.
[ Approve ] [ Decline ]
```

## Prerequisites

You need all of these. Nothing is optional except the first line.

1. **A Heinzelmännchen with the channel ports** (core ADR 0112, first released after 0.9.8) and this plugin:
   `hz system plugin add slack --confirm`. On 0.9.8 itself the plugin cannot load.
2. **A Slack workspace where you may install an app.** You create a *private app that only you use*, in your own
   workspace, from the manifest this plugin ships. If your workspace lets only admins install apps, ask for approval
   of that one app (the manifest lists exactly what it can do) or use a workspace of your own. The plugin does not
   work around that setting.
3. **Your Slack member ID**: your profile, the three dots, "Copy member ID" (like `U01ABCDEF`).
4. **Two tokens from your app**, kept in the OS keychain by `hz`, never in a file or a repository:
   - the **bot token** (`xoxb-...`, on *Install App*), scopes `chat:write`, `im:write`, `users:read`;
   - an **app-level token** (`xapp-...`, on *Basic Information*, scope `connections:write`) for Socket Mode.
5. **Python 3.12+** (supplied by uv) and an internet connection to `slack.com`. No public address, no port to open.

## Set up (about three minutes)

```bash
hz slack manifest                                  # copy the JSON
# api.slack.com/apps, Create New App, From a manifest, paste it, Create, Install to Workspace.
# Basic Information, App-Level Tokens, Generate Token with connections:write.
hz system credential set bot-token --service slack
hz system credential set app-token --service slack
hz system config set slack.owner U01ABCDEF         # or: hz setup slack
hz system doctor                                   # then: hz system connector test slack
```

Registering the channel is all `hz` needs: core finds `slack` as a notification channel and an approval channel and
offers it to the helpers whose schedule you reviewed to use it. You can also use it by hand:

```bash
hz slack notify "Build done" "You asked to know when it finishes." --helper Otto
hz slack ask "Send the weekly report" "$(cat report.md)" --helper Lotte
hz slack wait <request-id>        # listens for your click, up to --seconds; or: hz slack status <request-id>
```

**Clicks are only registered while something listens** (`wait`, `listen`, or the five-minute `listen` job while a draft is waiting). A button pressed with
nobody listening shows Slack's "not responding" notice and the draft stays waiting; press it again once `hz` listens.
The message says nothing false in the meantime: it still shows the buttons because it is still unanswered.

## What approval means here

Approval is a typed code path (T3), not a message. `ApprovalOutcome.approves(draft)` is true only if all of this held:

| Held at click time | How |
| --- | --- |
| It is a **button** press on our message | Replies, reactions and slash commands are not even subscribed to, and any such payload is refused |
| The person is **you** | The clicker's Slack ID equals the owner recorded *before* posting; a project `hz.toml` cannot set it |
| Right **workspace, conversation and message** | Compared with what was recorded when the message was posted |
| The **exact bytes** | The button carries the sha256 of the draft; the stored draft is hashed again under the lock; `approves(draft)` hashes what you pass |
| Still **fresh** | Pending, not expired (default 4 hours), click time plausible; a newer draft with the same `key` voids older ones |
| **Once** | The move from pending to decided is a single atomic update, so a second click, a Slack retry or a replay is refused |

Everything else from Slack is data. Only identifiers are read; message text, names and replies are never parsed for
meaning. A draft containing control, zero-width or bidirectional characters is refused (it could not be reviewed as
it is), and a draft over 4,000 characters is refused (you could not read it all in Slack). The draft is shown in a
literal preformatted block, so mentions and links in it are inert. Refused clicks are recorded in the audit trail
(`approvals.sqlite3` in the state folder, readable by you only) with a code of ours, never Slack's text.

What this does **not** prove: that a human, rather than software running as you in Slack, pressed the button. It is an
application-level decision by the owner's Slack account, as in `hz` core's own confirmations. Anyone who controls
your Slack account or the machine controls your approvals.

## Why your own app and not a browser session or the Slack CLI

| Approach | Verdict |
| --- | --- |
| **Browser session tokens** (community CLIs such as `slackcli` with `xoxc`/`xoxd`) | Acts as you, nothing to install, but it is an unofficial use of your login that Slack can break or forbid at any time, tokens die when you sign out, and it cannot receive button clicks. Approval would be a reaction or a typed reply, which cannot be bound to the exact bytes. Not a dependency for a product. |
| **The official Slack CLI** (`slack`) | Builds and runs apps on Slack's platform and manages manifests; it has no way to post a message or receive a click for another tool. Useful for creating and installing the app during development. |
| **A private Slack app** (this plugin): bot token for the Web API, Socket Mode for clicks, official `slack-sdk` | Supported by Slack, least privilege (three bot scopes, no user scope, no event subscriptions), signed identity of the clicker in every click, and no inbound address, so nothing is hosted. **Chosen.** |

Tenets weighed: P1 ("your identity over a bot identity") and ADR 0035 ("only what an ordinary employee may do, no admin-registered
apps") against T3 and P2 (approval must be bound and verifiable) and distributability. The app here is yours alone, in
your workspace, created by you, and it only ever writes to your own DM as a mailbox: it never posts as you and never to
a shared channel. Anything published under your name later is a separate step with your identity. If you cannot install an
app, the plugin reports so; it does not fall back to a browser session.

## Ports

The plugin registers one service, `SlackChannel`, a `NotificationChannel` and an `ApprovalChannel` as core defines them
(ADR 0112); core imports nothing from this plugin and names no Slack. A channel carries words and never decides:

- `deliver(notice)` posts at most once per `key`. The receipt says what was observed: `delivered`, `refused` (Slack said
  no, safe to retry) or `unknown` (the answer was lost, so it may have been sent and is never retried by itself).
- `post(request)` shows the exact preview with Approve and Decline, bound to the request's `arguments_sha256` and expiry,
  idempotent by `request_id`. `replies(references)` returns only clicks that passed every check above, with the owner's
  member ID as the actor; the host checks that actor, digest and expiry again before it consumes any approval.
- `settle(reference, outcome)` closes the message once the host has acted, expired it or replaced it.

Until a core release carries these ports, build and test against a candidate core wheel (`CORE=<wheel>`, or the CI
`core_run` input).

## Development

```bash
make check-fast
```

The in-memory Slack in `tests/conftest.py` is a labelled fake. `tests/e2e/live_test.py` talks to a real workspace when
`SLACK_PROOF=1`; the tokens come from the environment (the official `slack run` injects them without printing them).
