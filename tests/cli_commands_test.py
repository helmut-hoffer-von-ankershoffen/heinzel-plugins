"""Command-line dispatch, publication guards, hook scoping and screenshot modes fail safely and say what to do."""

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from heinzel_plugin_tools import cli

pytestmark = pytest.mark.unit

REVISION = "a" * 40


def make_project(root, name="heinzel-harbor", version="0.2.0", extra=""):
    directory = root / "plugins" / name
    (directory / "src").mkdir(parents=True)
    (directory / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "{version}"\ndependencies = ["heinzel>=0.9.1,<0.10"]\n'
        f'[project.entry-points."heinzel.modules"]\nharbor = "{name.replace("-", "_")}"\n'
        f'[build-system]\nrequires = ["hatchling"]\n{extra}'
    )
    return directory


@pytest.fixture
def collection(tmp_path, monkeypatch):
    make_project(tmp_path)
    make_project(tmp_path, "heinzel-lighthouse", "1.0.0")
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    original = cli.projects
    # The default root is bound when the module loads, so point discovery at the disposable collection explicitly.
    monkeypatch.setattr(cli, "projects", lambda root=None: original(root or tmp_path))
    monkeypatch.delenv("PLUGIN_NAME", raising=False)
    return tmp_path


def invoke(monkeypatch, *arguments):
    monkeypatch.setattr(sys, "argv", ["hz-plugin", *arguments])
    return cli.main()


def project_in(root, name="heinzel-harbor"):
    return next(item for item in cli.projects(root) if item.name == name)


def test_discovery_reads_metadata_and_skips_directories_without_a_plugin_entry_point(collection):
    (collection / "plugins/not-a-plugin").mkdir()
    (collection / "plugins/not-a-plugin/pyproject.toml").write_text('[project]\nname="x"\nversion="1"\n')
    assert [item.name for item in cli.projects(collection)] == ["heinzel-harbor", "heinzel-lighthouse"]


def test_a_non_canonical_name_or_version_or_duplicate_is_refused(tmp_path):
    make_project(tmp_path, "heinzel-bad", "01.0")
    with pytest.raises(ValueError, match="canonical version"):
        cli.projects(tmp_path)
    (tmp_path / "plugins/heinzel-bad/pyproject.toml").write_text(
        '[project]\nname = "Heinzel_Bad"\nversion = "1.0"\n[project.entry-points."heinzel.modules"]\nb = "b"\n'
    )
    with pytest.raises(ValueError, match="canonical distribution name"):
        cli.projects(tmp_path)


def test_two_plugins_with_one_distribution_name_are_refused(tmp_path):
    make_project(tmp_path)
    (tmp_path / "pyproject.toml").write_text((tmp_path / "plugins/heinzel-harbor/pyproject.toml").read_text())
    with pytest.raises(ValueError, match="Duplicate plugin distribution names"):
        cli.projects(tmp_path)


def test_a_failing_command_stops_the_sequence_with_its_exit_status(capsys):
    with pytest.raises(SystemExit) as stopped:
        cli.run([sys.executable, "-c", "raise SystemExit(7)"])
    assert stopped.value.code == 7
    assert "✗" in capsys.readouterr().out
    cli.run([sys.executable, "-c", "pass"])
    assert "✓" in capsys.readouterr().out


def test_plan_selects_only_changed_plugins_and_everything_for_shared_tooling(collection):
    inventory = cli.projects(collection)
    only = cli.plan(["plugins/heinzel-harbor/src/x.py"], inventory, collection)
    assert [item["name"] for item in only["include"]] == ["heinzel-harbor"]
    assert only["tooling"] is False and only["core"] is False
    shared = cli.plan(["src/heinzel_plugin_tools/cli.py"], inventory, collection)
    assert shared["tooling"] is True
    assert [item["name"] for item in shared["include"]] == ["heinzel-harbor", "heinzel-lighthouse"]


