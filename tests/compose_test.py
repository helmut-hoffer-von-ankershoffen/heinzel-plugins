"""App composition must consume the already released and accepted plugin bytes."""

import hashlib
import json
import runpy
import zipfile
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from heinzel_plugin_tools.cli import Project

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "changed",
    [None, "source", "copy", "profile", "restore", "plugin-acceptance", "core-before", "core-install", "core-after"],
)
def test_composition_never_rebuilds_an_independently_released_plugin(tmp_path, monkeypatch, changed):
    compose = runpy.run_path(str(Path(__file__).parents[1] / "scripts/compose.py"))["compose"]
    scope = compose.__globals__
    destination = tmp_path / "composition"
    destination.mkdir()
    core = destination / "heinzel-0.9.1-py3-none-any.whl"
    with zipfile.ZipFile(core, "w") as archive:
        archive.writestr("heinzel-0.9.1.dist-info/METADATA", "Name: heinzel\nVersion: 0.9.1\n")
    core_digest = hashlib.sha256(core.read_bytes()).hexdigest()
    if changed == "core-before":
        core.write_bytes(core.read_bytes() + b"replaced verified core")
    directory = tmp_path / "plugins/heinzel-unforeseen"
    (directory / "tests/acceptance").mkdir(parents=True)
    project = Project(
        directory, "heinzel-unforeseen", "1.0.0", {"tool": {"heinzel": {"plugin": {"profiles": ["standard"]}}}}
    )
    # A stale local dist must not influence the selected release wheel.
    (directory / "dist").mkdir()
    (directory / "dist/heinzel_unforeseen-1.0.0-py3-none-any.whl").write_bytes(b"stale local artifact")
    accepted = []
    released = []
    calls = []
    managed = []
    monkeypatch.setenv("PYTHONPATH", "/a/checkout/must/not/override/the/sdk")
    monkeypatch.setenv("PYTHONHOME", "/an/unrelated/python")

    def restore(repository, tag, name, target):
        assert any("--dry-run" in command for command in calls)
        assert (repository, tag, name) == ("example/plugins", "heinzel-unforeseen/v1.0.0", project.name)
        target.mkdir(parents=True)
        wheel = target / "heinzel_unforeseen-1.0.0-py3-none-any.whl"
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr(
                "heinzel_unforeseen-1.0.0.dist-info/METADATA",
                "Name: heinzel-unforeseen\nVersion: 1.0.0\nRequires-Dist: heinzel>=0.9.1,<0.10\n",
            )
        released.append(wheel.read_bytes())
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        if changed == "restore":
            wheel.write_bytes(wheel.read_bytes() + b"replaced verified plugin")
        return {"artifacts": [str(wheel)], "artifact_hashes": {str(wheel): digest}}

    def run(command, **kwargs):
        calls.append(command)
        assert "PYTHONPATH" not in kwargs["env"]
        assert "PYTHONHOME" not in kwargs["env"]
        if str(command[0]).endswith("/bin/python"):
            assert command[1] == "-I"
            assert command.count("-I") == 1
        if command[:2] == ["uv", "venv"]:
            Path(command[-1]).mkdir()
            if changed == "core-install":
                core.write_bytes(core.read_bytes() + b"replaced before install")
        if "--dry-run" in command:
            probe = json.loads(Path(command[-1]).read_text())
            assert (probe["format"], probe["sdk"]) == (2, 1)
            assert [item["name"] for item in probe["artifacts"]] == ["heinzel"]

    monkeypatch.setenv("GH_REPO", "example/plugins")
    monkeypatch.setitem(scope, "projects", lambda: [project])
    monkeypatch.setitem(scope, "validate_lock", lambda *_: {})
    monkeypatch.setitem(scope, "restore", restore)

    def accept_plugin(*_args, wheel):
        accepted.append(wheel.read_bytes())
        if changed == "plugin-acceptance":
            wheel.write_bytes(wheel.read_bytes() + b"replaced during acceptance")

    monkeypatch.setitem(scope, "acceptance", accept_plugin)
    monkeypatch.setitem(scope, "run", run)

    def verify_managed(_interpreter, candidate):
        value = json.loads(candidate.read_text())
        managed.append(value)
        artifact = value["artifacts"][1]
        if changed in {"source", "copy"}:
            path = Path(artifact["url"]) if changed == "source" else destination / artifact["filename"]
            path.write_bytes(path.read_bytes() + b"changed after acceptance")
        elif changed == "profile":
            candidate.write_text(json.dumps(value | {"sdk": 99}))
        elif changed == "core-after":
            core.write_bytes(core.read_bytes() + b"replaced core after acceptance")

    monkeypatch.setitem(scope, "verify_managed_profile", verify_managed)
    if changed:
        with pytest.raises(ValueError, match="changed|differs"):
            compose(core, destination, "https://example.test/releases/app-v0.9.1", core_sha256=core_digest)
        assert not (destination / "standard.json").exists()
        if changed in {"core-before", "core-install"}:
            assert not any(command[:3] == ["uv", "pip", "install"] for command in calls)
        if changed == "restore":
            assert accepted == []
        return
    compose(core, destination, "https://example.test/releases/app-v0.9.1", core_sha256=core_digest)
    plugin = next(
        item
        for item in json.loads((destination / "standard.json").read_text())["artifacts"]
        if item["name"] == project.name
    )
    assert accepted == released
    assert (destination / plugin["filename"]).read_bytes() == released[0]
    assert plugin["sha256"] == hashlib.sha256(released[0]).hexdigest()
    assert not (destination / ".verified").exists()
    assert not any("build" in command or "pytest" in command for command in calls)
    assert json.loads((destination / "standard.json").read_text())["format"] == 2
    assert len(managed) == 1
    assert managed[0]["artifacts"][1]["sha256"] == plugin["sha256"]


