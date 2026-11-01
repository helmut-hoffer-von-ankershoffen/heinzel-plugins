"""Publication input checks, GitHub transport errors and verified restoration of published artifacts."""

import hashlib
import io
import json
import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

from heinzel_plugin_tools import publishing as publisher

pytestmark = pytest.mark.unit

REVISION = "a" * 40
REPOSITORY = "example/plugins"
TAG = "heinzel-harbor/v1.2.0"


def completed(command, code=0, out="", err=""):
    return subprocess.CompletedProcess(command, code, out, err)


def test_api_returns_decoded_json_and_sends_the_payload_on_stdin(monkeypatch):
    seen = {}

    def run(command, **options):
        seen.update(command=command, options=options)
        return completed(command, out='{"id": 3}')

    monkeypatch.setattr(publisher.subprocess, "run", run)
    assert publisher.api("repos/example/plugins/releases", data={"draft": True}, method="PATCH") == {"id": 3}
    assert seen["command"] == ["gh", "api", "repos/example/plugins/releases", "--method", "PATCH", "--input", "-"]
    assert json.loads(seen["options"]["input"]) == {"draft": True}


def test_api_reads_without_a_body_by_default(monkeypatch):
    seen = {}

    def run(command, **options):
        seen.update(command=command, options=options)
        return completed(command, out="[]")

    monkeypatch.setattr(publisher.subprocess, "run", run)
    assert publisher.api("repos/example/plugins/releases") == []
    assert seen["command"] == ["gh", "api", "repos/example/plugins/releases"]
    assert seen["options"]["input"] is None


def test_a_404_is_tolerated_only_when_the_caller_expects_it(monkeypatch):
    failure = completed(["gh"], 1, err="gh: Not Found (HTTP 404)\n")
    monkeypatch.setattr(publisher.subprocess, "run", lambda *a, **k: failure)
    assert publisher.api("repos/x/y/git/ref/tags/t", missing=True) is None
    with pytest.raises(ValueError, match="GitHub request failed for repos/x/y/git/ref/tags/t: gh: Not Found"):
        publisher.api("repos/x/y/git/ref/tags/t")


def test_other_failures_are_never_treated_as_a_missing_object(monkeypatch):
    failure = completed(["gh"], 1, err="gh: Server Error (HTTP 500)")
    monkeypatch.setattr(publisher.subprocess, "run", lambda *a, **k: failure)
    with pytest.raises(ValueError, match="HTTP 500"):
        publisher.api("repos/x/y/git/ref/tags/t", missing=True)


def test_a_tag_that_resolves_to_a_tree_or_never_peels_is_refused(monkeypatch):
    monkeypatch.setattr(publisher, "api", lambda *a, **k: {"object": {"type": "tree", "sha": REVISION}})
    with pytest.raises(ValueError, match="built commit"):
        publisher.exact_tag(REPOSITORY, "plugin/v1.0.0", REVISION)
    monkeypatch.setattr(publisher, "api", lambda *a, **k: {"object": {"type": "tag", "sha": "c" * 40}})
    with pytest.raises(ValueError, match="built commit"):
        publisher.exact_tag(REPOSITORY, "plugin/v1.0.0", REVISION)


def test_assets_beyond_the_built_set_make_a_release_unalterable(tmp_path):
    wheel = tmp_path / "a.whl"
    wheel.write_bytes(b"x")
    with pytest.raises(ValueError, match="unexpected artifacts"):
        publisher.existing_assets({"assets": [{"name": "stray.txt", "digest": None}]}, [wheel])


def test_only_the_missing_artifacts_are_pending_for_upload(tmp_path):
    wheel, sdist = tmp_path / "a.whl", tmp_path / "a.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    release = {"assets": [{"name": wheel.name, "digest": "sha256:" + hashlib.sha256(b"wheel").hexdigest()}]}
    assert publisher.existing_assets(release, [wheel, sdist]) == [sdist]
    assert publisher.existing_assets(None, [wheel, sdist]) == [wheel, sdist]


def test_release_lookup_returns_none_when_no_release_exists(monkeypatch):
    monkeypatch.setattr(publisher, "api", lambda *a, **k: {"data": {"repository": {"release": None}}})
    assert publisher.find_release(REPOSITORY, "plugin/v1.0.0") is None


