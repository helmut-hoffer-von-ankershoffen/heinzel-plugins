"""Seed the personal Jira test project KAN with a fictional set of epics and work items, through real acli.

Run by hand, never by CI: `python tests/live/seed_kan.py`. It is idempotent: an item whose summary already exists in
the project is left alone. Everything here is fictional.
"""

import json
import subprocess
import sys
import tempfile

PROJECT = "KAN"
# (summary, type, parent summary, labels, assignee, status, due, description)
EPICS = [
    (
        "Harbor Lights: tide-table app launch",
        "Epic",
        ["harbor"],
        "Ship the tide-table app to the first 500 harbour towns.",
    ),
    ("Lantern Cafe: online ordering", "Epic", ["lantern"], "Let regulars order ahead and skip the queue."),
    ("Quiet Hours: notification settings", "Epic", ["quiet"], "People choose when the app may interrupt them."),
    ("Compass: onboarding refresh", "Epic", ["compass"], "A shorter first-run tour; nearly done."),
]
ITEMS = [
    (
        "Import tide tables for the northern coast",
        "Task",
        "Harbor Lights: tide-table app launch",
        ["harbor", "data"],
        "@me",
        "In Progress",
        "2026-11-02",
        "Parse the CSV exports and check the high/low times against the printed almanac.",
    ),
    (
        "Design the low-tide alert sheet",
        "Task",
        "Harbor Lights: tide-table app launch",
        ["harbor", "design"],
        "@me",
        "To Do",
        "2026-11-06",
        "Alert sheet with the next three low tides.",
    ),
    (
        "Fix wrong time zone on the Dunmore harbour page",
        "Task",
        "Harbor Lights: tide-table app launch",
        ["harbor", "bug"],
        "@me",
        "To Do",
        "2026-10-28",
        "Dunmore shows UTC instead of local time. Overdue on purpose.",
    ),
    (
        "Renew the harbour data licence",
        "Task",
        "Harbor Lights: tide-table app launch",
        ["harbor", "legal"],
        "@me",
        "To Do",
        "2026-10-28",
        "The almanac licence ran out; renew it. Overdue on purpose.",
    ),
    (
        "Write store listing copy",
        "Task",
        "Harbor Lights: tide-table app launch",
        ["harbor", "marketing"],
        None,
        "To Do",
        None,
        "Short and long description, five screenshots.",
    ),
    (
        "Set up crash reporting",
        "Task",
        "Harbor Lights: tide-table app launch",
        ["harbor", "blocked"],
        "@me",
        "To Do",
        None,
        "Blocked until the build pipeline has a signing key.",
    ),
    (
        "Menu API: list today's specials",
        "Task",
        "Lantern Cafe: online ordering",
        ["lantern", "api"],
        "@me",
        "In Progress",
        "2026-11-04",
        "GET /specials with allergens.",
    ),
    (
        "Order-ahead checkout screen",
        "Story",
        "Lantern Cafe: online ordering",
        ["lantern", "design"],
        None,
        "To Do",
        "2026-11-12",
        "As a regular I can pay and pick a time slot.",
    ),
    (
        "Pickup-time slots need a capacity limit",
        "Task",
        "Lantern Cafe: online ordering",
        ["lantern"],
        "@me",
        "To Do",
        "2026-11-03",
        "Max 12 orders per quarter hour.",
    ),
    (
        "Barista tablet view of open orders",
        "Task",
        "Lantern Cafe: online ordering",
        ["lantern", "tablet"],
        None,
        "To Do",
        None,
        "Large type, one tap to mark ready.",
    ),
    (
        "Quiet-hours schedule picker",
        "Story",
        "Quiet Hours: notification settings",
        ["quiet", "design"],
        "@me",
        "To Do",
        "2026-11-09",
        "Pick weekdays and a start and end time.",
    ),
    (
        "Respect quiet hours in push delivery",
        "Task",
        "Quiet Hours: notification settings",
        ["quiet", "backend"],
        None,
        "To Do",
        None,
        "Queue pushes during quiet hours and deliver at the end.",
    ),
    (
        "Document the notification categories",
        "Task",
        "Quiet Hours: notification settings",
        ["quiet", "docs"],
        None,
        "Done",
        None,
        "Done last week.",
    ),
    (
        "Trim the welcome tour to three screens",
        "Task",
        "Compass: onboarding refresh",
        ["compass"],
        "@me",
        "Done",
        None,
        "Shipped.",
    ),
    (
        "Add a skip button to the tour",
        "Task",
        "Compass: onboarding refresh",
        ["compass"],
        None,
        "Done",
        None,
        "Shipped.",
    ),
]