def test_legacy_sdk_is_refused_before_any_provider_restoration_or_acceptance(tmp_path, monkeypatch):
    compose = runpy.run_path(str(Path(__file__).parents[1] / "scripts/compose.py"))["compose"]
    scope = compose.__globals__
    destination = tmp_path / "composition"
    destination.mkdir()
    core = destination / "heinzel-0.9.1-py3-none-any.whl"
    with zipfile.ZipFile(core, "w") as archive:
        archive.writestr("heinzel-0.9.1.dist-info/METADATA", "Name: heinzel\nVersion: 0.9.1\n")
    project = Project(
        tmp_path / "plugin", "heinzel-harbor", "1.0.0", {"tool": {"heinzel": {"plugin": {"profiles": ["standard"]}}}}
    )

    def run(command, **_kwargs):
        if "--dry-run" in command:
            raise SystemExit(2)

    def provider(*_args, **_kwargs):
        pytest.fail("An incompatible SDK must be refused before any provider work")

    monkeypatch.setenv("GH_REPO", "example/plugins")
    monkeypatch.setitem(scope, "projects", lambda: [project])
    monkeypatch.setitem(scope, "run", run)
    for name in ("validate_lock", "restore", "acceptance"):
        monkeypatch.setitem(scope, name, provider)
    with pytest.raises(SystemExit) as failure:
        compose(core, destination, "https://example.test/release")
    assert failure.value.code == 2
    assert not (destination / "standard.json").exists()


def test_the_acceptance_environment_uses_the_python_the_core_requires(tmp_path):
    core_python = runpy.run_path(str(Path(__file__).parents[1] / "scripts/compose.py"))["core_python"]
    core = tmp_path / "heinzel-0.9.45-py3-none-any.whl"
    with zipfile.ZipFile(core, "w") as archive:
        archive.writestr(
            "heinzel-0.9.45.dist-info/METADATA", "Name: heinzel\nVersion: 0.9.45\nRequires-Python: >=3.15\n"
        )
    assert core_python(core) == ["--python", ">=3.15"]
    plain = tmp_path / "heinzel-0.9.1-py3-none-any.whl"
    with zipfile.ZipFile(plain, "w") as archive:
        archive.writestr("heinzel-0.9.1.dist-info/METADATA", "Name: heinzel\nVersion: 0.9.1\n")
    assert core_python(plain) == []


