"""A resolved main merge must survive the author's ordinary PR command and push."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

PR_SETTINGS = {"BODY", "BODY_FILE", "DRAFT", "NO_PREFLIGHT", "PLUGIN_CORE", "PLUGIN_NAME"}
"""What scripts/pr.sh reads from its environment; a developer's own NO_PREFLIGHT=1 must not change what is tested."""


@pytest.mark.parametrize("selected", [False, True])
@pytest.mark.parametrize("conflict", [False, True])
@pytest.mark.parametrize("inherited_git", [False, True])
def test_pr_preserves_pushed_ancestry_and_a_resolved_main_merge(
    tmp_path, monkeypatch, conflict, inherited_git, selected
):
    git = shutil.which("git")
    bash = shutil.which("bash")
    make = shutil.which("make")
    assert git and bash and make
    foreign = tmp_path / "foreign.git"
    foreign.mkdir()
    index = foreign / "index"
    index.write_bytes(b"foreign index must stay untouched")
    (foreign / "HEAD").write_text("ref: refs/heads/protected\n")
    if inherited_git:
        monkeypatch.setenv("GIT_DIR", str(foreign))
        monkeypatch.setenv("GIT_INDEX_FILE", str(index))
        monkeypatch.setenv("GIT_WORK_TREE", str(foreign))
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    binaries = tmp_path / "bin"
    binaries.mkdir()
    marker = tmp_path / "executed"
    core = str(tmp_path / f"a wheel $(touch {marker}) `touch {marker}`.whl")
    probe = tmp_path / "preflight.txt"
    overrides = tmp_path / "preflight.mk"
    overrides.write_text("tooling-check policies secrets:\n\t@:\n")
    makefile = Path(__file__).parents[1] / "Makefile"
    for name in ("uv", "make", "gh"):
        stub = binaries / name
        stub.write_text(
            "#!/bin/sh\n"
            + (
                'test "$2" != create || echo https://github.com/example/plugins/pull/1\n'
                if name == "gh"
                else f'exec "{make}" -f "{makefile}" -f "{overrides}" "$@"\n'
                if name == "make"
                else (
                    'while [ "$#" -gt 0 ] && [ "$1" != hz-plugin ]; do shift; done\n'
                    'if [ "${1:-}" = hz-plugin ] && [ "${2:-}" = preflight ]; then\n'
                    'printf "%s\n%s\n" "$PLUGIN_NAME" "$PLUGIN_CORE" > "$PROBE"\nfi\n'
                )
            )
        )
        stub.chmod(0o755)
    environment = {
        **{key: value for key, value in os.environ.items() if not key.startswith("GIT_") and key not in PR_SETTINGS},
        "PATH": str(binaries) + os.pathsep + os.environ["PATH"],
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "PLUGIN_NAME": "harbor" if selected else "",
        "PLUGIN_CORE": core if selected else "",
        "PROBE": str(probe),
        **{
            f"GIT_{role}_{key}": value
            for role in ("AUTHOR", "COMMITTER")
            for key, value in {"NAME": "Ada Example", "EMAIL": "ada@example.test"}.items()
        },
    }

    def run(*args, cwd=work, check=True):
        return subprocess.run(  # noqa: S603 - resolved executables, disposable repositories and fixed test arguments
            args, cwd=cwd, env=environment, text=True, capture_output=True, check=check, timeout=30
        )

    run(git, "init", "--quiet", "--bare", "--initial-branch=main", str(origin), cwd=tmp_path)
    run(git, "clone", "--quiet", str(origin), str(work), cwd=tmp_path)

    def commit(path, content):
        (work / path).write_text(content)
        run(git, "add", path)
        run(git, "commit", "--quiet", "-m", "feat: change example")

    commit("base", "base\n")
    run(git, "push", "--quiet", "origin", "main")
    run(git, "switch", "--quiet", "-c", "feature")
    commit("widget", "widget\n")
    run(git, "push", "--quiet", "origin", "feature")
    commit("base", "feature\n")
    run(git, "switch", "--quiet", "main")
    commit("base" if conflict else "gear", "main\n")
    run(git, "push", "--quiet", "origin", "main")
    run(git, "switch", "--quiet", "feature")
    result = run(git, "merge", "--no-edit", "main", check=False)
    assert result.returncode == (1 if conflict else 0)
    if conflict:
        commit("base", "feature and main\n")
    revision = run(git, "rev-parse", "HEAD").stdout.strip()
    script = tmp_path / "scripts/pr.sh"
    script.parent.mkdir()
    shutil.copyfile(Path(__file__).parents[1] / "scripts/pr.sh", script)
    result = run(bash, str(script), "feat: add widget", check=False)
    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    if selected:
        assert probe.read_text().splitlines() == ["harbor", core]
    else:
        assert not probe.exists()
    assert run(git, "ls-remote", "origin", "refs/heads/feature").stdout.split()[0] == revision
    assert run(git, "status", "--porcelain").stdout == ""
    assert (work / "base").read_text() == ("feature and main\n" if conflict else "feature\n")
    assert index.read_bytes() == b"foreign index must stay untouched"
    assert (foreign / "HEAD").read_text() == "ref: refs/heads/protected\n"
