"""Narrow immutable-input plans for the reviewed consent and release-retry updates.

This planner is inert until a separately trusted hook launcher invokes it. It is
not authority to load itself from the proposed branch or to bypass stock hooks.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

ANCHOR = "f94dbc0d5ecf18b605ed917317d91eb5144eec4f"
POLICY_PATHS = frozenset(
    {
        ".pre-commit-config.yaml",
        "Makefile",
        "README.md",
        "scripts/focused_dispatch.py",
        "scripts/focused_guard_install.py",
        "scripts/focused_hook.py",
        "scripts/focused_materialize.py",
        "scripts/focused_push_guard.py",
        "scripts/focused_trust.py",
        "src/heinzel_plugin_tools/cli.py",
        "src/heinzel_plugin_tools/focused_policy.py",
        "tests/cli_commands_test.py",
        "tests/focused_hook_test.py",
        "tests/focused_trust_test.py",
        "tests/focused_policy_test.py",
        "tests/focused_dispatch_test.py",
        "tests/focused_push_guard_test.py",
        "tests/focused_guard_install_test.py",
        "tests/focused_materialize_test.py",
    }
)
PLANS = {
    "39c5bcd10f675c63df1b8c1e5892a4fd3a89006f": (
        "c4cf2a3e00856f227c34cf58d141a7a2c9c0719c",
        (
            "tests/cli_commands_test.py",
            "tests/cli_environment_test.py",
            "tests/authoring_test.py",
            "tests/fast_integration_test.py",
            "tests/focused_hook_test.py",
            "tests/focused_trust_test.py",
            "tests/focused_policy_test.py",
            "tests/focused_dispatch_test.py",
            "tests/focused_push_guard_test.py",
            "tests/focused_guard_install_test.py",
            "tests/focused_materialize_test.py",
            "plugins/heinzel-google/tests/unit/setup_test.py",
            "plugins/heinzel-google/tests/unit/token_exchange_test.py",
            "plugins/heinzel-google/tests/unit/document_write_contract_test.py",
            "plugins/heinzel-google/tests/unit/contract_test.py",
            "plugins/heinzel-google/tests/integration/cli_test.py",
            "plugins/heinzel-zoom/tests/unit/contract_test.py",
            "plugins/heinzel-zoom/tests/integration/cli_test.py",
            "plugins/heinzel-zoom/tests/integration/connector_test.py",
            "plugins/heinzel-zoom/tests/integration/capability_test.py",
        ),
    ),
    "e30673ef9cc8cc98de36a418e3b5a6553d5dc416": (
        "b138410ef5ad39a890e2e22630a34cc7095d4859",
        (
            "tests/cli_commands_test.py",
            "tests/cli_environment_test.py",
            "tests/authoring_test.py",
            "tests/fast_integration_test.py",
            "tests/focused_hook_test.py",
            "tests/focused_trust_test.py",
            "tests/focused_policy_test.py",
            "tests/focused_dispatch_test.py",
            "tests/focused_push_guard_test.py",
            "tests/focused_guard_install_test.py",
            "tests/focused_materialize_test.py",
            "tests/download_retry_test.py",
            "tests/tooling_test.py",
            "tests/compose_test.py",
            "tests/next_app_test.py",
            "tests/next_app_propagation_test.py",
            "tests/publish_test.py",
            "tests/publish_restore_test.py",
            "tests/workflow_test.py",
            "tests/browser_bootstrap_ci_test.py",
            "tests/capture_test.py",
            "tests/historical_gallery_test.py",
            "tests/links_standards_test.py",
            "plugins/heinzel-atlassian/tests/integration/acli_test.py",
            "plugins/heinzel-atlassian/tests/integration/authorization_test.py",
            "plugins/heinzel-atlassian/tests/integration/capability_test.py",
            "plugins/heinzel-atlassian/tests/integration/cli_test.py",
            "plugins/heinzel-atlassian/tests/integration/connector_test.py",
            "plugins/heinzel-atlassian/tests/integration/work_test.py",
            "plugins/heinzel-atlassian/tests/unit/acli_test.py",
            "plugins/heinzel-atlassian/tests/unit/client_test.py",
            "plugins/heinzel-atlassian/tests/unit/confluence_test.py",
            "plugins/heinzel-atlassian/tests/unit/contract_test.py",
            "plugins/heinzel-atlassian/tests/unit/drafts_test.py",
            "plugins/heinzel-atlassian/tests/unit/jira_test.py",
            "plugins/heinzel-atlassian/tests/unit/service_test.py",
            "plugins/heinzel-atlassian/tests/unit/status_test.py",
            "plugins/heinzel-atlassian/tests/unit/untrusted_test.py",
            "plugins/heinzel-atlassian/tests/unit/work_test.py",
            "plugins/heinzel-issues/tests/integration/beads_test.py",
            "plugins/heinzel-issues/tests/integration/heads_test.py",
            "plugins/heinzel-issues/tests/integration/tracker_test.py",
            "plugins/heinzel-issues/tests/unit/issues_test.py",
            "plugins/heinzel-issues/tests/unit/view_test.py",
            "plugins/heinzel-tailscale/tests/integration/cli_test.py",
            "plugins/heinzel-tailscale/tests/integration/host_test.py",
            "plugins/heinzel-tailscale/tests/integration/lock_test.py",
            "plugins/heinzel-tailscale/tests/integration/origin_policy_test.py",
            "plugins/heinzel-tailscale/tests/unit/cli_test.py",
            "plugins/heinzel-tailscale/tests/unit/localapi_test.py",
            "plugins/heinzel-tailscale/tests/unit/mapping_test.py",
            "plugins/heinzel-tailscale/tests/unit/readiness_test.py",
            "plugins/heinzel-tailscale/tests/unit/status_test.py",
            "plugins/heinzel-clock/tests/clock_test.py",
            "plugins/heinzel-clock/tests/integration/setup_host_test.py",
            "plugins/heinzel-clock/web/src/ClockPanel.test.tsx",
        ),
    ),
}


def _env() -> dict[str, str]:
    # Hooks may inherit a caller's index, object store or replacement configuration.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    return env


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "--no-replace-objects", *args], cwd=repo, env=_env(), text=True, timeout=30)


def _ancestor(repo: Path, base: str, head: str) -> bool:
    return (
        subprocess.run(
            ["git", "--no-replace-objects", "merge-base", "--is-ancestor", base, head],
            cwd=repo,
            env=_env(),
            check=False,
            timeout=30,
        ).returncode
        == 0
    )


def _changed(repo: Path, old: str, new: str) -> set[str]:
    return set(filter(None, _git(repo, "diff", "--no-renames", "--name-only", "-z", old, new, "--").split("\0")))


def _entry(repo: Path, rev: str, path: str) -> str:
    return _git(repo, "ls-tree", "-z", rev, "--", path)


@dataclass(frozen=True)
class CheckPlan:
    tooling: tuple[str, ...]
    owners: tuple[tuple[str, tuple[str, ...]], ...]
    frontend: tuple[tuple[str, str], ...]
    guards: tuple[str, ...]


def plan(repo: Path, old: str, new: str, trusted_policy: str) -> CheckPlan:
    """Return a fixed plan, only when trusted launcher and all frozen inputs match.

    `trusted_policy` must be fixed by an independently trusted launcher. Accepting
    a caller-provided value here without such a launcher does not confer trust.
    """
    if old not in PLANS:
        raise ValueError("unknown original PR head")
    candidate, tests = PLANS[old]
    for sha in (old, new, trusted_policy):
        if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
            raise ValueError("expected full immutable commit ids")
    if _git(repo, "rev-parse", "HEAD").strip() != new or _git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("expected clean exact checkout")
    if not all(_ancestor(repo, base, new) for base in (old, candidate, ANCHOR, trusted_policy)):
        raise ValueError("candidate, protected baseline and policy must be ancestors")
    # The trusted policy must be independently anchored to the protected baseline.
    if not _ancestor(repo, ANCHOR, trusted_policy):
        raise ValueError("untrusted policy ancestry")
    modified = _changed(repo, candidate, new)
    if modified - POLICY_PATHS:
        raise ValueError("unknown change after frozen candidate")
    for path in POLICY_PATHS:
        if _entry(repo, trusted_policy, path) != _entry(repo, new, path):
            raise ValueError("policy bytes differ from trusted policy")
    # For every inherited pushed path, matching its anchor entry includes file mode
    # and deletion. A path touching the reviewed contribution remains contribution.
    contribution = _changed(repo, ANCHOR, candidate)
    for path in _changed(repo, old, new) - contribution - POLICY_PATHS:
        if _entry(repo, ANCHOR, path) != _entry(repo, new, path):
            raise ValueError("inherited path differs from protected baseline")
    for path in tests:
        if not _entry(repo, new, path).startswith(("100644 blob ", "100755 blob ")):
            raise ValueError("required focused test is missing or not a regular blob")
        if path not in POLICY_PATHS and _entry(repo, new, path) != _entry(repo, candidate, path):
            raise ValueError("required focused test differs from frozen candidate")
    grouped: dict[str, list[str]] = {}
    for path in tests:
        if path.startswith("plugins/") and "/tests/" in path:
            _, owner, relative = path.split("/", 2)
            grouped.setdefault(owner, []).append(relative)
    frontend = tuple((path.split("/")[1], path) for path in tests if path.startswith("plugins/") and "/web/" in path)
    return CheckPlan(
        tooling=tuple(path for path in tests if path.startswith("tests/")),
        owners=tuple((owner, tuple(paths)) for owner, paths in sorted(grouped.items())),
        frontend=frontend,
        guards=(
            "confidentiality",
            "root-ruff-check",
            "root-ruff-format",
            "actionlint",
            "zizmor-offline",
            "vendor",
            "owner-boundary",
            "owner-ruff-check",
            "owner-ruff-format",
            "gallery-privacy",
            "frontend-typecheck",
        ),
    )