def test_plan_pulls_in_consumers_of_a_provided_contract_transitively(tmp_path, monkeypatch):
    provider = '[tool.heinzel.plugin]\nprovides = ["tides"]\n'
    relay = '[tool.heinzel.plugin]\nrequires = ["tides"]\nprovides = ["alerts"]\n'
    consumer = '[tool.heinzel.plugin]\nrequires = ["alerts"]\n'
    make_project(tmp_path, "heinzel-tides", extra=provider)
    make_project(tmp_path, "heinzel-relay", extra=relay)
    make_project(tmp_path, "heinzel-pager", extra=consumer)
    make_project(tmp_path, "heinzel-unrelated")
    inventory = cli.projects(tmp_path)
    selected = cli.plan(["plugins/heinzel-tides/x.py"], inventory, tmp_path)["include"]
    assert {item["name"] for item in selected} == {"heinzel-tides", "heinzel-relay", "heinzel-pager"}
    by_contract = cli.plan([], inventory, tmp_path, contracts=["alerts"])["include"]
    assert {item["name"] for item in by_contract} == {"heinzel-pager"}


def test_plan_drops_plugins_that_do_not_support_the_candidate_core(collection, tmp_path):
    core = tmp_path / "core.whl"
    with zipfile.ZipFile(core, "w") as archive:
        archive.writestr("heinzel-0.10.0.dist-info/METADATA", "Name: heinzel\nVersion: 0.10.0\n")
    plan = cli.plan(["src/heinzel_plugin_tools/x.py"], cli.projects(collection), collection, core=str(core))
    assert plan["include"] == []


def test_list_prints_every_plugin_with_its_relative_path(collection, monkeypatch, capsys):
    assert invoke(monkeypatch, "list") == 0
    assert json.loads(capsys.readouterr().out) == [
        {"name": "heinzel-harbor", "version": "0.2.0", "path": "plugins/heinzel-harbor"},
        {"name": "heinzel-lighthouse", "version": "1.0.0", "path": "plugins/heinzel-lighthouse"},
    ]


def test_plan_command_combines_explicit_and_git_changes(collection, monkeypatch, capsys):
    monkeypatch.setattr(cli.subprocess, "check_output", lambda command, **_: "plugins/heinzel-lighthouse/a.py\n")
    assert invoke(monkeypatch, "plan", "--changed", "plugins/heinzel-harbor/b.py", "--base", "origin/main") == 0
    assert {item["name"] for item in json.loads(capsys.readouterr().out)["include"]} == {
        "heinzel-harbor",
        "heinzel-lighthouse",
    }


def test_a_base_that_looks_like_a_git_option_is_refused(collection, monkeypatch, capsys):
    with pytest.raises(SystemExit) as stopped:
        invoke(monkeypatch, "plan", "--base=--output=/etc/passwd")
    assert stopped.value.code == 2
    assert "not a Git option" in capsys.readouterr().err


def test_an_ambiguous_or_unknown_plugin_name_asks_for_one(collection, monkeypatch, capsys):
    for name in ("nonexistent", None):
        arguments = ["release-info"] + ([name] if name else [])
        with pytest.raises(SystemExit) as stopped:
            invoke(monkeypatch, *arguments)
        assert stopped.value.code == 2
    assert "Choose one plugin" in capsys.readouterr().err


def test_a_plugin_is_selected_by_short_name_or_by_its_directory(collection, monkeypatch, capsys):
    assert invoke(monkeypatch, "release-info", "harbor") == 0
    assert json.loads(capsys.readouterr().out)["tag"] == "heinzel-harbor/v0.2.0"
    monkeypatch.chdir(collection / "plugins/heinzel-lighthouse")
    assert invoke(monkeypatch, "release-info") == 0
    assert json.loads(capsys.readouterr().out)["name"] == "heinzel-lighthouse"


@pytest.mark.parametrize(
    ("command", "function"),
    [
        ("lock", "lock"),
        ("setup", "setup"),
        ("fix", "fix"),
        ("audit", "audit"),
        ("preview", "preview"),
        ("acceptance", "acceptance"),
    ],
)
def test_each_owning_command_runs_for_exactly_the_selected_plugin(collection, monkeypatch, command, function):
    seen = []
    monkeypatch.setattr(cli, function, lambda project, core, **_: seen.append((project.name, core)))
    assert invoke(monkeypatch, command, "harbor", "--core", "candidate.whl") == 0
    assert seen == [("heinzel-harbor", "candidate.whl")]


@pytest.mark.parametrize("command", ["test", "check", "check-fast"])
def test_check_commands_map_to_their_scope(collection, monkeypatch, command):
    seen = []
    monkeypatch.setattr(cli, "check", lambda project, core, **options: seen.append(options))
    invoke(monkeypatch, command, "harbor")
    assert seen == [{"tests_only": command == "test", "fast": command == "check-fast"}]