@pytest.mark.parametrize("result", ["missing", "appeared", "broken-provider", "broken-core", "untrusted"])
def test_dependency_receipt_is_only_for_exact_absent_enrolled_releases(tmp_path, monkeypatch, result):
    check = runpy.run_path(str(Path(__file__).parents[1] / "scripts/compose.py"))["check_dependencies"]
    scope = check.__globals__
    repository = scope["PLUGINS_REPOSITORY"]
    commit = "a" * 40
    for key, value in {
        "GH_REPO": repository,
        "GITHUB_REPOSITORY": repository,
        "GITHUB_WORKFLOW_REF": f"{repository}/.github/workflows/compose.yml@refs/heads/main",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "schedule",
        "GITHUB_RUN_ATTEMPT": "2" if result == "untrusted" else "1",
        "GITHUB_SHA": commit,
        "GITHUB_RUN_ID": "1234",
        "RUNNER_TEMP": str(tmp_path),
        "GITHUB_OUTPUT": str(tmp_path / "output"),
    }.items():
        monkeypatch.setenv(key, value)
    selected = [
        SimpleNamespace(name=f"heinzel-{name}", version="1.2.3", options={"profiles": profiles})
        for name, profiles in [("missing", ["standard"]), ("published", ["standard"]), ("unrelated", ["other"])]
    ]
    checked = []
    restored = []

    def absent(repo, tag):
        assert repo == repository
        assert "unrelated" not in tag
        checked.append(tag)
        return "missing" in tag and (result != "appeared" or checked.count(tag) == 1)

    @contextmanager
    def core(*_):
        if result == "broken-core":
            raise ValueError("attestation failed")
        yield tmp_path / "heinzel-1.2.4-py3-none-any.whl", "b" * 40, "c" * 64

    def restore(repo, tag, name, _):
        assert (repo, tag, name) == (repository, "heinzel-published/v1.2.3", "heinzel-published")
        restored.append(tag)
        if result == "broken-provider":
            raise ValueError("wheel verification failed")

    for name, replacement in {
        "projects": lambda: selected,
        "release_absent": absent,
        "verified_core": core,
        "validate_lock": lambda *_: None,
        "restore": restore,
    }.items():
        monkeypatch.setitem(scope, name, replacement)
    arguments = ("https://example.invalid/wheel", "1.2.4")
    receipt = tmp_path / "standard-app-dependency.json"
    if result == "missing":
        with pytest.raises(SystemExit, match="Missing enrolled plugin publication"):
            check(*arguments)
        assert restored == ["heinzel-published/v1.2.3"]
        assert json.loads(receipt.read_text()) == {
            "schema": 1,
            "kind": "enrolled-plugin-publication-missing",
            "plugins_sha": commit,
            "core_version": "1.2.4",
            "core_sha": "b" * 40,
            "core_wheel_sha256": "c" * 64,
            "run_id": 1234,
            "run_attempt": 1,
            "missing": [{"name": "heinzel-missing", "version": "1.2.3", "tag": "heinzel-missing/v1.2.3"}],
        }
        assert (tmp_path / "output").read_text() == "dependency_missing=true\n"
        return
    if result.startswith("broken"):
        with pytest.raises(ValueError, match="failed"):
            check(*arguments)
    else:
        check(*arguments)
    assert not receipt.exists()
    assert not (tmp_path / "output").exists()
    if result == "untrusted":
        assert not checked


@pytest.mark.parametrize("state", ["missing", "draft", "tag-only", "unavailable"])
def test_release_absence_requires_an_accessible_repository_and_an_absent_tag(monkeypatch, state):
    check = runpy.run_path(str(Path(__file__).parents[1] / "scripts/compose.py"))["release_absent"]

    def release(*_):
        if state == "unavailable":
            raise ValueError("unavailable")
        return {"draft": True} if state == "draft" else None

    monkeypatch.setitem(check.__globals__, "find_release", release)
    monkeypatch.setitem(check.__globals__, "api", lambda *_args, **_kw: {} if state == "tag-only" else None)
    if state in {"tag-only", "unavailable"}:
        with pytest.raises(ValueError, match="exists without|unavailable"):
            check("example/plugins", "heinzel-clock/v1.2.3")
    else:
        assert check("example/plugins", "heinzel-clock/v1.2.3") is (state == "missing")


