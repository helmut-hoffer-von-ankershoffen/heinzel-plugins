"""A retry never moves an existing tag or overwrites differently identified published artifacts."""

import hashlib
import json
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
    wrong = {"ref": f"refs/tags/{tag}", "object": {"type": "commit", "sha": "b" * 40}}
    monkeypatch.setattr(publisher, "api", lambda *a, **k: wrong)
    with pytest.raises(ValueError, match="built commit"):
        publisher.publish(REPOSITORY, tag, REVISION, [wheel], pypi=True)


def test_annotated_tags_are_peeled_before_comparison(monkeypatch):
    calls = []

    def api(path, **_):
        calls.append(path)
        return (
            {"object": {"type": "commit", "sha": REVISION}}
            if "/git/tags/" in path
            else {"ref": "refs/tags/plugin/v1.0.0", "object": {"type": "tag", "sha": "c" * 40}}
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
        return {"ref": "refs/tags/plugin/v1.0.0", "object": {"type": "commit", "sha": REVISION}}

    monkeypatch.setattr(publisher, "api", api)
    publisher.exact_tag(REPOSITORY, "plugin/v1.0.0", REVISION)
    assert calls[1][1] == {"ref": "refs/tags/plugin/v1.0.0", "sha": REVISION}


def test_null_initial_tag_response_refuses_without_writing_or_waiting(monkeypatch):
    def execute(command, **_):
        assert command == ["gh", "api", f"repos/{REPOSITORY}/git/ref/tags/app-v0.9.55"]
        return subprocess.CompletedProcess(command, 0, "null", "")

    monkeypatch.setattr(publisher.subprocess, "run", execute)
    monkeypatch.setattr(publisher.time, "sleep", lambda _: pytest.fail("Malformed response is not retryable"))
    with pytest.raises(ValueError, match="expected a JSON object"):
        publisher.exact_tag(REPOSITORY, "app-v0.9.55", REVISION)


@pytest.mark.parametrize(
    ("created", "early", "final", "error"),
    [
        ("exact", ["missing", "exact"], ["missing", "exact"], None),
        ("wrong-ref", [], [], "did not confirm creation"),
        ("wrong-commit", [], [], "did not confirm creation"),
        ("exact", ["missing"] * 5, [], "HTTP 404"),
        ("exact", ["forbidden"], [], "HTTP 403"),
        ("exact", ["null"], [], "expected a JSON object"),
        ("exact", ["wrong-ref"], [], "different tag ref"),
        ("exact", ["exact"], ["missing"] * 5, "HTTP 404"),
        ("exact", ["exact"], ["null"], "expected a JSON object"),
        ("exact", ["exact"], ["wrong-ref"], "different tag ref"),
        ("exact", ["exact"], ["wrong-commit"], "built commit"),
    ],
)
def test_app_publication_requires_bounded_exact_tag_readbacks(tmp_path, monkeypatch, created, early, final, error):
    tag = "app-v0.9.55"
    root = f"repos/{REPOSITORY}"
    profile = tmp_path / "standard.json"
    profile.write_bytes(b"verified app profile")
    reads = iter(["missing", *early, *final])
    release = {"id": 7, "tag_name": tag, "draft": True, "assets": []}
    writes, backoff = [], []

    def reference(answer):
        return {
            "ref": "refs/tags/other" if answer == "wrong-ref" else f"refs/tags/{tag}",
            "object": {"type": "commit", "sha": "b" * 40 if answer == "wrong-commit" else REVISION},
        }

    def execute(command, *, input=None, **_):
        if command[:3] == ["gh", "release", "upload"]:
            assert "--clobber" not in command
            writes.append("upload")
            digest = "sha256:" + hashlib.sha256(profile.read_bytes()).hexdigest()
            release["assets"].append({"name": profile.name, "digest": digest})
            return subprocess.CompletedProcess(command, 0)
        endpoint = command[2]
        payload = json.loads(input) if input else None
        if endpoint == f"{root}/git/ref/tags/{tag}":
            assert payload is None
            mode = next(reads)
            if mode in ("missing", "forbidden"):
                status = "Not Found (HTTP 404)" if mode == "missing" else "Forbidden (HTTP 403)"
                return subprocess.CompletedProcess(command, 1, "", f"gh: {status}")
            answer = None if mode == "null" else reference(mode)
        elif endpoint == f"{root}/git/refs":
            assert payload == {"ref": f"refs/tags/{tag}", "sha": REVISION}
            writes.append("create-tag")
            answer = reference(created)
        elif endpoint == "graphql":
            answer = {"data": {"repository": {"release": None}}}
        elif endpoint == f"{root}/releases":
            assert payload["draft"] is True and payload["target_commitish"] == REVISION
            writes.append("draft")
            answer = release
        else:
            assert endpoint == f"{root}/releases/7"
            if payload:
                assert payload == {"draft": False}
                writes.append("publish")
            answer = release
        return subprocess.CompletedProcess(command, 0, json.dumps(answer), "")

    monkeypatch.setattr(publisher.subprocess, "run", execute)
    monkeypatch.setattr(publisher.time, "sleep", backoff.append)
    if error is None:
        publisher.publish(REPOSITORY, tag, REVISION, [profile])
    else:
        with pytest.raises(ValueError, match=error):
            publisher.publish(REPOSITORY, tag, REVISION, [profile])
    expected = ["create-tag"]
    if early and early[-1] == "exact":
        expected.extend(["draft", "upload"])
    if error is None:
        expected.append("publish")
    assert writes == expected
    assert backoff == [delay for stage in (early, final) for delay in (1, 2, 4, 8)[: stage.count("missing")]]
    assert next(reads, None) is None


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
            return {"ref": "refs/tags/plugin/v1.0.0", "object": {"type": "commit", "sha": REVISION}}
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
            return {"ref": "refs/tags/plugin/v1.0.0", "object": {"type": "commit", "sha": REVISION}}
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
    monkeypatch.setattr(publisher, "exact_tag", lambda *_args, **_kwargs: None)
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
    monkeypatch.setattr(publisher, "exact_tag", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(publisher, "find_release", lambda *_args: release)
    monkeypatch.setattr(
        publisher, "api", lambda *_args, **_kwargs: pytest.fail("No upload or alias mutation before verification")
    )
    with pytest.raises(ValueError, match="differs or has no verifiable digest"):
        publisher.publish(REPOSITORY, "app-v0.9.1", REVISION, [artifact], make_latest="true")


@pytest.mark.parametrize("state", ["draft", "held", "final"])
def test_app_prerelease_publishes_atomically_without_reclassifying_public_releases(tmp_path, monkeypatch, state):
    wheel = tmp_path / "artifact.whl"
    wheel.write_bytes(b"checked artifact")
    release = {
        "id": 7,
        "draft": state == "draft",
        "prerelease": state == "held",
        "assets": [{"name": wheel.name, "digest": "sha256:" + hashlib.sha256(wheel.read_bytes()).hexdigest()}],
    }
    writes = []

    def api(path, data=None, method="GET"):
        assert path == "repos/example/plugins/releases/7"
        if data is not None:
            writes.append((method, data))
        return release

    monkeypatch.setattr(publisher, "api", api)
    monkeypatch.setattr(publisher, "exact_tag", lambda *_, **_kwargs: None)
    monkeypatch.setattr(publisher, "find_release", lambda *_: release)

    if state == "final":
        with pytest.raises(ValueError, match="already public final app"):
            publisher.publish(REPOSITORY, "app-v0.9.0", REVISION, [wheel], make_latest="false", prerelease=True)
    else:
        publisher.publish(REPOSITORY, "app-v0.9.0", REVISION, [wheel], make_latest="false", prerelease=True)

    assert writes == (
        [("PATCH", {"draft": False, "make_latest": "false", "prerelease": True})] if state == "draft" else []
    )


@pytest.mark.parametrize("notes", [None, "## heinzel-a 1.0.0\n\n- New.\n"])
def test_the_release_body_is_set_when_the_draft_is_created(tmp_path, monkeypatch, notes):
    wheel = tmp_path / "artifact.whl"
    wheel.write_bytes(b"checked artifact")
    asset = {"name": wheel.name, "digest": "sha256:" + hashlib.sha256(wheel.read_bytes()).hexdigest()}
    release = None
    bodies = []

    def api(path, data=None, method="POST", **_):
        nonlocal release
        if path == "graphql":
            return {"data": {"repository": {"release": {"databaseId": 7} if release else None}}}
        if "/git/ref/" in path:
            return {"ref": "refs/tags/plugin/v1.0.0", "object": {"type": "commit", "sha": REVISION}}
        if data is not None and method == "PATCH":
            assert "body" not in data, "notes are written once, at draft creation"
            release["draft"] = data["draft"]
        elif data is not None:
            bodies.append(data["body"])
            release = {"id": 7, "tag_name": "plugin/v1.0.0", "assets": [], "draft": True}
        return release

    def execute(command, **_):
        release["assets"].append(asset)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(publisher, "api", api)
    monkeypatch.setattr(publisher.subprocess, "run", execute)
    keywords = {} if notes is None else {"notes": notes}
    publisher.publish(REPOSITORY, "plugin/v1.0.0", REVISION, [wheel], **keywords)
    assert bodies == [notes or publisher.DEFAULT_NOTES]


@pytest.mark.parametrize("notes", ["", "  \n", "x" * (publisher.NOTES_LIMIT + 1)])
def test_empty_or_oversized_notes_fail_before_any_publication(tmp_path, monkeypatch, notes):
    wheel = tmp_path / "artifact.whl"
    wheel.write_bytes(b"checked artifact")
    calls = []

    def api(path, data=None, **_):
        calls.append(path)
        if path == "graphql":  # the read-only release lookup: no release yet
            return {"data": {"repository": {"release": None}}}
        pytest.fail(f"nothing may be read or written beyond the release lookup: {path} {data}")

    monkeypatch.setattr(publisher, "api", api)
    monkeypatch.setattr(publisher.subprocess, "run", lambda *a, **k: pytest.fail("nothing may be uploaded"))
    with pytest.raises(ValueError, match="notes"):
        publisher.publish(REPOSITORY, "plugin/v1.0.0", REVISION, [wheel], pypi=True, notes=notes)
    assert calls == ["graphql"], "no tag ref is created before the notes are refused"


def test_a_resumed_release_keeps_its_body_without_new_notes(tmp_path, monkeypatch):
    wheel = tmp_path / "artifact.whl"
    wheel.write_bytes(b"checked artifact")
    asset = {"name": wheel.name, "digest": "sha256:" + hashlib.sha256(wheel.read_bytes()).hexdigest()}
    release = {"id": 7, "tag_name": "plugin/v1.0.0", "assets": [asset], "draft": True}
    patches = []
    monkeypatch.setattr(publisher, "exact_tag", lambda *_, **_kwargs: None)
    monkeypatch.setattr(publisher, "find_release", lambda *_: release)

    def api(path, data=None, method="POST", **_):
        if method == "PATCH":
            patches.append(data)
        return release

    monkeypatch.setattr(publisher, "api", api)
    publisher.publish(REPOSITORY, "plugin/v1.0.0", REVISION, [wheel], notes="")
    assert patches == [{"draft": False}]


def test_the_cli_reads_the_notes_file(tmp_path, monkeypatch):
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist/artifact.whl").write_bytes(b"checked artifact")
    (tmp_path / "notes.md").write_text("- New.\n")
    seen = {}
    monkeypatch.setenv("GH_REPO", REPOSITORY)
    monkeypatch.setattr(publisher, "publish", lambda *a, **k: seen.update(k))
    arguments = ["publishing", "--tag", "plugin/v1.0.0", "--revision", REVISION, "--directory", str(tmp_path / "dist")]
    monkeypatch.setattr("sys.argv", [*arguments, "--notes-file", str(tmp_path / "notes.md")])
    publisher.main()
    assert seen["notes"] == "- New.\n"
    monkeypatch.setattr("sys.argv", arguments)
    publisher.main()
    assert seen["notes"] == publisher.DEFAULT_NOTES