def test_preflight_checks_builds_audits_and_runs_acceptance_only_when_declared(collection, monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "check", lambda *a, **k: calls.append("check"))
    monkeypatch.setattr(cli, "build", lambda *a: calls.append("build"))
    monkeypatch.setattr(cli, "audit", lambda *a: calls.append("audit"))
    monkeypatch.setattr(cli, "acceptance", lambda *a, **k: calls.append(("acceptance", k["wheel"].name)))
    invoke(monkeypatch, "preflight", "harbor")
    assert calls == ["check", "build", "audit"]
    directory = collection / "plugins/heinzel-harbor"
    (directory / "tests/e2e").mkdir(parents=True)
    (directory / "dist").mkdir()
    (directory / "dist/heinzel_harbor-0.2.0-py3-none-any.whl").write_bytes(b"w")
    calls.clear()
    invoke(monkeypatch, "preflight", "harbor")
    assert calls[-1] == ("acceptance", "heinzel_harbor-0.2.0-py3-none-any.whl")


def test_release_checks_then_builds_while_build_only_builds(collection, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli, "check", lambda *a, **k: calls.append("check"))
    monkeypatch.setattr(cli, "build", lambda *a: calls.append("build"))
    invoke(monkeypatch, "build", "harbor")
    assert calls == ["build"]
    calls.clear()
    invoke(monkeypatch, "release", "harbor")
    assert calls == ["check", "build"]
    assert "Release: heinzel-harbor/v0.2.0" in capsys.readouterr().out


def test_check_changed_checks_only_the_plugins_the_changes_select(collection, monkeypatch):
    seen = []
    monkeypatch.setattr(cli, "check", lambda project, core, **options: seen.append((project.name, options)))
    invoke(monkeypatch, "check-changed", "--changed", "plugins/heinzel-lighthouse/x.py")
    assert seen == [("heinzel-lighthouse", {"fast": True})]


def test_new_requires_a_name_and_forwards_the_scaffold_options(collection, monkeypatch):
    with pytest.raises(SystemExit):
        invoke(monkeypatch, "new")
    seen = []
    monkeypatch.setattr(cli, "scaffold", lambda *args, **kwargs: seen.append((args, kwargs)))
    invoke(monkeypatch, "new", "quay", "--preset", "contributions", "--no-screenshots")
    assert seen == [(("quay", None, None, None, "contributions"), {"screenshots": False})]


def test_the_boundary_command_checks_imports_and_the_installed_core(collection, monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "boundaries", lambda project: calls.append("boundaries"))
    monkeypatch.setattr(cli, "validate_installed_core", lambda project: calls.append("core"))
    invoke(monkeypatch, "boundary", "harbor")
    assert calls == ["boundaries", "core"]


def test_profile_requires_a_built_core_wheel(collection, monkeypatch, capsys):
    with pytest.raises(SystemExit):
        invoke(monkeypatch, "profile")
    assert "profile needs --core with a built wheel" in capsys.readouterr().err