@pytest.mark.parametrize("change", ["wheel", "sdist", "tag", "unenrolled", "same"])
def test_composition_requires_restored_dependency_revision_and_both_asset_hashes(tmp_path, monkeypatch, change):
    compose = runpy.run_path(str(Path(__file__).parents[1] / "scripts/compose.py"))["compose"]
    scope = compose.__globals__
    project = SimpleNamespace(
        name="heinzel-clock", version="1.2.3", options={"profiles": ["standard"]}, directory=tmp_path
    )
    (tmp_path / "tests" / "acceptance").mkdir(parents=True)
    core = tmp_path / "core.whl"
    core.write_bytes(b"core")
    wheel = tmp_path / "heinzel_clock-1.2.3-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    sdist = tmp_path / "heinzel_clock-1.2.3.tar.gz"
    artifacts = {str(wheel): hashlib.sha256(wheel.read_bytes()).hexdigest(), str(sdist): "d" * 64}
    tag = "heinzel-clock/v1.2.3"
    pin = {"revision": "e" * 40, "assets": {Path(path).name: digest for path, digest in artifacts.items()}}
    raw = json.dumps({tag: pin}, sort_keys=True, separators=(",", ":"))
    pins = scope["parse_dependency_pins"](raw)
    if change in {"wheel", "sdist"}:
        artifacts[str(wheel if change == "wheel" else sdist)] = "f" * 64
    if change == "unenrolled":
        project.options["profiles"] = ["unrelated"]
    monkeypatch.setenv("GH_REPO", "example/plugins")
    for name, replacement in {
        "projects": lambda: [project],
        "core_python": lambda _: [],
        "validate_lock": lambda *_: None,
        "run": lambda *_a, **_kw: None,
        "check_profile_format": lambda *_a, **_kw: None,
        "profile": lambda _, _core, path, _base: path.touch(),
        "restore": lambda *_: {
            "revision": ("f" if change == "tag" else "e") * 40,
            "artifact_hashes": artifacts,
            "artifacts": list(artifacts),
        },
    }.items():
        monkeypatch.setitem(scope, name, replacement)

    def acceptance(*_args, **_kwargs):
        if change != "same":
            pytest.fail("mismatched dependency entered acceptance")
        raise RuntimeError("verified dependency reached acceptance")

    monkeypatch.setitem(scope, "acceptance", acceptance)
    if change == "same":
        with pytest.raises(RuntimeError, match="verified dependency reached acceptance"):
            compose(core, tmp_path, None, dependency_pins=pins)
    else:
        with pytest.raises(ValueError, match="differs|outside the enrolled standard profile"):
            compose(core, tmp_path, None, dependency_pins=pins)


@pytest.mark.parametrize("raw", ["{}", '{ "duplicate": 1, "duplicate": 2 }', "x" * (16 * 1024 + 1)])
def test_dependency_pin_parser_refuses_empty_noncanonical_or_oversized_inputs(raw):
    parse = runpy.run_path(str(Path(__file__).parents[1] / "scripts/compose.py"))["parse_dependency_pins"]
    with pytest.raises(ValueError, match="pin"):
        parse(raw)


@pytest.mark.parametrize(
    ("version", "tag", "wheel_tags"),
    [
        ("1.2.3", "v1.2.3", "py3-none-any"),
        ("1.2.4.dev3", "edge-v1.2.4.dev3", "py3-none-any"),
        ("1.2.3", "v1.2.3", "1-py3-none-any"),
    ],
)
def test_core_attests_private_response_before_exposing_canonical_wheel(monkeypatch, version, tag, wheel_tags):
    verify = runpy.run_path(str(Path(__file__).parents[1] / "scripts/compose.py"))["verified_core"]
    scope = verify.__wrapped__.__globals__
    repository = scope["CORE_REPOSITORY"]
    filename = f"heinzel-{version}-{wheel_tags}.whl"
    url = f"https://github.com/{repository}/releases/download/{tag}/{filename}"
    content = b"exact fetched release fixture"
    revision = "b" * 40
    digest = hashlib.sha256(content).hexdigest()
    locations = []

    def fetch(source, *, hosts, timeout, limit):
        assert source == url
        assert hosts == {"github.com"}
        assert timeout == 60
        assert limit == scope["CORE_WHEEL_LIMIT"]
        return source, content

    def peel(repo, tag_name):
        assert (repo, tag_name) == (repository, tag)
        return revision

    def attest(command):
        assert command[:3] == ["gh", "attestation", "verify"]
        assert command[4:] == ["--repo", repository, "--source-digest", revision, "--deny-self-hosted-runners"]
        temporary = Path(command[3])
        assert temporary.read_bytes() == content
        assert not (temporary.parent / filename).exists()
        locations.append(temporary.parent)

    for name, replacement in {"fetch_bytes": fetch, "tag_revision": peel, "run": attest}.items():
        monkeypatch.setitem(scope, name, replacement)
    monkeypatch.setenv("EXPECTED_CORE_SHA", revision)
    monkeypatch.setenv("EXPECTED_CORE_WHEEL_SHA256", digest)
    with verify(url, version) as (wheel, actual_revision, actual_digest):
        assert wheel.name == filename
        assert wheel.parent == locations[0]
        assert wheel.read_bytes() == content
        assert (actual_revision, actual_digest) == (revision, digest)
    assert not locations[0].exists()


