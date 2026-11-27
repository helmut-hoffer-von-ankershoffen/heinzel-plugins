"""Narrow immutable-input plans for the reviewed consent and release-retry updates.

This planner is inert until a separately trusted hook launcher invokes it. It is
not authority to load itself from the proposed branch or to bypass stock hooks.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

_T_CLI_COMMANDS = "tests/cli_commands_test.py"
_T_TOOLING = "tests/tooling_test.py"
_T_FOCUSED_HOOK = "tests/focused_hook_test.py"
_T_FOCUSED_TRUST = "tests/focused_trust_test.py"
_T_FOCUSED_POLICY = "tests/focused_policy_test.py"
_T_FOCUSED_DISPATCH = "tests/focused_dispatch_test.py"
_T_FOCUSED_PUSH_GUARD = "tests/focused_push_guard_test.py"
_T_FOCUSED_GUARD_INSTALL = "tests/focused_guard_install_test.py"
_T_FOCUSED_MATERIALIZE = "tests/focused_materialize_test.py"
_T_CLI_ENVIRONMENT = "tests/cli_environment_test.py"
_T_AUTHORING = "tests/authoring_test.py"
_T_FAST_INTEGRATION = "tests/fast_integration_test.py"
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
        _T_CLI_COMMANDS,
        _T_TOOLING,
        _T_FOCUSED_HOOK,
        _T_FOCUSED_TRUST,
        _T_FOCUSED_POLICY,
        _T_FOCUSED_DISPATCH,
        _T_FOCUSED_PUSH_GUARD,
        _T_FOCUSED_GUARD_INSTALL,
        _T_FOCUSED_MATERIALIZE,
    }
)
GALLERY_ORIGINAL = "330dc9bc521c9b59990604fa3bc9e74342de0886"
GALLERY_HOSTED_HEAD = "d04153aa78ff1692f81a291b251c527ab86dc476"
GALLERY_CAPTURE_FIXTURE = "tests/capture_run_test.py"
GALLERY_RUNTIME_BLOBS = {
    ".github/workflows/ci.yml": "98242894cc754d366a8f393bac1a566c5ea30cea",
    ".python-version": "93a848f9688291c7b2172cf99f133675225ad282",
    "pyproject.toml": "5d9f9ab9094354dd2c47897ed72077006c85e7a1",
    "uv.lock": "ac5b39f6beda2983080b1e6b14144b2fc19c5f72",
}
GALLERY_FORWARD_BLOBS = {
    "plugins/heinzel-clock/pyproject.toml": "62288fcdd504267e9c63701ca31fc8ad126e230c",
    "plugins/heinzel-clock/CHANGELOG.md": "21a4a42fa506cbcbcfd62de403c739f7576f4e64",
    "plugins/heinzel-weather/pyproject.toml": "dc158e333037afb78a1bb4719dd5f4cc9ea60a0f",
    "plugins/heinzel-weather/CHANGELOG.md": "32be23b91dba11aef4cdeeab9a714e8b8cde0d09",
    GALLERY_CAPTURE_FIXTURE: "a1a8756e07e145f32bd00f2685e043578b7737a2",
}
GALLERY_POLICY_PATHS = frozenset(
    {
        *GALLERY_RUNTIME_BLOBS,
        "scripts/focused_dispatch.py",
        "src/heinzel_plugin_tools/focused_policy.py",
        _T_FOCUSED_DISPATCH,
        _T_FOCUSED_POLICY,
    }
)
PLANS = {
    GALLERY_ORIGINAL: (
        "272ced40248432c2d5e91acf2e088859d0bac1d0",
        (
            "tests/capture_bootstrap_test.py",
            "tests/capture_fixture_origins_test.py",
            "tests/capture_test.py",
            "tests/cli_environment_test.py",
            "tests/cli_commands_test.py",
            "tests/presentation_test.py",
            "tests/privacy_test.py",
            "tests/workflow_test.py",
            "tests/gallery_index_guard_test.py",
            "tests/focused_push_guard_test.py",
            "tests/focused_policy_test.py",
            "tests/focused_dispatch_test.py",
            "tests/focused_materialize_test.py",
            "tests/focused_trust_test.py",
            "tests/focused_guard_install_test.py",
            "tests/focused_hook_test.py",
            "plugins/heinzel-atlassian/tests/unit/contract_test.py",
            "plugins/heinzel-clock/tests/clock_test.py",
            "plugins/heinzel-example/tests/contributions_test.py",
            "plugins/heinzel-github/tests/unit/release_feed_test.py",
            "plugins/heinzel-github/tests/unit/contract_test.py",
            "plugins/heinzel-google/tests/unit/setup_test.py",
            "plugins/heinzel-google/tests/unit/sign_in_test.py",
            "plugins/heinzel-google/tests/unit/gws_test.py",
            "plugins/heinzel-google/tests/unit/screenshot_fixture_test.py",
            "plugins/heinzel-google/tests/integration/cli_test.py",
            "plugins/heinzel-google/tests/integration/runner_test.py",
            "plugins/heinzel-issues/tests/unit/view_test.py",
            "plugins/heinzel-resource/tests/unit/resources_test.py",
            "plugins/heinzel-slack/tests/integration/cli_process_test.py",
            "plugins/heinzel-tailscale/tests/unit/status_test.py",
            "plugins/heinzel-tailscale/tests/unit/readiness_test.py",
            "plugins/heinzel-tailscale/tests/integration/host_test.py",
            "plugins/heinzel-theme/tests/unit/content_test.py",
            "plugins/heinzel-weather/tests/integration/heads_test.py",
            "plugins/heinzel-weather/tests/unit/service_test.py",
            "plugins/heinzel-weather/tests/unit/screenshot_fixture_test.py",
            "plugins/heinzel-zoom/tests/unit/contract_test.py",
            "plugins/heinzel-clock/web/src/ClockPanel.test.tsx",
        ),
    ),
    "39c5bcd10f675c63df1b8c1e5892a4fd3a89006f": (
        "c4cf2a3e00856f227c34cf58d141a7a2c9c0719c",
        (
            _T_CLI_COMMANDS,
            _T_TOOLING,
            _T_CLI_ENVIRONMENT,
            _T_AUTHORING,
            _T_FAST_INTEGRATION,
            _T_FOCUSED_HOOK,
            _T_FOCUSED_TRUST,
            _T_FOCUSED_POLICY,
            _T_FOCUSED_DISPATCH,
            _T_FOCUSED_PUSH_GUARD,
            _T_FOCUSED_GUARD_INSTALL,
            _T_FOCUSED_MATERIALIZE,
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
            _T_CLI_COMMANDS,
            _T_CLI_ENVIRONMENT,
            _T_AUTHORING,
            _T_FAST_INTEGRATION,
            _T_FOCUSED_HOOK,
            _T_FOCUSED_TRUST,
            _T_FOCUSED_POLICY,
            _T_FOCUSED_DISPATCH,
            _T_FOCUSED_PUSH_GUARD,
            _T_FOCUSED_GUARD_INSTALL,
            _T_FOCUSED_MATERIALIZE,
            "tests/download_retry_test.py",
            _T_TOOLING,
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


def _check_ancestry(repo: Path, old: str, new: str, candidate: str, trusted_policy: str) -> None:
    if _git(repo, "rev-parse", "HEAD").strip() != new or _git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("expected clean exact checkout")
    if not all(_ancestor(repo, base, new) for base in (old, candidate, ANCHOR, trusted_policy)):
        raise ValueError("candidate, protected baseline and policy must be ancestors")
    # The trusted policy must be independently anchored to the protected baseline.
    if not _ancestor(repo, ANCHOR, trusted_policy):
        raise ValueError("untrusted policy ancestry")


def _check_frozen_inputs(
    repo: Path, old: str, new: str, candidate: str, trusted_policy: str, policy_paths: frozenset[str]
) -> None:
    if _changed(repo, candidate, new) - policy_paths:
        raise ValueError("unknown change after frozen candidate")
    for path in policy_paths:
        if _entry(repo, trusted_policy, path) != _entry(repo, new, path):
            raise ValueError("policy bytes differ from trusted policy")
    # For every inherited pushed path, matching its anchor entry includes file mode
    # and deletion. A path touching the reviewed contribution remains contribution.
    contribution = _changed(repo, ANCHOR, candidate)
    for path in _changed(repo, old, new) - contribution - policy_paths:
        if _entry(repo, ANCHOR, path) != _entry(repo, new, path):
            raise ValueError("inherited path differs from protected baseline")


def _check_required_tests(
    repo: Path, new: str, candidate: str, tests: tuple[str, ...], policy_paths: frozenset[str]
) -> None:
    for path in tests:
        if not _entry(repo, new, path).startswith(("100644 blob ", "100755 blob ")):
            raise ValueError("required focused test is missing or not a regular blob")
        if path not in policy_paths and _entry(repo, new, path) != _entry(repo, candidate, path):
            raise ValueError("required focused test differs from frozen candidate")


def plan(repo: Path, old: str, new: str, trusted_policy: str) -> CheckPlan:
    """Return a fixed plan, only when trusted launcher and all frozen inputs match.

    `trusted_policy` must be fixed by an independently trusted launcher. Accepting
    a caller-provided value here without such a launcher does not confer trust.
    """
    hosted_fix = old == GALLERY_HOSTED_HEAD
    plan_key = GALLERY_ORIGINAL if hosted_fix else old
    if plan_key not in PLANS:
        raise ValueError("unknown original PR head")
    candidate, tests = PLANS[plan_key]
    for sha in (old, new, trusted_policy):
        if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
            raise ValueError("expected full immutable commit ids")
    gallery = plan_key == GALLERY_ORIGINAL
    if gallery and (
        new != trusted_policy
        or _git(repo, "show", "-s", "--format=%P", new).strip() != (old if hosted_fix else candidate)
    ):
        raise ValueError("gallery push requires the pinned, direct policy successor")
    policy_paths = GALLERY_POLICY_PATHS if gallery else POLICY_PATHS
    if hosted_fix:
        policy_paths = policy_paths.union(GALLERY_FORWARD_BLOBS)
        tests = (*tests, GALLERY_CAPTURE_FIXTURE)
    _check_ancestry(repo, old, new, candidate, trusted_policy)
    _check_frozen_inputs(repo, old, new, candidate, trusted_policy, policy_paths)
    blobs = GALLERY_RUNTIME_BLOBS if gallery else {}
    if hosted_fix:
        blobs = blobs | GALLERY_FORWARD_BLOBS
    for path, blob in blobs.items():
        if _entry(repo, new, path) != f"100644 blob {blob}\t{path}\0":
            raise ValueError(f"gallery runtime input differs from its reviewed blob: {path}")
    _check_required_tests(repo, new, candidate, tests, policy_paths)
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