@pytest.mark.parametrize("release", [None, {"id": 8, "tag_name": "plugin/v1.0.0"}, {"id": 7, "tag_name": "other"}])
def test_a_release_with_a_different_identity_than_requested_is_refused(monkeypatch, release):
    def api(path, **_):
        if path == "graphql":
            return {"data": {"repository": {"release": {"databaseId": 7}}}}
        return release

    monkeypatch.setattr(publisher, "api", api)
    with pytest.raises(ValueError, match="different release identity"):
        publisher.find_release(REPOSITORY, "plugin/v1.0.0")


@pytest.mark.parametrize("tag", ["app-v01.0.0", "app-v1.0.0rc1", "app-v1.0.0.dev1", "app-vx"])
def test_only_a_canonical_stable_app_version_can_become_latest(tag):
    with pytest.raises(ValueError):
        publisher._app_version(tag)


def test_a_canonical_app_tag_parses_to_its_version():
    assert str(publisher._app_version("app-v1.2.3")) == "1.2.3"


def test_a_current_non_string_latest_identity_cannot_be_compared(monkeypatch):
    monkeypatch.setattr(publisher, "api", lambda *a, **k: {"tag_name": 5})
    with pytest.raises(ValueError, match="latest release identity is invalid"):
        publisher._latest_setting(REPOSITORY, "app-v1.0.0", "true")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"make_latest": "maybe"}, "explicit true or false"),
        ({"repository": "not-a-repository"}, "owner/repository"),
        ({"repository": "a/b/c"}, "owner/repository"),
        ({"tag": "Plugin/V1"}, "canonical tag"),
        ({"revision": "abc123"}, "canonical tag"),
        ({"revision": "A" * 40}, "canonical tag"),
    ],
)
def test_malformed_publication_inputs_are_refused_before_any_network_call(tmp_path, monkeypatch, kwargs, message):
    wheel = tmp_path / "a.whl"
    wheel.write_bytes(b"x")
    monkeypatch.setattr(publisher, "api", lambda *a, **k: pytest.fail("No request for invalid input"))
    arguments = {"repository": REPOSITORY, "tag": "plugin/v1.0.0", "revision": REVISION} | kwargs
    with pytest.raises(ValueError, match=message):
        publisher.publish(
            arguments.pop("repository"),
            arguments.pop("tag"),
            arguments.pop("revision"),
            [wheel],
            **arguments,
        )


def test_artifacts_must_be_existing_regular_non_linked_files(tmp_path, monkeypatch):
    monkeypatch.setattr(publisher, "api", lambda *a, **k: pytest.fail("No request for invalid artifacts"))
    real = tmp_path / "real.whl"
    real.write_bytes(b"x")
    link = tmp_path / "link.whl"
    link.symlink_to(real)
    for artifacts in ([], [tmp_path / "missing.whl"], [link], [tmp_path]):
        with pytest.raises(ValueError, match="exact built artifact files"):
            publisher.publish(REPOSITORY, "plugin/v1.0.0", REVISION, artifacts)


def test_a_published_but_incomplete_release_is_never_modified(tmp_path, monkeypatch):
    wheel = tmp_path / "a.whl"
    wheel.write_bytes(b"x")
    monkeypatch.setattr(publisher, "exact_tag", lambda *a: None)
    monkeypatch.setattr(publisher, "find_release", lambda *a: {"id": 7, "draft": False, "assets": []})
    monkeypatch.setattr(publisher.subprocess, "run", lambda *a, **k: pytest.fail("Immutable release was touched"))
    with pytest.raises(ValueError, match="incomplete; refusing to change immutable"):
        publisher.publish(REPOSITORY, "plugin/v1.0.0", REVISION, [wheel])


def test_an_upload_that_does_not_show_up_is_reported_as_incomplete(tmp_path, monkeypatch):
    wheel = tmp_path / "a.whl"
    wheel.write_bytes(b"x")
    draft = {"id": 7, "draft": True, "assets": []}
    monkeypatch.setattr(publisher, "exact_tag", lambda *a: None)
    monkeypatch.setattr(publisher, "find_release", lambda *a: draft)
    monkeypatch.setattr(publisher, "api", lambda *a, **k: draft)
    monkeypatch.setattr(publisher.subprocess, "run", lambda command, **k: completed(command))
    with pytest.raises(ValueError, match="Publication is incomplete"):
        publisher.publish(REPOSITORY, "plugin/v1.0.0", REVISION, [wheel])