@pytest.mark.parametrize("failure", ["core-revision", "wheel-digest", "attestation", "changed-after-attestation"])
def test_core_never_exposes_unverified_wheel(monkeypatch, failure):
    verify = runpy.run_path(str(Path(__file__).parents[1] / "scripts/compose.py"))["verified_core"]
    scope = verify.__wrapped__.__globals__
    repository = scope["CORE_REPOSITORY"]
    filename = "heinzel-1.2.3-py3-none-any.whl"
    url = f"https://github.com/{repository}/releases/download/v1.2.3/{filename}"
    content = b"Core release fixture"
    monkeypatch.setitem(scope, "fetch_bytes", lambda source, **_: (source, content))
    monkeypatch.setitem(scope, "tag_revision", lambda *_: "a" * 40)
    monkeypatch.setenv("EXPECTED_CORE_SHA", "b" * 40 if failure == "core-revision" else "a" * 40)
    monkeypatch.setenv(
        "EXPECTED_CORE_WHEEL_SHA256", "c" * 64 if failure == "wheel-digest" else hashlib.sha256(content).hexdigest()
    )
    locations = []

    def attest(command):
        assert failure in {"attestation", "changed-after-attestation"}
        staged = Path(command[3])
        destination = staged.parent
        assert not (destination / filename).exists()
        locations.append(destination)
        if failure == "attestation":
            raise ValueError("test attestation failed")
        staged.write_bytes(b"changed state after verification")

    monkeypatch.setitem(scope, "run", attest)
    with (
        pytest.raises(
            ValueError, match="differs from the recovery request|attestation failed|changed before composition"
        ),
        verify(url, "1.2.3"),
    ):
        pytest.fail("An unverified wheel must not be exposed")
    assert all(not location.exists() for location in locations)


@pytest.mark.parametrize("suffix", ["?source=other", "#fragment", "/alternate.whl", "\t"])
def test_core_refuses_noncanonical_url_before_downloading(monkeypatch, suffix):
    verify = runpy.run_path(str(Path(__file__).parents[1] / "scripts/compose.py"))["verified_core"]
    scope = verify.__wrapped__.__globals__
    repository = scope["CORE_REPOSITORY"]
    url = f"https://github.com/{repository}/releases/download/v1.2.3/heinzel-1.2.3-py3-none-any.whl"
    monkeypatch.setitem(scope, "fetch_bytes", lambda *a, **kw: pytest.fail("Noncanonical wheel must not be downloaded"))
    with pytest.raises(ValueError, match="official core release"), verify(url + suffix, "1.2.3"):
        pytest.fail("Noncanonical wheel must not be exposed")


@pytest.mark.parametrize("kind", ["directory-symlink", "artifact-symlink", "artifact-directory", "none"])
def test_composition_exposes_wheel_only_to_a_regular_destination(tmp_path, kind):
    copy = runpy.run_path(str(Path(__file__).parents[1] / "scripts/compose.py"))["copy_accepted_artifacts"]
    source = tmp_path / "heinzel-1.2.3-py3-none-any.whl"
    source.write_bytes(b"verified release fixture")
    destination = tmp_path / "composition"
    if kind == "directory-symlink":
        untouched = tmp_path / "other"
        untouched.mkdir()
        destination.symlink_to(untouched, target_is_directory=True)
    else:
        destination.mkdir()
    target = destination / source.name
    if kind == "artifact-symlink":
        untouched = tmp_path / "existing-fixture"
        untouched.write_bytes(b"unchanged")
        target.symlink_to(untouched)
    elif kind == "artifact-directory":
        target.mkdir()
    profile = {"artifacts": [{"url": str(source), "filename": source.name}]}
    if kind == "none":
        copy(profile, destination)
        assert target.read_bytes() == source.read_bytes()
    else:
        with pytest.raises(ValueError, match="destination must be"):
            copy(profile, destination)
    if kind == "directory-symlink":
        assert not list(untouched.iterdir())
    elif kind == "artifact-symlink":
        assert untouched.read_bytes() == b"unchanged"
