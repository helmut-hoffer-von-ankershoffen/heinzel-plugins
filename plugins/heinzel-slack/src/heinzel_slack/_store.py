"""The record of every approval request, kept on this machine before anything is posted (T2).

SQLite gives the one thing approval needs from storage: a transition from `pending` to a decision that exactly one
caller wins, across threads and processes. The draft's bytes are stored with its digest so that a decision is
checked against what is on disk, not against what a button claims.
"""

import contextlib
import os
import sqlite3
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from heinzel_slack._digest import draft_digest

_SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id TEXT PRIMARY KEY, external TEXT NOT NULL UNIQUE, owner TEXT NOT NULL, team TEXT NOT NULL,
    channel TEXT NOT NULL, message_ts TEXT NOT NULL, bound TEXT NOT NULL, digest TEXT NOT NULL, draft TEXT NOT NULL,
    action TEXT NOT NULL, helper TEXT NOT NULL, state TEXT NOT NULL,
    created_at TEXT NOT NULL, expires_at TEXT NOT NULL, decided_at TEXT, decided_by TEXT,
    detail TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS deliveries (
    key TEXT PRIMARY KEY, status TEXT NOT NULL, reference TEXT, at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
    n INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, request_id TEXT NOT NULL,
    event TEXT NOT NULL, detail TEXT NOT NULL
);
"""


@dataclass(frozen=True, slots=True)
class Row:
    """One stored request."""

    id: str
    external: str
    owner: str
    team: str
    channel: str
    message_ts: str
    bound: str
    digest: str
    draft: str
    action: str
    helper: str
    state: str
    created_at: datetime
    expires_at: datetime
    decided_at: datetime | None
    decided_by: str | None
    detail: str


def _stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


class Store:
    """Approval requests and their audit trail, in one SQLite file only the owner can read."""

    def __init__(self, directory: Path) -> None:
        """Create the folder (0700) and the file (0600) on first use."""
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
        self.path = directory / "approvals.sqlite3"
        with contextlib.suppress(OSError):
            os.close(os.open(self.path, os.O_CREAT | os.O_WRONLY, 0o600))
        self.path.chmod(0o600)
        with self._connect() as db:
            db.executescript(_SCHEMA)

    @contextlib.contextmanager
    def _connect(self) -> Generator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            yield db
        finally:
            db.close()

    @contextlib.contextmanager
    def _transaction(self) -> Generator[sqlite3.Connection]:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
            except BaseException:
                db.execute("ROLLBACK")
                raise
            db.execute("COMMIT")

    def insert(self, row: Row) -> Row | None:
        """Record a new request as `posting`; if its external id exists, return the stored one and write nothing."""
        with self._transaction() as db:
            found = db.execute("SELECT * FROM requests WHERE external=?", (row.external,)).fetchone()
            if found:
                return _row(found)
            db.execute(
                "INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,'')",
                (
                    row.id,
                    row.external,
                    row.owner,
                    row.team,
                    row.channel,
                    row.message_ts,
                    row.bound,
                    row.digest,
                    row.draft,
                    row.action,
                    row.helper,
                    row.state,
                    _stamp(row.created_at),
                    _stamp(row.expires_at),
                ),  # fmt: skip
            )
            self._audit(db, row.created_at, row.id, "created", f"digest {row.bound[:12]}")
        return None

    def mark(self, request_id: str, state: str, now: datetime) -> bool:
        """Close an open request as `superseded`, `expired` or similar on the host's word; decided ones stay."""
        with self._transaction() as db:
            done = db.execute(
                "UPDATE requests SET state=?, decided_at=? WHERE id=? AND state IN ('pending','posting')",
                (state, _stamp(now), request_id),
            ).rowcount
            if done:
                self._audit(db, now, request_id, state, "by host")
            return bool(done)

    def delivery(self, key: str) -> tuple[str, str | None] | None:
        """The recorded state of a notice key: (status, reference)."""
        with self._connect() as db:
            found = db.execute("SELECT status, reference FROM deliveries WHERE key=?", (key,)).fetchone()
        return (str(found[0]), found[1]) if found else None

    def begin_delivery(self, key: str, now: datetime) -> bool:
        """Record the intent to send a notice before sending it; False if the key was already tried (T2)."""
        with self._transaction() as db:
            if db.execute("SELECT 1 FROM deliveries WHERE key=?", (key,)).fetchone():
                return False
            db.execute("INSERT INTO deliveries VALUES (?, 'attempted', NULL, ?)", (key, _stamp(now)))
            return True

    def forget_delivery(self, key: str) -> None:
        """Forget an attempt Slack refused, so the same notice can be tried again."""
        with self._transaction() as db:
            db.execute("DELETE FROM deliveries WHERE key=? AND status='attempted'", (key,))

    def end_delivery(self, key: str, status: str, reference: str | None) -> None:
        """Record what became of a notice."""
        with self._transaction() as db:
            db.execute("UPDATE deliveries SET status=?, reference=? WHERE key=?", (status, reference, key))

    def by_external(self, external: str) -> Row | None:
        """The request a host id maps to, or None."""
        with self._connect() as db:
            found = db.execute("SELECT * FROM requests WHERE external=?", (external,)).fetchone()
        return _row(found) if found else None

    def posted(self, request_id: str, message_ts: str, now: datetime) -> bool:
        """Mark a request `pending` once Slack has the message; False if it was voided in the meantime."""
        with self._transaction() as db:
            done = db.execute(
                "UPDATE requests SET state='pending', message_ts=? WHERE id=? AND state='posting'",
                (message_ts, request_id),
            ).rowcount
            if done:
                self._audit(db, now, request_id, "posted", message_ts)
            return bool(done)

    def failed(self, request_id: str, detail: str, now: datetime) -> None:
        """Mark a request whose post failed; it can never be approved."""
        with self._transaction() as db:
            db.execute(
                "UPDATE requests SET state='failed', detail=? WHERE id=? AND state='posting'", (detail, request_id)
            )
            self._audit(db, now, request_id, "failed", detail)

    def get(self, request_id: str) -> Row | None:
        """The stored request, or None."""
        with self._connect() as db:
            found = db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
        return _row(found) if found else None

    def decide(  # noqa: PLR0913 - one atomic transition, every input independent
        self, request_id: str, state: str, by: str, bound: str, now: datetime
    ) -> bool:
        """Move a request from `pending` to `approved` or `declined`; exactly one caller can win.

        The stored draft is hashed again under the lock and must still match the digest the decision is for.
        """
        with self._transaction() as db:
            found = db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
            if not found:
                return False
            row = _row(found)
            if row.state != "pending" or row.bound != bound or draft_digest(row.draft) != row.digest:
                return False
            if now >= row.expires_at:
                return False
            db.execute(
                "UPDATE requests SET state=?, decided_at=?, decided_by=? WHERE id=? AND state='pending'",
                (state, _stamp(now), by, request_id),
            )
            self._audit(db, now, request_id, state, by)
            return True

    def expire_due(self, now: datetime) -> list[Row]:
        """Mark pending requests past their time `expired`; the ones just expired."""
        with self._transaction() as db:
            found = db.execute("SELECT * FROM requests WHERE state='pending' AND expires_at<=?", (_stamp(now),))
            rows = [_row(r) for r in found.fetchall()]
            for row in rows:
                db.execute("UPDATE requests SET state='expired', decided_at=? WHERE id=?", (_stamp(now), row.id))
                self._audit(db, now, row.id, "expired", "")
        return rows

    def pending(self) -> list[Row]:
        """Requests still waiting for an answer, oldest first."""
        with self._connect() as db:
            found = db.execute("SELECT * FROM requests WHERE state='pending' ORDER BY created_at").fetchall()
        return [_row(r) for r in found]

    def deny(self, request_id: str, reason: str, now: datetime) -> None:
        """Keep a refused answer in the audit trail; its reason is a code of ours, never Slack's text."""
        with self._transaction() as db:
            self._audit(db, now, request_id[:64], "denied", reason)

    def audit(self, request_id: str) -> list[tuple[str, str]]:
        """The events of a request, oldest first, as (event, detail)."""
        with self._connect() as db:
            found = db.execute("SELECT event, detail FROM audit WHERE request_id=? ORDER BY n", (request_id,))
            return [(str(a), str(b)) for a, b in found.fetchall()]

    @staticmethod
    def _audit(db: sqlite3.Connection, at: datetime, request_id: str, event: str, detail: str) -> None:
        db.execute(
            "INSERT INTO audit (at, request_id, event, detail) VALUES (?,?,?,?)",
            (_stamp(at), request_id, event, detail[:200]),
        )


def _row(found: sqlite3.Row | tuple[object, ...]) -> Row:
    (rid, external, owner, team, channel, ts, bound, digest, draft, action, helper, state, created, expires, decided,
     by, detail) = found  # fmt: skip
    return Row(
        id=str(rid), external=str(external), owner=str(owner), team=str(team), channel=str(channel),
        message_ts=str(ts), bound=str(bound), digest=str(digest), draft=str(draft), action=str(action),
        helper=str(helper), state=str(state), created_at=datetime.fromisoformat(str(created)),
        expires_at=datetime.fromisoformat(str(expires)),
        decided_at=datetime.fromisoformat(str(decided)) if decided else None,
        decided_by=str(by) if by else None, detail=str(detail),
    )  # fmt: skip
