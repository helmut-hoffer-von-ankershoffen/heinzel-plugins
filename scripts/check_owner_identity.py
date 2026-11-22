#!/usr/bin/env python3
"""Refuse a commit whose author or committer is not the owner's identity (owner rule: every commit is the owner's).

    check_owner_identity.py               the author and committer git will record for the next commit (pre-commit)
    check_owner_identity.py --unpushed    the author and committer of every commit not on origin/main (pre-push)
    check_owner_identity.py --range A..B  the commits of a range

Fix a refusal with `git config user.name` and `git config user.email` in this repository (the values are printed),
and `git commit --amend --reset-author` or `git rebase --exec` for commits already made. Never bypass the hook.
"""

import shutil
import subprocess
import sys

OWNER = "helmut-hoffer-von-ankershoffen <1826050+helmut-hoffer-von-ankershoffen@users.noreply.github.com>"
USAGE = 2
GIT = shutil.which("git") or "git"


def git(*args: str) -> str:
    """The output of one git command; raises CalledProcessError when git refuses."""
    return subprocess.run([GIT, *args], check=True, capture_output=True, text=True).stdout.strip()


def ident(line: str) -> str:
    """`Name <email> 1700000000 +0100` -> `Name <email>`."""
    return line.rsplit(">", 1)[0] + ">" if ">" in line else line


def problems_of(pairs: list[tuple[str, str, str]]) -> list[str]:
    """One line for every (where, role, identity) triple that is not the owner."""
    return [f"{where}: the {role} is {who or 'unset'}, not the owner" for where, role, who in pairs if who != OWNER]


def next_commit() -> list[tuple[str, str, str]]:
    """The author and committer git will record for the next commit."""
    roles = ("author", "committer")
    return [("the next commit", role, ident(git("var", f"GIT_{role.upper()}_IDENT"))) for role in roles]


def commits(rev_range: str) -> list[tuple[str, str, str]]:
    """The author and committer of every commit of the range."""
    out = git("log", "--format=%h%x09%an <%ae>%x09%cn <%ce>", rev_range)
    pairs = []
    for line in filter(None, out.splitlines()):
        sha, author, committer = line.split("\t")
        pairs += [(f"commit {sha}", "author", author), (f"commit {sha}", "committer", committer)]
    return pairs


def main(argv: list[str]) -> int:
    """Check what the arguments select; 0 when every identity is the owner's."""
    try:
        if argv[:1] == ["--range"] and len(argv) == USAGE:
            found = problems_of(commits(argv[1]))
        elif argv == ["--unpushed"]:
            found = problems_of(commits("origin/main..HEAD"))
        elif not argv:
            found = problems_of(next_commit())
        else:
            print(__doc__, file=sys.stderr)
            return USAGE
    except subprocess.CalledProcessError as err:
        print(f"owner identity check could not read git: {err.stderr.strip() or err}", file=sys.stderr)
        return 1
    for line in found:
        print(line, file=sys.stderr)
    if found:
        name, _, email = OWNER.partition(" <")
        print(f"Every commit is the owner's. Here: git config user.name {name}", file=sys.stderr)
        print(f"and git config user.email {email.rstrip('>')}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