def test_a_fresh_release_is_created_as_a_draft_pinned_to_the_built_commit(tmp_path, monkeypatch):
    wheel = tmp_path / "a.whl"
    wheel.write_bytes(b"x")
    digest = "sha256:" + hashlib.sha256(b"x").hexdigest()
    state = {"release": None}
    requests = []

    def api(path, data=None, method="POST", **_):
        requests.append((path, method, data))
        if data and path.endswith("/releases") and method == "POST":
            state["release"] = {"id": 9, "draft": True, "assets": []}
            return state["release"]
        if "releases/9" in path and method != "PATCH":
            return {"id": 9, "draft": True, "assets": [{"name": wheel.name, "digest": digest}]}
        return {"id": 9, "draft": False}

    monkeypatch.setattr(publisher, "exact_tag", lambda *a: None)
    monkeypatch.setattr(publisher, "find_release", lambda *a: None)
    monkeypatch.setattr(publisher, "api", api)
    monkeypatch.setattr(publisher.subprocess, "run", lambda command, **k: completed(command))
    publisher.publish(REPOSITORY, "plugin/v1.0.0", REVISION, [wheel])
    created = requests[0][2]
    assert created["target_commitish"] == REVISION and created["draft"] is True
    assert requests[-1][:2] == ("repos/example/plugins/releases/9", "PATCH")
    assert requests[-1][2] == {"draft": False}


def wheel_bytes(metadata: str, member="harbor-1.2.0.dist-info/METADATA") -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(member, metadata)
    return stream.getvalue()


def sdist_bytes(metadata: str, member="heinzel_harbor-1.2.0/PKG-INFO") -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        data = metadata.encode()
        info = tarfile.TarInfo(member)
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    return stream.getvalue()


METADATA = "Metadata-Version: 2.1\nName: Heinzel_Harbor\nVersion: 1.2.0\n"


def test_wheel_and_sdist_identities_are_read_from_declared_metadata(tmp_path):
    wheel = tmp_path / "heinzel_harbor-1.2.0-py3-none-any.whl"
    wheel.write_bytes(wheel_bytes(METADATA))
    sdist = tmp_path / "heinzel_harbor-1.2.0.tar.gz"
    sdist.write_bytes(sdist_bytes(METADATA))
    assert publisher.artifact_identity(wheel) == ("heinzel-harbor", "1.2.0")
    assert publisher.artifact_identity(sdist) == ("heinzel-harbor", "1.2.0")


def test_a_wheel_without_exactly_one_metadata_file_has_no_identity(tmp_path):
    wheel = tmp_path / "x-1-py3-none-any.whl"
    wheel.write_bytes(wheel_bytes(METADATA, member="README.md"))
    with pytest.raises(ValueError, match="exactly one metadata identity"):
        publisher.artifact_identity(wheel)


def test_an_sdist_with_nested_or_missing_package_info_has_no_identity(tmp_path):
    nested = tmp_path / "x-1.tar.gz"
    nested.write_bytes(sdist_bytes(METADATA, member="x-1/deep/PKG-INFO"))
    with pytest.raises(ValueError, match="one bounded root metadata"):
        publisher.artifact_identity(nested)


def test_unknown_artifact_kinds_and_nameless_metadata_are_refused(tmp_path):
    other = tmp_path / "x.zip"
    other.write_bytes(b"")
    with pytest.raises(ValueError, match="wheel and source distribution"):
        publisher.artifact_identity(other)
    nameless = tmp_path / "x-1-py3-none-any.whl"
    nameless.write_bytes(wheel_bytes("Metadata-Version: 2.1\nName: harbor\n"))
    with pytest.raises(ValueError, match="name and version"):
        publisher.artifact_identity(nameless)


def test_oversized_wheel_metadata_is_refused(tmp_path):
    wheel = tmp_path / "x-1-py3-none-any.whl"
    wheel.write_bytes(wheel_bytes("Name: harbor\nVersion: 1\n" + "x" * (1024 * 1024)))
    with pytest.raises(ValueError, match="size limit"):
        publisher.artifact_identity(wheel)


def test_a_tag_is_read_back_to_a_full_commit_without_creating_it(monkeypatch):
    calls = []

    def api(path, **kwargs):
        calls.append((path, kwargs))
        if "/git/tags/" in path:
            return {"object": {"type": "commit", "sha": REVISION}}
        return {"object": {"type": "tag", "sha": "c" * 40}}

    monkeypatch.setattr(publisher, "api", api)
    assert publisher.tag_revision(REPOSITORY, TAG) == REVISION
    assert all(kwargs.get("data") is None for _, kwargs in calls)
    assert "heinzel-harbor%2Fv1.2.0" in calls[0][0]