COMMENTS = [
    (
        "Import tide tables for the northern coast",
        "Northern coast CSVs imported; the Dunmore rows still have the wrong offset.",
    ),
    (
        "Fix wrong time zone on the Dunmore harbour page",
        "Reproduced: the page shows 14:05 for a 15:05 local high tide.",
    ),
    ("Set up crash reporting", "Waiting for the signing key from the build pipeline; nothing to do until then."),
    (
        "Pickup-time slots need a capacity limit",
        "Agreed with the cafe: twelve orders per quarter hour, to be revisited after a week.",
    ),
]


def acli(*args: str) -> object:
    done = subprocess.run(["acli", *args], capture_output=True, text=True, check=False)
    if done.returncode != 0:
        sys.exit(f"acli {' '.join(args[:3])} failed: {done.stderr.strip() or done.stdout.strip()}")
    return json.loads(done.stdout) if "--json" in args and done.stdout.strip() else None


def me() -> str:
    """The email address acli is signed in as."""
    done = subprocess.run(["acli", "jira", "auth", "status"], capture_output=True, text=True, check=False)
    return next(line.split(":", 1)[1].strip() for line in done.stdout.splitlines() if line.strip().startswith("Email:"))


def existing() -> dict[str, str]:
    found = acli("jira", "workitem", "search", "--jql", f"project = {PROJECT}", "--paginate", "--json")
    assert isinstance(found, list)
    return {item["fields"]["summary"]: item["key"] for item in found}


def main() -> None:
    keys = existing()
    for summary, kind, labels, text in EPICS:
        if summary not in keys:
            made = acli(
                "jira",
                "workitem",
                "create",
                "--project",
                PROJECT,
                "--type",
                kind,
                "--summary",
                summary,
                "--label",
                ",".join(labels),
                "--description",
                text,
                "--json",
            )
            keys[summary] = made["key"]  # type: ignore[index]
            sys.stdout.write(f"created {keys[summary]} {summary}\n")
    for summary, kind, parent, labels, assignee, status, due, text in ITEMS:
        if summary in keys:
            continue
        attributes: dict[str, object] = {"parent": {"key": keys[parent]}}
        if due:  # acli has no due-date flag: a definition file carries it, and the parent
            attributes["duedate"] = due
        definition = {
            "projectKey": PROJECT,
            "type": kind,
            "summary": summary,
            "labels": labels,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
            },
            "additionalAttributes": attributes,
        }
        if assignee:  # a definition file wants an email address, not "@me"
            definition["assignee"] = me()
        with tempfile.NamedTemporaryFile("w", suffix=".json") as handle:
            json.dump(definition, handle)
            handle.flush()
            made = acli("jira", "workitem", "create", "--from-json", handle.name, "--json")
        key = made["key"]  # type: ignore[index]
        keys[summary] = key
        if status != "To Do":
            acli("jira", "workitem", "transition", "--key", key, "--status", status, "--yes", "--json")
        sys.stdout.write(f"created {key} {summary}\n")
    for summary, body in COMMENTS:
        key = keys[summary]
        listed = acli("jira", "workitem", "comment", "list", "--key", key, "--json")
        if not (listed or {}).get("comments"):  # type: ignore[union-attr]
            acli("jira", "workitem", "comment", "create", "--key", key, "--body", body, "--json")
            sys.stdout.write(f"commented {key}\n")
    sys.stdout.write(f"{len(keys)} items in {PROJECT}\n")


if __name__ == "__main__":
    main()
