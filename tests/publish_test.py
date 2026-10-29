"""A retry never moves an existing tag or overwrites differently identified published artifacts."""

import hashlib
import subprocess

import pytest

from heinzel_plugin_tools import publishing as publisher

pytestmark = pytest.mark.unit

REVISION = "a" * 40
REPOSITORY = "example/plugins"


@pytest.mark.parametrize("tag", ["heinzel-resource/v0.1.0", "app-v0.9.0"])
def test_a_preexisting_wrong_tag_blocks_both_plugin_and_composition_publication(tmp_path, monkeypatch, tag):
    wheel = tmp_path / "artifact.whl"
    wheel.write_bytes(b"checked artifact")
    monkeypatch.setattr(publisher, "api", lambda *a, **k: {"object": {"type": "commit", "sha": "b" * 40}})
    with pytest.raises(ValueError, match="built commit"):
        publisher.publish(REPOSITORY, tag, REVISION, [wheel], pypi=True)


def test_annotated_tags_are_peeled_before_comparison(monkeypatch):
    calls = []

    def api(path, **_):
        calls.append(path)
        return (
            {"object": {"type": "commit", "sha": REVISION}}
            if "/git/tags/" in path
            else {"object": {"type": "tag", "sha": "c" * 40}}
        )

    monkeypatch.setattr(publisher, "api", api)
    publisher.exact_tag(REPOSITORY, "plugin/v1.0.0", REVISION)
    assert calls[-1].endswith("/git/tags/" + "c" * 40)


def test_missing_tag_is_created_at_exact_build_revision(monkeypatch):
    calls = []

    def api(path, data=None, **_):
        calls.append((path, data))
        if len(calls) == 1:
            return None
        return {"object": {"type": "commit", "sha": REVISION}}

    monkeypatch.setattr(publisher, "api", api)
    publisher.exact_tag(REPOSITORY, "plugin/v1.0.0", REVISION)
    assert calls[1][1] == {"ref": "refs/tags/plugin/v1.0.0", "sha": REVISION}


def test_partial_pypi_failure_is_resumable_without_changing_tag_or_replacing_assets(tmp_path, monkeypatch):
    wheel = tmp_path / "artifact.whl"
    wheel.write_bytes(b"checked artifact")
    asset = {"name": wheel.name, "digest": "sha256:" + hashlib.sha256(wheel.read_bytes()).hexdigest()}
    release = None
    calls = []
    failed = False

    def api(path, data=None, method="POST", **_):
        nonlocal release
        if "/git/ref/" in path:
            return {"object": {"type": "commit", "sha": REVISION}}
        if data is not None and method == "PATCH":
            assert release["assets"] == [asset], "publish only after verifying every upload"
            release["draft"] = data["draft"]
        elif data is not None:
            assert data["draft"] is True
            release = {"id": 7, "assets": [], "draft": True}
        return release

    def execute(command, **_):
        nonlocal failed
        calls.append(command)
        if command[0] == "uv" and not failed:
            failed = True
            raise subprocess.CalledProcessError(1, command)
        if command[:3] == ["gh", "release", "upload"]:
            release["assets"].append(asset)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(publisher, "api", api)
    monkeypatch.setattr(publisher.subprocess, "run", execute)
    with pytest.raises(subprocess.CalledProcessError):
        publisher.publish(REPOSITORY, "plugin/v1.0.0", REVISION, [wheel], pypi=True)
    assert release is None
    publisher.publish(REPOSITORY, "plugin/v1.0.0", REVISION, [wheel], pypi=True)
    publisher.publish(REPOSITORY, "plugin/v1.0.0", REVISION, [wheel], pypi=True)
    uploads = [command for command in calls if command[0] == "gh"]
    assert len(uploads) == 1
    assert "--clobber" not in uploads[0]
    assert all("--check-url" in command for command in calls if command[0] == "uv")


@pytest.mark.parametrize("digest", [None, "sha256:" + "0" * 64])
def test_existing_unverifiable_or_different_artifact_is_never_overwritten(tmp_path, digest):
    wheel = tmp_path / "artifact.whl"
    wheel.write_bytes(b"checked artifact")
    release = {"assets": [{"name": wheel.name, "digest": digest}]}
    with pytest.raises(ValueError, match="differs or has no verifiable digest"):
        publisher.existing_assets(release, [wheel])
