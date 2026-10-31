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
        if path == "graphql":
            return {"data": {"repository": {"release": {"databaseId": 7} if release else None}}}
        if "/git/ref/" in path:
            return {"object": {"type": "commit", "sha": REVISION}}
        if data is not None and method == "PATCH":
            assert release["assets"] == [asset], "publish only after verifying every upload"
            release["draft"] = data["draft"]
        elif data is not None:
            assert data["draft"] is True
            release = {"id": 7, "tag_name": "plugin/v1.0.0", "assets": [], "draft": True}
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


def test_a_draft_hidden_from_rest_tag_lookup_is_resumed_and_verified_by_id(tmp_path, monkeypatch):
    wheel = tmp_path / "artifact.whl"
    wheel.write_bytes(b"checked artifact")
    asset = {"name": wheel.name, "digest": "sha256:" + hashlib.sha256(wheel.read_bytes()).hexdigest()}
    release = {"id": 7, "tag_name": "plugin/v1.0.0", "assets": [], "draft": True}
    calls = []

    def api(path, data=None, method="POST", **_):
        calls.append((path, method))
        if path == "graphql":
            assert data["variables"] == {"owner": "example", "name": "plugins", "tag": "plugin/v1.0.0"}
            return {"data": {"repository": {"release": {"databaseId": 7}}}}
        if "/git/ref/" in path:
            return {"object": {"type": "commit", "sha": REVISION}}
        assert path == "repos/example/plugins/releases/7", (
            "Never create a duplicate draft or use its hidden REST tag route"
        )
        if method == "PATCH":
            assert release["assets"] == [asset]
            release["draft"] = False
        return release

    def execute(command, **_):
        assert command[:3] == ["gh", "release", "upload"]
        release["assets"].append(asset)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(publisher, "api", api)
    monkeypatch.setattr(publisher.subprocess, "run", execute)
    publisher.publish(REPOSITORY, "plugin/v1.0.0", REVISION, [wheel])
    publisher.publish(REPOSITORY, "plugin/v1.0.0", REVISION, [wheel])
    assert release["draft"] is False
    assert sum(method == "PATCH" for _, method in calls) == 1


@pytest.mark.parametrize(
    "answer",
    [
        {"errors": [{"message": "Unavailable"}]},
        {"data": {"repository": None}},
        {"data": {"repository": {"release": {"databaseId": "not-an-id"}}}},
    ],
)
def test_release_identity_errors_fail_closed(monkeypatch, answer):
    monkeypatch.setattr(publisher, "api", lambda *_, **__: answer)
    with pytest.raises(ValueError, match="GitHub"):
        publisher.find_release(REPOSITORY, "plugin/v1.0.0")


@pytest.mark.parametrize("digest", [None, "sha256:" + "0" * 64])
def test_existing_unverifiable_or_different_artifact_is_never_overwritten(tmp_path, digest):
    wheel = tmp_path / "artifact.whl"
    wheel.write_bytes(b"checked artifact")
    release = {"assets": [{"name": wheel.name, "digest": digest}]}
    with pytest.raises(ValueError, match="differs or has no verifiable digest"):
        publisher.existing_assets(release, [wheel])


@pytest.mark.parametrize(
    ("policy", "current", "expected"),
    [("false", None, "false"), ("true", None, "true"), ("true", "app-v0.9.0", "true"), ("true", "app-v0.9.2", "false")],
)
def test_explicit_latest_policy_is_applied_only_after_complete_asset_verification(
    tmp_path, monkeypatch, policy, current, expected
):
    artifact = tmp_path / "standard.json"
    artifact.write_bytes(b"verified profile")
    asset = {"name": artifact.name, "digest": "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest()}
    release = {"id": 7, "tag_name": "app-v0.9.1", "draft": True, "assets": [asset]}
    mutations = []
    monkeypatch.setattr(publisher, "exact_tag", lambda *_args: None)
    monkeypatch.setattr(publisher, "find_release", lambda *_args: release)

    def api(path, data=None, method="POST", **_kwargs):
        if path.endswith("/latest"):
            return {"tag_name": current} if current is not None else None
        assert path.endswith("/releases/7")
        if method == "PATCH":
            assert release["assets"] == [asset]
            mutations.append(data)
            release.update(data)
        return release

    monkeypatch.setattr(publisher, "api", api)
    monkeypatch.setattr(
        publisher.subprocess, "run", lambda *_args, **_kwargs: pytest.fail("Do not reupload or rebuild")
    )
    publisher.publish(REPOSITORY, "app-v0.9.1", REVISION, [artifact], make_latest=policy)
    publisher.publish(REPOSITORY, "app-v0.9.1", REVISION, [artifact], make_latest=policy)
    assert mutations == [{"draft": False, "make_latest": expected}] * 2


@pytest.mark.parametrize("current", [None, "plugin/v1.0.0", "app-v0.9.0rc1", "app-v0.09.0", "unknown"])
def test_unknown_current_standard_app_identity_cannot_be_promoted_over(monkeypatch, current):
    monkeypatch.setattr(publisher, "api", lambda *_args, **_kwargs: {"tag_name": current})
    with pytest.raises(ValueError):
        publisher._latest_setting(REPOSITORY, "app-v0.9.1", "true")


def test_nonlatest_plugin_publication_does_not_inspect_or_replace_the_app_alias(monkeypatch):
    monkeypatch.setattr(publisher, "api", lambda *_args, **_kwargs: pytest.fail("No latest alias lookup or promotion"))
    assert publisher._latest_setting(REPOSITORY, "plugin/v1.0.0", "false") == "false"


def test_unverified_assets_cannot_change_latest_policy(tmp_path, monkeypatch):
    artifact = tmp_path / "standard.json"
    artifact.write_bytes(b"built profile")
    release = {"id": 7, "draft": True, "assets": [{"name": artifact.name, "digest": "sha256:" + "0" * 64}]}
    monkeypatch.setattr(publisher, "exact_tag", lambda *_args: None)
    monkeypatch.setattr(publisher, "find_release", lambda *_args: release)
    monkeypatch.setattr(
        publisher, "api", lambda *_args, **_kwargs: pytest.fail("No upload or alias mutation before verification")
    )
    with pytest.raises(ValueError, match="differs or has no verifiable digest"):
        publisher.publish(REPOSITORY, "app-v0.9.1", REVISION, [artifact], make_latest="true")
