"""A new SDK must not leave the versionless app installer without a verified composition."""

import hashlib
import json
import runpy
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit
SELECT = runpy.run_path(str(Path(__file__).parents[1] / "scripts/next_app.py"))["select"]


@pytest.fixture
def releases(monkeypatch):
    metadata = {
        "info": {"version": "1.2.3"},
        "urls": [{"filename": "heinzel-1.2.3-py3-none-any.whl", "yanked": False, "digests": {"sha256": "a" * 64}}],
    }
    sdk = {"assets": [{"name": "heinzel-1.2.3-py3-none-any.whl", "digest": "sha256:" + "a" * 64}]}
    responses = {
        "app": None,
        "repos/example/plugins/git/ref/tags/app-v1.2.3": None,
        "repos/helmut-hoffer-von-ankershoffen/heinzel/releases/tags/v1.2.3": sdk,
    }
    monkeypatch.setitem(SELECT.__globals__, "package", lambda _version: metadata)
    monkeypatch.setitem(SELECT.__globals__, "api", lambda path, **_: responses[path])
    monkeypatch.setitem(SELECT.__globals__, "find_release", lambda *_: responses["app"])
    return metadata, sdk, responses


def test_schedule_selects_a_new_published_sdk_without_plugin_or_core_builds(releases):
    chosen = SELECT("example/plugins")
    assert chosen["version"] == "1.2.3"
    assert chosen["core_wheel"].endswith("/v1.2.3/heinzel-1.2.3-py3-none-any.whl")


def existing_app(releases, monkeypatch, change=lambda _profile: None):
    artifacts = []
    for name, version, digest in (("heinzel", "1.2.3", "a" * 64), ("heinzel-harbor", "4.5.6", "b" * 64)):
        filename = f"{name.replace('-', '_')}-{version}-py3-none-any.whl"
        artifacts.append(
            {
                "name": name,
                "version": version,
                "filename": filename,
                "sha256": digest,
                "url": f"https://github.com/example/plugins/releases/download/app-v1.2.3/{filename}",
            }
        )
    profile = {"format": 1, "sdk": 1, "core_version": "1.2.3", "artifacts": artifacts}
    change(profile)
    content = json.dumps(profile).encode()
    release = {
        "draft": False,
        "assets": [
            {"name": "standard.json", "digest": "sha256:" + hashlib.sha256(content).hexdigest(), "size": len(content)},
            *({"name": a["filename"], "digest": "sha256:" + a["sha256"]} for a in artifacts),
        ],
    }
    monkeypatch.setitem(SELECT.__globals__, "download", lambda *_: content)
    releases[2]["app"] = release
    return release


def test_an_existing_complete_app_is_a_noop(releases, monkeypatch):
    existing_app(releases, monkeypatch)
    assert SELECT("example/plugins") is None


@pytest.mark.parametrize("field", ["version", "filename", "url"])
def test_a_profile_rejected_by_installer_field_bounds_is_not_a_complete_app(releases, monkeypatch, field):
    def change(profile):
        artifact = profile["artifacts"][1]
        if field == "version":
            artifact["version"] = "1" * 81
            artifact["filename"] = f"heinzel_harbor-{artifact['version']}-py3-none-any.whl"
        elif field == "filename":
            artifact["name"] = "heinzel-" + "h" * 240
            artifact["filename"] = f"{artifact['name'].replace('-', '_')}-4.5.6-py3-none-any.whl"
        else:
            artifact["url"] = "https://github.com/" + "h" * 4096
        if field != "url":
            artifact["url"] = f"https://github.com/example/plugins/releases/download/app-v1.2.3/{artifact['filename']}"

    existing_app(releases, monkeypatch, change)
    with pytest.raises(ValueError, match="installer contract"):
        SELECT("example/plugins")


@pytest.mark.parametrize(
    "problem", ["missing-provider", "wrong-provider-hash", "wrong-profile-hash", "invalid-profile"]
)
def test_a_published_partial_or_corrupt_app_requires_review_instead_of_a_false_noop(releases, monkeypatch, problem):
    change = (lambda profile: profile.update(sdk=2)) if problem == "invalid-profile" else lambda _: None
    release = existing_app(releases, monkeypatch, change)
    if problem == "missing-provider":
        release["assets"].pop()
    elif problem == "wrong-provider-hash":
        release["assets"][-1]["digest"] = "sha256:" + "c" * 64
    elif problem == "wrong-profile-hash":
        release["assets"][0]["digest"] = "sha256:" + "c" * 64
    with pytest.raises(ValueError, match="operator review"):
        SELECT("example/plugins")


@pytest.mark.parametrize("state", ["draft-at-old-main", "prerelease-at-old-main", "tag-with-no-release"])
def test_an_existing_identity_never_recomposes_at_a_new_main_revision(releases, state):
    if state == "draft-at-old-main":
        releases[2]["app"] = {"draft": True, "target_commitish": "older-immutable-commit"}
    elif state == "prerelease-at-old-main":
        releases[2]["app"] = {"draft": False, "prerelease": True, "target_commitish": "older-immutable-commit"}
    else:
        releases[2]["repos/example/plugins/git/ref/tags/app-v1.2.3"] = {"object": {"sha": "older-immutable-commit"}}
    with pytest.raises(ValueError, match="operator review"):
        SELECT("example/plugins")


@pytest.mark.parametrize("version", ["1.2", "01.2.3", "1.2.3rc1", "1.2.3.dev1", "1.2.3+local"])
def test_nonstable_or_noncanonical_sdk_versions_are_not_app_releases(releases, version):
    releases[0]["info"]["version"] = version
    with pytest.raises(ValueError, match="canonical stable"):
        SELECT("example/plugins")


def test_explicit_sdk_metadata_must_match_the_selected_version(releases):
    url = "https://github.com/helmut-hoffer-von-ankershoffen/heinzel/releases/download/v1.2.4/heinzel-1.2.4-py3-none-any.whl"
    with pytest.raises(ValueError, match="metadata does not match"):
        SELECT("example/plugins", version="1.2.4", core_wheel=url)


@pytest.mark.parametrize("incomplete", ["draft", "missing-wheel", "yanked"])
def test_partially_published_sdks_do_not_start_composition(releases, incomplete):
    metadata, sdk, _ = releases
    if incomplete == "draft":
        sdk["draft"] = True
    elif incomplete == "missing-wheel":
        sdk["assets"] = []
    else:
        metadata["urls"][0]["yanked"] = True
    assert SELECT("example/plugins") is None


def test_mismatched_sdk_bytes_fail_before_any_composition(releases):
    releases[1]["assets"][0]["digest"] = "sha256:" + "b" * 64
    with pytest.raises(ValueError, match="does not match"):
        SELECT("example/plugins")


def test_explicit_unreviewed_core_urls_are_rejected(releases):
    with pytest.raises(ValueError, match="official immutable"):
        SELECT("example/plugins", version="1.2.3", core_wheel="https://example.test/not-the-sdk.whl")
