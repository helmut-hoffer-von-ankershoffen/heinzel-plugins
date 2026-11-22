"""The gate guard: a pull request that changes what sets the coverage floor or the Sonar bar needs the owner's label.

The `Gate guard` job of .github/workflows/ci.yml runs main's copy of this file, and `CI OK`
requires it on pull requests. It compares the guarded facts at main (the test merge's first parent) and at this run's
merge commit: the CI jobs that measure and judge coverage and Sonar (and CI OK and this job), the judges' scripts, the
coverage and test sections of pyproject.toml, and the extra files in GUARDED_FILES. When one differs, it passes only
if the repository owner put the label `gate-change-approved` on the pull request after this run started (push, label,
then re-run the failed jobs). The verdict names every changed fact.

Limit: this job's steps come from the pull request's own ci.yml. A pull request that rewrites them escapes the guard;
that change is in the diff of the gate-guard job, which its reviewer reads. Only a check run from main's workflow
(a ruleset-required workflow or Gate review) closes it.

Environment: BASE_SHA, PR_NUMBER, GITHUB_REPOSITORY, GITHUB_REPOSITORY_OWNER, GITHUB_RUN_ID, GH_TOKEN, GITHUB_API_URL,
GITHUB_OUTPUT, GITHUB_STEP_SUMMARY. Standard library only.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

NAME = "Gate guard"
LABEL = "gate-change-approved"
WORKFLOW = ".github/workflows/ci.yml"
GUARDED_JOBS = ("coverage", "coverage-floor", "sonar-ratings", "gate-guard", "ok")
GUARDED_FILES = ("scripts/coverage_floor.py", "scripts/sonar_ratings.py", "scripts/gate_guard.py")
GUARDED_SECTIONS = ("coverage", "pytest")  # [tool.coverage*] and [tool.pytest*] of pyproject.toml
MAX_PAGES = 10


class GuardError(ValueError):
    """A guarded fact changed without the owner's label: a real verdict."""


class ToolError(RuntimeError):
    """The guard could not read Git or GitHub: no verdict was reached."""