def test_a_tag_that_is_not_a_commit_cannot_be_restored(monkeypatch):
    monkeypatch.setattr(publisher, "api", lambda *a, **k: {"object": {"type": "blob", "sha": REVISION}})
    with pytest.raises(ValueError, match="existing source commit"):
        publisher.tag_revision(REPOSITORY, TAG)


@pytest.fixture
def release(tmp_path, monkeypatch):
    """A complete published release whose downloads are materialized from fictional bytes."""
    wheel_name = "heinzel_harbor-1.2.0-py3-none-any.whl"
    contents = {wheel_name: wheel_bytes(METADATA), "heinzel_harbor-1.2.0.tar.gz": sdist_bytes(METADATA)}
    assets = [
        {"name": name, "size": len(data), "digest": "sha256:" + hashlib.sha256(data).hexdigest()}
        for name, data in contents.items()
    ]
    state = {"release": {"draft": False, "assets": assets}, "commands": [], "contents": contents}

    def api(path, **_):
        if "/git/ref/" in path:
            return {"object": {"type": "commit", "sha": REVISION}}
        return state["release"]

    def run(command, **_):
        state["commands"].append(command)
        if command[:3] == ["gh", "release", "download"]:
            destination = Path(command[command.index("--dir") + 1])
            name = command[command.index("--pattern") + 1]
            (destination / name).write_bytes(state["contents"][name])
        return completed(command)

    monkeypatch.setattr(publisher, "api", api)
    monkeypatch.setattr(publisher.subprocess, "run", run)
    return state, tmp_path / "restored"


def test_restoring_downloads_attests_and_reports_every_artifact(release):
    state, destination = release
    record = publisher.restore(REPOSITORY, TAG, "heinzel-harbor", destination)
    assert (record["tag"], record["name"], record["version"], record["revision"]) == (
        TAG,
        "heinzel-harbor",
        "1.2.0",
        REVISION,
    )
    assert sorted(Path(path).name for path in record["artifacts"]) == sorted(state["contents"])
    for path, sha in record["artifact_hashes"].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha
    attestations = [c for c in state["commands"] if c[:3] == ["gh", "attestation", "verify"]]
    assert len(attestations) == 2
    assert all(c[c.index("--source-digest") + 1] == REVISION for c in attestations)
    assert all("--deny-self-hosted-runners" in c for c in attestations)


def test_the_short_plugin_name_is_accepted_for_its_prefixed_tag(release):
    _, destination = release
    assert publisher.restore(REPOSITORY, TAG, "harbor", destination)["name"] == "heinzel-harbor"


@pytest.mark.parametrize(
    ("tag", "name", "message"),
    [
        ("heinzel-harbor/v1.2.0", "other", "existing independent release tag"),
        ("heinzel-harbor/v01.2.0", "heinzel-harbor", "canonical release version"),
        ("heinzel-harbor/1.2.0", "heinzel-harbor", "existing independent release tag"),
        ("heinzel-harbor/v1.2.0", "Heinzel_Harbor", "existing independent release tag"),
    ],
)
def test_restoration_requires_this_plugins_own_canonical_tag(release, tag, name, message):
    _, destination = release
    with pytest.raises(ValueError, match=message):
        publisher.restore(REPOSITORY, tag, name, destination)
    assert not destination.exists()


def test_restoration_rejects_an_invalid_repository_identity(release):
    _, destination = release
    with pytest.raises(ValueError, match="owner/repository"):
        publisher.restore("nonsense", TAG, "heinzel-harbor", destination)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda r: r.update(draft=True), "complete published wheel/sdist"),
        (lambda r: r.update(assets=r["assets"][:1]), "complete published wheel/sdist"),
        (
            lambda r: r["assets"][0].update(name="heinzel_harbor-9.9.9-py3-none-any.whl"),
            "wheel does not match",
        ),
        (lambda r: r["assets"][1].update(name="heinzel_harbor-9.9.9.tar.gz"), "source distribution does not match"),
    ],
)
def test_an_incomplete_or_mismatched_release_is_never_downloaded(release, change, message):
    state, destination = release
    change(state["release"])
    with pytest.raises(ValueError, match=message):
        publisher.restore(REPOSITORY, TAG, "heinzel-harbor", destination)
    assert not any(c[:3] == ["gh", "release", "download"] for c in state["commands"])


def test_a_digest_mismatch_stops_before_attestation_or_upload(release):
    state, destination = release
    state["release"]["assets"][0]["digest"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="identity or digest differs"):
        publisher.restore(REPOSITORY, TAG, "heinzel-harbor", destination)
    assert not any(c[:2] == ["gh", "attestation"] for c in state["commands"])


