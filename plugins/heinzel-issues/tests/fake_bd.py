"""A stand-in for `bd` with the same JSON shapes, for tests on machines without Beads; rows live in .beads/fake.json."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

STORE = Path(".beads/fake.json")


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def option(args: list[str], name: str) -> str | None:
    return args[args.index(name) + 1] if name in args else None


def main(args: list[str]) -> int:
    rows = json.loads(STORE.read_text()) if STORE.exists() else []
    command, rest = args[0], args[1:]
    if command == "create":
        row = {
            "id": f"demo-{len(rows) + 1}",
            "title": rest[0],
            "description": sys.stdin.read() if option(rest, "--body-file") == "-" else "",
            "status": "open",
            "labels": (option(rest, "--labels") or "").split(",") if option(rest, "--labels") else [],
            "created_at": now(),
            "updated_at": now(),
            "created_by": option(rest, "--actor") or "Ada Example",
        }
        rows.append(row)
        STORE.write_text(json.dumps(rows))
        print(json.dumps(row))
        return 0
    if command in {"update", "close", "show"}:
        found = [row for row in rows if row["id"] == rest[0]]
        if not found:
            print(f"Error: no issue found matching {rest[0]!r}", file=sys.stderr)
            return 1
        row = found[0]
        if command == "update":
            if "--claim" in rest:
                actor = option(rest, "--actor") or "Ada Example"
                if row.get("assignee") not in {None, "", actor}:
                    print(f"Error: {rest[0]} is already claimed by {row['assignee']}", file=sys.stderr)
                    return 1
                row.update(assignee=actor, status="in_progress")
            if notes := option(rest, "--append-notes"):
                row["notes"] = f"{row['notes']}\n{notes}" if row.get("notes") else notes
            if status := option(rest, "--status"):
                row["status"] = status
            row["updated_at"] = now()
        if command == "close":
            row.update(status="closed", close_reason=option(rest, "--reason") or "", closed_at=now(), updated_at=now())
        STORE.write_text(json.dumps(rows))
        print(json.dumps([row]))
        return 0
    if command == "list":
        label, after = option(rest, "--label"), option(rest, "--updated-after")
        shown = [
            row
            for row in rows
            if (label is None or label in row["labels"]) and (after is None or row["updated_at"] > after)
        ]
        print(json.dumps(shown))
        return 0
    print(f"unknown command {command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