def git(*args: str) -> subprocess.CompletedProcess[bytes]:
    """One git command in this checkout.

    Raises:
        ToolError: git could not run.
    """
    try:
        return subprocess.run(  # noqa: S603 - fixed git arguments
            ["git", *args],  # noqa: S607 - git from PATH
            capture_output=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        message = f"git could not run: {error}"
        raise ToolError(message) from error


def show(revision: str, path: str) -> str | None:
    """The file at revision, or None when it does not exist there.

    Raises:
        ToolError: The revision is not a commit of this checkout, or git could not read the file.
    """
    if git("rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}").returncode != 0:
        message = f"{revision[:12]} is not a commit of this checkout"
        raise ToolError(message)
    if git("cat-file", "-e", f"{revision}:{path}").returncode != 0:
        return None
    done = git("show", f"{revision}:{path}")
    if done.returncode != 0:
        message = f"git show {revision[:12]}:{path} failed: {done.stderr.decode().strip()[:300]}"
        raise ToolError(message)
    return done.stdout.decode()


def job_block(workflow: str, job: str) -> str | None:
    """The text of one top-level job of the workflow, from its key to the next job, or None."""
    found = re.search(rf"(?ms)^  {re.escape(job)}:\n.*?(?=^  [A-Za-z0-9_-]+:\n|\Z)", workflow)
    return found.group(0).rstrip() if found else None


def sections(pyproject: str, name: str) -> str:
    """The [tool.NAME*] tables of pyproject.toml, in order."""
    kept, on = [], False
    for line in pyproject.splitlines():
        if line.startswith("["):
            on = bool(re.match(rf"^\[+tool\.{re.escape(name)}\b", line))
        if on:
            kept.append(line)
    return "\n".join(kept)


def facts(read: Callable[[str], str | None]) -> dict[str, str | None]:
    """Every guarded fact of one revision, by a name a reader understands."""
    workflow = read(WORKFLOW) or ""
    pyproject = read("pyproject.toml") or ""
    found: dict[str, str | None] = {f"ci.yml job {job}": job_block(workflow, job) for job in GUARDED_JOBS}
    found |= {f"file {path}": read(path) for path in GUARDED_FILES}
    found |= {f"pyproject.toml [tool.{name}*]": sections(pyproject, name) for name in GUARDED_SECTIONS}
    return found


def changed(base: Mapping[str, str | None], head: Mapping[str, str | None]) -> list[str]:
    """The names of the facts that differ, in a stable order."""
    return [name for name in base if base[name] != head.get(name)]


class GitHub:
    """Reads the pull request's labels and their events (replaced in tests)."""

    def __init__(self, env: Mapping[str, str]) -> None:
        """Bind the API base, the repository and the token."""
        self.api = env.get("GITHUB_API_URL", "https://api.github.com")
        self.repo = env.get("GITHUB_REPOSITORY", "")
        self.token = env.get("GH_TOKEN", "")

    def get(self, path: str) -> Any:  # noqa: ANN401 - whatever the API returns, checked by the caller
        """One API answer.

        Raises:
            ToolError: GitHub did not answer usably.
        """
        request = urllib.request.Request(  # noqa: S310 - the fixed https API base
            f"{self.api}/repos/{self.repo}/{path}",
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as reply:  # noqa: S310 - see above
                return json.loads(reply.read())
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            message = f"GitHub did not answer {path}: {error}"
            raise ToolError(message) from error


def approved(github: Any, pull: str, owner: str, run_id: str) -> bool:  # noqa: ANN401 - GitHub or a test double
    """True when the label is on the pull request and the owner added it after this run started.

    Raises:
        ToolError: The pull request, the run or the events can't be read.
    """
    labels = github.get(f"pulls/{pull}").get("labels", [])
    if not any(isinstance(label, dict) and label.get("name") == LABEL for label in labels):
        return False
    started = github.get(f"actions/runs/{run_id}").get("created_at")
    if not isinstance(started, str) or not started:
        message = f"run {run_id} has no start time"
        raise ToolError(message)
    for page in range(1, MAX_PAGES + 1):
        events = github.get(f"issues/{pull}/events?per_page=100&page={page}")
        if not isinstance(events, list):
            message = "the pull request's events are not a list"
            raise ToolError(message)
        for event in events:
            if (
                isinstance(event, dict)
                and event.get("event") == "labeled"
                and (event.get("label") or {}).get("name") == LABEL
                and (event.get("actor") or {}).get("login") == owner
                and str(event.get("created_at", "")) > started
            ):
                return True
        if len(events) < 100:  # noqa: PLR2004 - the page size above
            return False
    return False


def judge(env: Mapping[str, str], github: Any, notes: list[str], read_at: Callable[[str, str], str | None]) -> str:  # noqa: ANN401
    """The passing verdict, or which guarded facts changed without the owner's label.

    Raises:
        GuardError: A guarded fact changed and the owner's label is missing or older than this run.
        ToolError: An input is missing.
    """
    base, pull = env.get("BASE_SHA", ""), env.get("PR_NUMBER", "")
    if not re.fullmatch(r"[0-9a-f]{40}", base) or not pull.isdigit():
        message = "BASE_SHA and PR_NUMBER must name the pull request's base commit and number"
        raise ToolError(message)
    differ = changed(facts(lambda path: read_at(base, path)), facts(lambda path: read_at("HEAD", path)))
    notes.append(f"Compared: main at {base[:12]} with this run's merge commit.")
    if not differ:
        return f"{NAME} passed: no guarded fact changed"
    notes.extend(f"Changed: {name}" for name in differ)
    owner = env.get("GITHUB_REPOSITORY_OWNER", "")
    if owner and approved(github, pull, owner, env.get("GITHUB_RUN_ID", "")):
        notes.append(f"Approved: {owner} added the label {LABEL} after this run started.")
        return f"{NAME} passed: {len(differ)} guarded fact(s) changed, approved by the owner's label"
    message = (
        f"{len(differ)} guarded fact(s) changed ({', '.join(differ)}); the owner adds the label {LABEL} "
        "after reviewing them, then re-runs the failed jobs"
    )
    raise GuardError(message)


def publish(env: Mapping[str, str], headline: str, notes: list[str], *, failed: bool) -> None:
    """Print the verdict, annotate a failure, and hand it to CI OK and the job summary."""
    print("\n".join([headline, *notes]))
    if failed:
        print(f"::error title={NAME}::{headline}")
    if path := env.get("GITHUB_OUTPUT"):
        with Path(path).open("a", encoding="utf-8") as output:
            output.write(f"verdict={headline[:1000].replace(chr(10), ' ')}\n")
    if path := env.get("GITHUB_STEP_SUMMARY"):
        with Path(path).open("a", encoding="utf-8") as summary:
            summary.write(f"### {headline}\n\n" + "\n".join(f"- {note}" for note in notes) + "\n")


def main(
    env: Mapping[str, str] = os.environ,
    github: Any = None,  # noqa: ANN401 - GitHub or a test double
    read_at: Callable[[str, str], str | None] = show,
) -> int:
    """Judge, publish and return the exit code: 0 passed, 1 not approved, 2 tool error."""
    notes: list[str] = []
    try:
        verdict = judge(env, github or GitHub(env), notes, read_at)
    except GuardError as error:
        publish(env, f"{NAME} FAILED (not approved): {error}", notes, failed=True)
        return 1
    except (ToolError, KeyError, TypeError, AttributeError) as error:
        headline = f"{NAME} TOOL ERROR (the guard broke, nothing was judged): {type(error).__name__}: {error}"
        publish(env, headline, notes, failed=True)
        return 2
    publish(env, verdict, notes, failed=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