def test_a_download_of_the_wrong_size_is_refused(release):
    state, destination = release
    state["release"]["assets"][0]["size"] += 1
    with pytest.raises(ValueError, match="size differs"):
        publisher.restore(REPOSITORY, TAG, "heinzel-harbor", destination)


def test_an_oversized_release_artifact_is_never_downloaded(release):
    state, destination = release
    state["release"]["assets"][1]["size"] = 200 * 1024 * 1024
    with pytest.raises(ValueError, match="bounded canonical filenames"):
        publisher.restore(REPOSITORY, TAG, "heinzel-harbor", destination)
    downloaded = [c[c.index("--pattern") + 1] for c in state["commands"] if c[:3] == ["gh", "release", "download"]]
    assert "heinzel_harbor-1.2.0.tar.gz" not in downloaded


def test_an_asset_name_containing_a_path_is_refused(release):
    state, destination = release
    state["release"]["assets"][0]["name"] = "../heinzel_harbor-1.2.0-py3-none-any.whl"
    with pytest.raises(ValueError):
        publisher.restore(REPOSITORY, TAG, "heinzel-harbor", destination)


def test_an_artifact_that_changes_during_attestation_is_refused(release, monkeypatch):
    state, destination = release
    inner = publisher.subprocess.run

    def tamper(command, **options):
        result = inner(command, **options)
        if command[:3] == ["gh", "attestation", "verify"]:
            Path(command[3]).write_bytes(b"swapped after download")
        return result

    monkeypatch.setattr(publisher.subprocess, "run", tamper)
    with pytest.raises(ValueError, match="changed during attestation"):
        publisher.restore(REPOSITORY, TAG, "heinzel-harbor", destination)


def run_main(monkeypatch, arguments, environment=None):
    monkeypatch.setattr("sys.argv", ["publishing", *arguments])
    for key, value in (environment or {}).items():
        monkeypatch.setenv(key, value)
    publisher.main()


def test_the_publish_command_uploads_every_file_except_the_release_record(tmp_path, monkeypatch):
    (tmp_path / "a.whl").write_bytes(b"w")
    (tmp_path / "b.tar.gz").write_bytes(b"s")
    (tmp_path / "release.json").write_text("{}")
    (tmp_path / "nested").mkdir()
    seen = {}
    monkeypatch.setattr(publisher, "publish", lambda *args, **kwargs: seen.update(args=args, kwargs=kwargs))
    run_main(
        monkeypatch,
        [
            "--tag",
            "plugin/v1.0.0",
            "--revision",
            REVISION,
            "--directory",
            str(tmp_path),
            "--pypi",
            "--make-latest",
            "false",
        ],
        {"GH_REPO": REPOSITORY},
    )
    assert seen["args"][:3] == (REPOSITORY, "plugin/v1.0.0", REVISION)
    assert [path.name for path in seen["args"][3]] == ["a.whl", "b.tar.gz"]
    assert seen["kwargs"] == {"pypi": True, "make_latest": "false"}


def test_publishing_without_a_built_revision_is_a_usage_error(tmp_path, monkeypatch):
    with pytest.raises(SystemExit) as stopped:
        run_main(monkeypatch, ["--tag", "t", "--directory", str(tmp_path)], {"GH_REPO": REPOSITORY})
    assert stopped.value.code == 2


def test_restoring_requires_the_owning_distribution_name(tmp_path, monkeypatch):
    with pytest.raises(SystemExit) as stopped:
        run_main(monkeypatch, ["--tag", TAG, "--directory", str(tmp_path), "--restore"], {"GH_REPO": REPOSITORY})
    assert stopped.value.code == 2


def test_restore_prints_the_record_and_exports_the_workflow_outputs(tmp_path, monkeypatch, capsys):
    record = {"tag": TAG, "name": "heinzel-harbor", "version": "1.2.0", "revision": REVISION}
    monkeypatch.setattr(publisher, "restore", lambda *args: record)
    output = tmp_path / "github-output"
    run_main(
        monkeypatch,
        ["--tag", TAG, "--directory", str(tmp_path / "d"), "--restore", "--name", "harbor"],
        {"GH_REPO": REPOSITORY, "GITHUB_OUTPUT": str(output)},
    )
    assert json.loads(capsys.readouterr().out) == record
    assert output.read_text().splitlines() == [
        f"tag={TAG}",
        "name=heinzel-harbor",
        f"revision={REVISION}",
    ]