def test_a_command_failure_is_reported_without_a_traceback(monkeypatch, capsys):
    monkeypatch.setattr(cli, "main", lambda: (_ for _ in ()).throw(ValueError("lock is stale")))
    assert cli.entrypoint() == 1
    assert capsys.readouterr().err == "Plugin command failed: lock is stale\n"
    monkeypatch.setattr(cli, "main", lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
    assert cli.entrypoint() == 0
    assert capsys.readouterr().err == "Stopped.\n"
    monkeypatch.setattr(cli, "main", lambda: 3)
    assert cli.entrypoint() == 3


def test_an_exact_clean_source_is_required_before_verifying_a_release(monkeypatch):
    monkeypatch.setattr(cli.subprocess, "check_output", lambda *a, **k: " M plugins/heinzel-harbor/x.py\n")
    with pytest.raises(ValueError, match="clean committed sources"):
        cli.require_clean_source()
    monkeypatch.setattr(cli.subprocess, "check_output", lambda *a, **k: "\n")
    cli.require_clean_source()


@pytest.fixture
def git_state(monkeypatch):
    """Answer the four git queries of a publication in order: branch, status, local and remote revisions."""

    def prepare(branch="main", status="", local=REVISION, remote=REVISION):
        replies = iter([branch + "\n", status, local, remote])
        monkeypatch.setattr(cli.subprocess, "check_output", lambda *a, **k: next(replies))

    return prepare


@pytest.mark.parametrize("tag", ["other/v0.2.0", "heinzel-harbor/v00.2.0", "v0.2.0"])
def test_a_resume_tag_must_be_this_plugins_canonical_tag(collection, monkeypatch, tag):
    monkeypatch.setattr(cli.subprocess, "check_output", lambda *a, **k: pytest.fail("No git work for a bad tag"))
    with pytest.raises(ValueError, match="canonical existing tag"):
        cli.dispatch_publication(project_in(collection), tag)


@pytest.mark.parametrize(
    ("state", "message"),
    [
        ({"branch": "feature"}, "clean, current main"),
        ({"status": " M file\n"}, "clean, current main"),
        ({"remote": "b" * 40}, "git pull --ff-only"),
    ],
)
def test_publication_needs_clean_current_main(collection, monkeypatch, git_state, state, message):
    git_state(**state)
    monkeypatch.setattr(cli, "run", lambda *a, **k: None)
    monkeypatch.setattr(cli, "repository_private", lambda: pytest.fail("Stop before reading visibility"))
    with pytest.raises(ValueError, match=message):
        cli.dispatch_publication(project_in(collection), None)


def test_a_private_plugin_cannot_resume_a_public_tag(collection, monkeypatch, git_state):
    git_state()
    monkeypatch.setattr(cli, "run", lambda *a, **k: None)
    monkeypatch.setattr(cli, "repository_private", lambda: True)
    with pytest.raises(ValueError, match="Private GitHub releases are already published"):
        cli.dispatch_publication(project_in(collection), "heinzel-harbor/v0.2.0")


def test_resuming_a_public_release_passes_the_tag_to_the_protected_workflow(collection, monkeypatch, git_state, capsys):
    git_state()
    commands = []
    monkeypatch.setattr(cli, "run", lambda command, **_: commands.append(command))
    monkeypatch.setattr(cli, "repository_private", lambda: False)
    cli.dispatch_publication(project_in(collection), "heinzel-harbor/v0.2.0", "pypi")
    dispatch = commands[-1]
    assert "resume_tag=heinzel-harbor/v0.2.0" in dispatch and "registry=pypi" in dispatch
    assert "Dispatched the protected release workflow" in capsys.readouterr().out


def test_publication_registry_rejects_unknown_choices():
    with pytest.raises(ValueError, match="REGISTRY=github or REGISTRY=pypi"):
        cli.publication_registry(False, "npm")


def test_a_pre_push_hook_reads_the_pushed_range(monkeypatch):
    seen = []
    monkeypatch.setattr(cli.subprocess, "check_output", lambda command, **_: seen.append(command) or "a\0b\0")
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", "111")
    monkeypatch.setenv("PRE_COMMIT_TO_REF", "222")
    assert cli.hook_changes() == ["a", "b"]
    assert seen[0][:2] == ["git", "diff"] and seen[0][seen[0].index("-z") + 1 : -2] == ["111", "222"]


def test_a_new_branch_push_lists_every_plugin_file_including_deletions_it_would_hide(monkeypatch):
    seen = []
    monkeypatch.setattr(cli.subprocess, "check_output", lambda command, **_: seen.append(command) or "x\0")
    monkeypatch.delenv("PRE_COMMIT_FROM_REF", raising=False)
    monkeypatch.setenv("PRE_COMMIT_TO_REF", "222")
    assert cli.hook_changes() == ["x"]
    assert seen[0][:2] == ["git", "ls-tree"] and "222" in seen[0]


def test_a_commit_hook_reads_the_staged_index(monkeypatch):
    seen = []
    monkeypatch.setattr(cli.subprocess, "check_output", lambda command, **_: seen.append(command) or "")
    monkeypatch.delenv("PRE_COMMIT_FROM_REF", raising=False)
    monkeypatch.delenv("PRE_COMMIT_TO_REF", raising=False)
    assert cli.hook_changes() == []
    assert "--cached" in seen[0]


def test_a_pre_push_without_a_target_revision_is_a_hook_error(monkeypatch):
    monkeypatch.setenv("PRE_COMMIT_FROM_REF", "111")
    monkeypatch.delenv("PRE_COMMIT_TO_REF", raising=False)
    with pytest.raises(ValueError, match="PRE_COMMIT_TO_REF"):
        cli.hook_changes()


def test_the_git_hook_flag_scopes_checks_to_the_hooked_paths(collection, monkeypatch):
    seen = []
    monkeypatch.setattr(cli, "hook_changes", lambda: ["plugins/heinzel-harbor/x.py"])
    monkeypatch.setattr(cli, "check", lambda project, core, **_: seen.append(project.name))
    invoke(monkeypatch, "check-changed", "--git-hook")
    assert seen == ["heinzel-harbor"]


def test_repository_visibility_comes_from_the_hosting_service_when_not_declared(monkeypatch):
    monkeypatch.delenv("PLUGIN_PRIVATE", raising=False)
    monkeypatch.setattr(cli.subprocess, "check_output", lambda *a, **k: "false\n")
    assert cli.repository_private() is False
    monkeypatch.setattr(cli.subprocess, "check_output", lambda *a, **k: '"maybe"')
    assert cli.repository_private() is True


def test_a_public_audit_runs_the_pinned_scanners_against_the_installed_interpreter(project_with_env, monkeypatch):
    project, calls = project_with_env
    monkeypatch.setenv("PLUGIN_PRIVATE", "false")
    cli.audit(project, None)
    command = calls[-1]
    assert command[:3] == ["uv", "run", "--no-project"]
    assert "pip-audit==2.10.1" in command and "pip-licenses==5.5.5" in command
    assert command[-2:] == [str(project.directory / ".venv/bin/python"), "heinzel-harbor"]


def test_a_malformed_custom_audit_command_is_refused(project_with_env):
    project, calls = project_with_env
    project.metadata["tool"] = {"heinzel": {"plugin": {"audit_command": "audit --all"}}}
    with pytest.raises(ValueError, match="argument list"):
        cli.audit(project, None)
    project.metadata["tool"] = {"heinzel": {"plugin": {"audit_command": ["audit", ""]}}}
    with pytest.raises(ValueError, match="argument list"):
        cli.audit(project, None)
    assert calls == []


@pytest.fixture
def project_with_env(collection, monkeypatch):
    project = project_in(collection)
    calls = []
    monkeypatch.setattr(cli, "prepare_environment", lambda *a: project.directory / ".venv/bin/python")
    monkeypatch.setattr(cli, "run", lambda command, **_: calls.append(command))
    return project, calls


def test_a_standalone_plugin_outside_any_repository_gets_its_own_repository(collection, monkeypatch, capsys):
    project = project_in(collection)
    project.metadata["tool"] = {"heinzel": {"plugin": {"layout": "standalone"}}}
    calls = []
    monkeypatch.setattr(cli, "run", lambda command, **options: calls.append(command))
    monkeypatch.setattr(cli, "fix", lambda *a: calls.append("fix"))
    cli.setup(project, None)
    assert calls[0][:2] == ["git", "init"] and calls[1] == "fix"
    assert "Ready." in capsys.readouterr().out


def test_setup_of_an_already_locked_plugin_only_prepares_its_environment(collection, monkeypatch):
    project = project_in(collection)
    (project.directory / "plugin-lock.json").write_text("{}")
    calls = []
    monkeypatch.setattr(cli, "prepare_environment", lambda *a: calls.append("prepare"))
    monkeypatch.setattr(cli, "fix", lambda *a: pytest.fail("A locked plugin is not relocked"))
    cli.setup(project, None)
    assert calls == ["prepare"]


@pytest.mark.parametrize("name", ["Harbor", "1harbor", "har bor", "har_bor", ""])
def test_a_scaffold_name_must_be_lowercase_words(collection, monkeypatch, name):
    monkeypatch.setattr(cli, "run", lambda *a, **k: pytest.fail("Nothing runs for an invalid name"))
    with pytest.raises(ValueError, match="lowercase plugin name"):
        cli.scaffold(name, None, None, None, "minimal")


def test_a_scaffold_never_overwrites_an_existing_plugin(collection):
    with pytest.raises(ValueError, match="already exists"):
        cli.scaffold("heinzel-harbor", None, None, None, "minimal")


def test_a_scaffold_generates_in_isolated_state_and_forwards_template_and_ref(collection, monkeypatch):
    commands = []

    def generate(command, **options):
        commands.append((command, options))
        make_project(collection, "heinzel-quay")

    monkeypatch.setattr(cli, "run", generate)
    monkeypatch.setattr(cli, "lock", lambda *a: commands.append("lock"))
    monkeypatch.setattr(cli, "fix", lambda *a: commands.append("fix"))
    monkeypatch.setenv("HZ_DATA_DIR", "/personal/data")
    monkeypatch.setenv("VIRTUAL_ENV", "/unrelated")
    cli.scaffold("quay", "candidate.whl", "https://example.org/t", "v1", "contributions", screenshots=False)
    command, options = commands[0]
    assert command[command.index("--preset") + 1] == "contributions"
    assert command[command.index("--template") + 1] == "https://example.org/t"
    assert command[command.index("--ref") + 1] == "v1"
    assert "plugin_name=quay" in command and command[command.index("--from") + 1] == "candidate.whl"
    environment = options["env"]
    assert environment["HZ_PLUGINS_ENABLED"] == "false" and "VIRTUAL_ENV" not in environment
    assert environment["HZ_DATA_DIR"] != "/personal/data"
    assert commands[1:] == ["lock", "fix"]


def test_a_scaffold_whose_capture_fails_keeps_the_plugin_and_names_the_retry(collection, monkeypatch):
    monkeypatch.setattr(cli, "run", lambda *a, **k: make_project(collection, "heinzel-quay"))
    monkeypatch.setattr(cli, "lock", lambda *a: None)
    monkeypatch.setattr(cli, "fix", lambda *a: None)
    monkeypatch.setattr(cli, "capture_plugin", lambda *a, **k: 1)
    with pytest.raises(ValueError, match="hz-plugin screenshots heinzel-quay"):
        cli.scaffold("quay", None, None, None, "minimal")
    assert (collection / "plugins/heinzel-quay/docs/screenshots.toml").is_file()


def test_capture_runs_the_pinned_tool_with_only_the_requested_options(collection, monkeypatch):
    seen = []
    monkeypatch.setattr(cli.subprocess, "call", lambda command, **options: seen.append((command, options)) or 4)
    status = cli.capture_plugin(
        project_in(collection),
        "candidate.whl",
        headed=True,
        open_preview=True,
        draft_only=True,
        review_receipt=Path("receipt.json"),
        prepared_python=Path("python"),
    )
    command, options = seen[0]
    assert status == 4 and options["cwd"] == collection / "plugins/heinzel-harbor"
    assert {"--headed", "--open", "--draft", "--core", "--python", "--review-receipt"} <= set(command)
    assert "--json" not in command
    assert Path(command[command.index("--review-receipt") + 1]).is_absolute()


@pytest.mark.parametrize(
    ("stdout", "code", "expected_status", "ok"),
    [
        ('{"ok": true}', 0, 0, True),
        ('{"ok": false}', 0, 1, False),
        ('{"ok": true}', 9, 9, True),
        ("not json", 0, 1, False),
    ],
)
def test_json_capture_always_prints_a_machine_readable_report(
    collection, monkeypatch, capsys, stdout, code, expected_status, ok
):
    monkeypatch.setattr(
        cli.subprocess, "run", lambda command, **_: subprocess.CompletedProcess(command, code, stdout=stdout)
    )
    assert cli.capture_plugin(project_in(collection), None, json_output=True) == expected_status
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is ok
    if stdout == "not json":
        assert "could not start" in report["error"] and "hz-plugin screenshots heinzel-harbor" in report["next"]


def screenshots(monkeypatch, capsys, *arguments, check=False):
    status = cli.screenshot_main(list(arguments), check=check)
    captured = capsys.readouterr()
    return status, captured.out, captured.err


def test_the_screenshot_init_mode_writes_the_starter_plan(collection, monkeypatch, capsys):
    status, out, _ = screenshots(monkeypatch, capsys, "harbor", "--init", "--json")
    assert status == 0
    result = json.loads(out)
    assert result["ok"] is True and Path(result["plan"]).is_file()
    assert result["next"] == "hz-plugin screenshots heinzel-harbor"


def test_screenshot_modes_are_mutually_exclusive(collection, monkeypatch, capsys):
    status, out, _ = screenshots(monkeypatch, capsys, "harbor", "--init", "--check", "--json")
    assert status == 1
    assert "Choose one screenshot mode" in json.loads(out)["error"]
    status, _, err = screenshots(monkeypatch, capsys, "harbor", "--draft", "--review-receipt", "r.json")
    assert status == 1 and "Choose one screenshot mode" in err


def test_a_screenshot_command_without_a_unique_plugin_lists_the_choices(collection, monkeypatch, capsys):
    status, _, err = screenshots(monkeypatch, capsys, "missing")
    assert status == 1
    assert "heinzel-harbor, heinzel-lighthouse" in err


def test_the_screenshot_check_mode_reports_freshness_offline(collection, monkeypatch, capsys):
    monkeypatch.setattr(cli, "check_screenshots", lambda project: {"ok": True})
    status, out, _ = screenshots(monkeypatch, capsys, "harbor", check=True)
    assert status == 0 and out == "✓ heinzel-harbor: screenshots are fresh\n"
    monkeypatch.setattr(cli, "check_screenshots", lambda project: (_ for _ in ()).throw(ValueError("stale gallery")))
    status, out, err = screenshots(monkeypatch, capsys, "harbor", "--check")
    assert status == 1 and out == "" and err.startswith("Screenshot check failed:")


def test_the_screenshot_plan_mode_asks_for_a_fresh_definition(collection, monkeypatch, capsys):
    from heinzel_plugin_tools import planning

    seen = []
    monkeypatch.setattr(planning, "ensure_definition", lambda directory, refresh: seen.append((directory, refresh)))
    status, out, _ = screenshots(monkeypatch, capsys, "harbor", "--plan", "--json")
    assert status == 0 and seen == [(collection / "plugins/heinzel-harbor", True)]
    assert json.loads(out)["next"] == "hz-plugin screenshots heinzel-harbor --open"


def test_a_screenshot_capture_hands_over_to_the_capture_tool(collection, monkeypatch, capsys):
    seen = []
    monkeypatch.setattr(
        cli, "capture_plugin", lambda project, core, **options: seen.append((project.name, options)) or 0
    )
    assert screenshots(monkeypatch, capsys, "harbor", "--draft", "--headed")[0] == 0
    assert seen[0][0] == "heinzel-harbor" and seen[0][1]["draft_only"] and seen[0][1]["headed"]


def test_main_routes_screenshot_commands_to_their_own_parser(monkeypatch):
    seen = []
    monkeypatch.setattr(cli, "screenshot_main", lambda arguments, check=False: seen.append((arguments, check)) or 0)
    assert invoke(monkeypatch, "screenshots", "harbor", "--json") == 0
    assert invoke(monkeypatch, "screenshots-check") == 0
    assert seen == [(["harbor", "--json"], False), ([], True)]


def write_source(project, text, name="module.py"):
    package = project.directory / "src/heinzel_harbor"
    package.mkdir(exist_ok=True)
    (package / name).write_text(text)


def test_a_plugin_may_import_the_public_sdk_and_itself(collection):
    project = project_in(collection)
    write_source(project, "import json\nfrom heinzel.kernel import Module\nfrom heinzel_harbor import helpers\n")
    cli.boundaries(project)


@pytest.mark.parametrize(
    "statement",
    [
        "from heinzel.modules import registry",
        "import heinzel.heads.web",
        "from heinzel.kernel._internal import secret",
        "import heinzel_lighthouse",
        "from heinzel_lighthouse.beam import shine",
    ],
)
def test_private_core_and_sibling_plugin_imports_are_refused_with_their_location(collection, statement):
    project = project_in(collection)
    write_source(project, f"x = 1\n{statement}\n")
    with pytest.raises(ValueError, match=r"module\.py:2: consume a public contract instead of"):
        cli.boundaries(project)


def test_a_plugin_cannot_depend_on_a_sibling_distribution(collection):
    project = project_in(collection)
    project.metadata["project"]["dependencies"].append("heinzel-lighthouse>=1")
    with pytest.raises(ValueError, match="require a public contract, not a sibling plugin distribution"):
        cli.boundaries(project)


def test_an_unrecognized_heinzel_prefixed_dependency_is_treated_as_a_sibling(collection):
    project = project_in(collection)
    project.metadata["project"]["dependencies"].append("heinzel-never-installed")
    with pytest.raises(ValueError, match="sibling plugin distribution"):
        cli.boundaries(project)
