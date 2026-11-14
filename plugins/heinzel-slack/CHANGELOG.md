# Changelog

## Unreleased

## 0.3.0

Slack as Core's `chat` capability, with the self channel of Core ADR 0160. `messages` reads a public channel the bot
was invited to over a time window (paged, threads included, mentions shown as names, all text cleaned as untrusted);
`post` posts with every mention and broadcast neutralised. `notify_self` and `ask_self` reach the owner in their own
DM: a question carries one button per option and is answered by the owner's click (Socket Mode) or a typed reply
(polled), bounded by its timeout, cancellable, and never leaving a socket open. Self-channel clicks are routed through
the local store, so a click that reaches the approval listener still answers, and they never count as an approval.
Slack's rate limits are waited out within bounds. The app manifest adds the scopes `channels:history`, `channels:read` and `im:history` and lets
the owner type in the DM: reinstall the app from `hz slack manifest`. Reviewed notices and draft approvals are
unchanged.

## 0.2.0

Forget a request when its Heinzel is deleted for good (Core ADR 0148). The channel's new
`forget(request_id, reference)` finds a request by either key, also a draft stored before a post that never got a
receipt, and deletes its rows (draft preview, approval state and audit trail) from `approvals.sqlite3`, zeroes the freed pages,
rewrites the file and empties the WAL, so no byte of the draft stays in the database, its free pages, the -wal or the
-shm file. It works offline and is idempotent. Every posted message of the request, also one Core has just settled
as replaced, is then edited in Slack to a short "Withdrawn" without its draft, best effort and in the background;
forgetting never waits on the network. A Core without the hook never calls it.

## 0.1.0

First version: notices and shared drafts in the owner's own Slack direct message, through the owner's private Slack
app (official Web API and Socket Mode). Approve and Decline are bound to the exact draft bytes and to the owner;
a reply, a reaction, another person, a replaced or expired draft and a replayed click never approve.
