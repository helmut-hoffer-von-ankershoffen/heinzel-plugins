"""Record real acli answers from the personal test project KAN as fixtures, with the person made fictional.

Run by hand: `python tests/live/capture_fixtures.py`. Names, addresses, avatars and account ids are replaced; the
shape of every answer is acli's own.
"""

import json
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "fixtures" / "live"
VIEW = "summary,status,assignee,priority,labels,issuetype,parent,duedate,created,updated,description,comment"
IDENTITY = {"displayName": "Wren Calder", "emailAddress": "wren@example.com", "accountId": "acct-wren"}


def run(*args: str) -> tuple[int, str, str]:
    done = subprocess.run(["acli", *args], capture_output=True, text=True, check=False)
    return done.returncode, done.stdout, done.stderr


def anonymous(node: object, real: dict[str, str]) -> object:
    if isinstance(node, dict):
        return {
            k: (IDENTITY[k] if k in IDENTITY and v == real.get(k) else anonymous(v, real))
            for k, v in node.items()
            if k != "avatarUrls"
        }
    if isinstance(node, list):
        return [anonymous(v, real) for v in node]
    if isinstance(node, str):
        return node.replace(real.get("accountId", "\0"), "acct-wren")
    return node


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    code, out, err = run("jira", "workitem", "view", "KAN-8", "--fields", VIEW, "--json")
    assert code == 0, err
    real = json.loads(out)["fields"]["assignee"]
    jobs = {
        "view_task.json": ("jira", "workitem", "view", "KAN-8", "--fields", VIEW, "--json"),
        "view_overdue.json": ("jira", "workitem", "view", "KAN-10", "--fields", VIEW, "--json"),
        "view_epic.json": ("jira", "workitem", "view", "KAN-4", "--fields", VIEW, "--json"),
        "search_assigned.json": (
            "jira",
            "workitem",
            "search",
            "--jql",
            "assignee = currentUser() ORDER BY key",
            "--fields",
            "key,summary,status",
            "--paginate",
            "--json",
        ),
        "search_children.json": (
            "jira",
            "workitem",
            "search",
            "--jql",
            "parent = KAN-4 ORDER BY key",
            "--fields",
            "key,summary,status",
            "--paginate",
            "--json",
        ),
    }
    for name, args in jobs.items():
        code, out, err = run(*args)
        if code != 0:
            sys.exit(f"{name}: {err}")
        (OUT / name).write_text(json.dumps(anonymous(json.loads(out), real), indent=1, sort_keys=True) + "\n")
        sys.stdout.write("wrote", name + "\n")
    errors = {}
    for name, probe in {
        "missing_item": ("jira", "workitem", "view", "KAN-999", "--json"),
        "bad_type": None,
        "bad_jql": ("jira", "workitem", "search", "--jql", "bad ((", "--limit", "1", "--json"),
        "field_not_allowed": ("jira", "workitem", "search", "--jql", "project = KAN", "--fields", "updated", "--json"),
        "missing_summary": ("jira", "workitem", "create", "--project", "KAN", "--type", "Task", "--json"),
    }.items():
        command = probe or (
            "jira",
            "workitem",
            "create",
            "--project",
            "KAN",
            "--type",
            "Bug",
            "--summary",
            "probe",
            "--json",
        )
        _, out, err = run(*command)
        errors[name] = (err or out).strip()
    code, out, err = (
        subprocess.run(
            ["acli", "jira", "workitem", "search", "--jql", "project = KAN", "--limit", "1", "--json"],
            capture_output=True,
            text=True,
            check=False,
            env={"HOME": "/nonexistent-home", "PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
        ),
        None,
        None,
    )
    errors["signed_out"] = (code.stderr or code.stdout).strip()
    (OUT / "errors.json").write_text(json.dumps(errors, indent=1, sort_keys=True) + "\n")
    sys.stdout.write(f"{json.dumps(errors, indent=1)}\n")


if __name__ == "__main__":
    main()
