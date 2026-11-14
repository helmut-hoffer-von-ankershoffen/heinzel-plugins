import os

import pytest

from heinzel_atlassian import AtlassianSettings
from heinzel_atlassian._acli import environment, executable, parse_version, run_environment, where_looked

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("text", "version"),
    [
        ("acli version 1.3.39-stable\n", (1, 3, 39)),
        ("acli version v2.0.1\n", (2, 0, 1)),
        ("something else\n", None),
        ("", None),
    ],
)
def test_the_version_is_read_from_acli_version(text, version):
    assert parse_version(text) == version


def test_relative_path_entries_are_left_out_of_the_child_path():
    assert environment({"PATH": f"bin{os.pathsep}/usr/bin{os.pathsep}{os.pathsep}.{os.pathsep}/opt/bin"})["PATH"] == (
        f"/usr/bin{os.pathsep}/opt/bin"
    )


def test_only_allowlisted_variables_and_no_colour_reach_acli():
    source = {
        "PATH": "/usr/bin",
        "HOME": "/home/wilma",
        "LANG": "en_US.UTF-8",
        "LC_ALL": "C",
        "ACLI_LOG_FILE": "/home/wilma/acli.log",
        "https_proxy": "http://proxy.acme.example:3128",
        "NO_PROXY": "localhost",
        "HZ_CREDENTIAL_ATLASSIAN_ATLASSIAN_TOKEN": "fake-token-never-passed-on",
        "GH_TOKEN": "fake-token-of-another-vendor",
        "AWS_SECRET_ACCESS_KEY": "fake-secret",
        "PYTHONPATH": "/somewhere",
    }
    assert environment(source) == {
        "PATH": "/usr/bin",
        "HOME": "/home/wilma",
        "LANG": "en_US.UTF-8",
        "LC_ALL": "C",
        "ACLI_LOG_FILE": "/home/wilma/acli.log",
        "https_proxy": "http://proxy.acme.example:3128",
        "NO_PROXY": "localhost",
        "NO_COLOR": "1",
    }


def test_acli_runs_with_its_own_directory_and_homebrew_after_path(no_homebrew):
    env = run_environment("/opt/tools/bin/acli", {"PATH": f"/usr/bin{os.pathsep}relative{os.pathsep}/bin"})
    assert env["PATH"] == os.pathsep.join(["/usr/bin", "/bin", "/opt/tools/bin", *no_homebrew])


def test_a_linked_acli_runs_with_both_its_directories(no_homebrew, tmp_path):
    target = tmp_path / "Cellar" / "acli" / "bin" / "acli"
    target.parent.mkdir(parents=True)
    target.write_text("", encoding="utf-8")
    link = tmp_path / "bin" / "acli"
    link.parent.mkdir()
    link.symlink_to(target)
    env = run_environment(str(link), {"PATH": "/usr/bin"})
    assert env["PATH"] == os.pathsep.join(["/usr/bin", str(link.parent), str(target.resolve().parent), *no_homebrew])


def test_a_missing_acli_says_where_heinzel_looked(no_homebrew, monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    assert executable(AtlassianSettings()) is None
    assert where_looked() == f"on PATH and in {no_homebrew[0]} and {no_homebrew[1]}"
