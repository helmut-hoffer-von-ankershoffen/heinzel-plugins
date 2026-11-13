# Changelog

## Unreleased

## 0.2.0

Forget a request when its Heinzel is deleted for good (Core ADR 0148). The channel's new
`forget(request_id, reference)` finds a request by either key, also a draft stored before a post that never got a
receipt, and deletes its rows (draft preview, approval state and audit trail) from `approvals.sqlite3`, zeroes the freed pages,
rewrites the file and empties the WAL, so no byte of the draft stays in the database, its free pages, the -wal or the
-shm file. It works offline and is idempotent. A request still open in Slack is withdrawn there best effort, in the
background and without its draft; forgetting never waits on the network. A Core without the hook never calls it.

## 0.1.0

First version: notices and shared drafts in the owner's own Slack direct message, through the owner's private Slack
app (official Web API and Socket Mode). Approve and Decline are bound to the exact draft bytes and to the owner;
a reply, a reaction, another person, a replaced or expired draft and a replayed click never approve.
