"""Verified provenance is the only route to exact upstream implementation exemptions."""

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from heinzel_plugin_tools import cli, vendor

pytestmark = pytest.mark.integration


@pytest.fixture
def vendored(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="owner-package"\nversion="1.0.0"\n'
        '[project.entry-points."heinzel.modules"]\nexample="owner"\n'
        '[build-system]\nrequires=["hatchling"]\nbuild-backend="hatchling.build"\n'
        '[tool.hatch.build.targets.wheel]\npackages=["src/owner"]\n'
        '[tool.mypy]\nstrict=true\nmypy_path=["src"]\n'
        '[tool.pyright]\ntypeCheckingMode="strict"\ninclude=["src"]\n'
        '[tool.coverage.run]\nsource=["owner"]\nbranch=true\n'
        "[tool.coverage.report]\nfail_under=90\n"
    )
    (tmp_path / "src/owner/_vendor").mkdir(parents=True)
    (tmp_path / "src/owner/__init__.py").write_text("")
    (tmp_path / "src/owner/_vendor/__init__.py").write_text("")
    wheel = tmp_path / "example_sdk-1.2.3-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("example_sdk/__init__.py", "from example_sdk.api import greet as greet\n")
        archive.writestr("example_sdk/api.py", "def greet(value: str) -> str:\n    return 3\n")
        archive.writestr("example_sdk/py.typed", "")
        archive.writestr(
            "example_sdk-1.2.3.dist-info/METADATA",
            "Name: example_sdk\nVersion: 1.2.3\nLicense: MIT\nLicense-File: LICENSE\n",
        )
        archive.writestr("example_sdk-1.2.3.dist-info/LICENSE", "MIT fixture license\n")
        archive.writestr("example_sdk-1.2.3.dist-info/RECORD", "untrusted record\n")
    vendor.generate_manifest(
        tmp_path,
        wheel,
        distribution="example_sdk",
        version="1.2.3",
        sha256=vendor.digest(wheel.read_bytes()),
        license_expression="MIT",
        license_paths=["example_sdk-1.2.3.dist-info/LICENSE"],
        source="example_sdk",
        target="owner._vendor.example_sdk",
        paths=["example_sdk/__init__.py", "example_sdk/api.py", "example_sdk/py.typed"],
    )
    return tmp_path


def manifest(root):
    return json.loads((root / vendor.MANIFEST).read_text())


def save_manifest(root, value):
    (root / vendor.MANIFEST).write_text(json.dumps(value))


def test_verified_inventory_preserves_annotations_license_marker_and_first_party(vendored):
    inventory = vendor.project(vendored)
    assert inventory.distribution == "example_sdk" and inventory.version == "1.2.3"
    assert "src/owner/_vendor/__init__.py" not in inventory.files
    assert len(inventory.files) == 4
    assert (vendored / "src/owner/_vendor/example_sdk/api.py").read_text().startswith("def greet(value: str) -> str:")
    before = {path: (vendored / path).read_bytes() for path in inventory.files}
    vendor.regenerate(vendored)
    assert before == {path: (vendored / path).read_bytes() for path in inventory.files}


@pytest.mark.parametrize(
    "mutation",
    [
        "modified",
        "missing",
        "extra",
        "native",
        "symlink",
        "hardlink",
        "fifo",
        "empty-dir",
        "sibling",
        "other-namespace",
    ],
)
def test_exact_source_inventory_fails_closed(vendored, mutation):
    path = vendored / "src/owner/_vendor/example_sdk/api.py"
    if mutation == "modified":
        path.write_text("def greet(value: str) -> str:\n    return 'changed'\n")
    elif mutation == "missing":
        path.unlink()
    elif mutation in {"extra", "native"}:
        path.with_name("extra.py" if mutation == "extra" else "extra.so").write_bytes(b"extra")
    elif mutation == "symlink":
        path.unlink()
        path.symlink_to(vendored / "pyproject.toml")
    elif mutation == "hardlink":
        os.link(path, vendored / "hardlink")
    elif mutation == "fifo":
        os.mkfifo(path.with_name("pipe"))
    elif mutation == "empty-dir":
        path.with_name("extra").mkdir()
    elif mutation == "sibling":
        path.parent.parent.joinpath("adapter.py").write_text("first_party = True\n")
    else:
        (vendored / "src/other/_vendor").mkdir(parents=True)
    with pytest.raises(ValueError, match="inventory|mismatch|symlink|Missing|Unverified"):
        vendor.project(vendored)


@pytest.mark.parametrize(
    "mutation",
    [
        "wheel",
        "original",
        "projected",
        "transform",
        "extra-key",
        "version",
        "license",
        "escape",
        "typing",
        "first-party",
    ],
)
def test_manifest_and_upstream_drift_fail_closed(vendored, mutation):
    value = manifest(vendored)
    if mutation == "wheel":
        (vendored / "vendor-provenance" / value["upstream"]["wheel"]).write_bytes(b"not a zip")
    elif mutation in {"original", "projected"}:
        value["files"][0][mutation + "_sha256"] = "0" * 64
    elif mutation == "transform":
        value["transform_version"] = "unknown"
    elif mutation == "extra-key":
        value["skip"] = True
    elif mutation in {"version", "license"}:
        value["upstream"]["version" if mutation == "version" else "license_expression"] = "other"
    elif mutation == "escape":
        value["files"][0]["target"] = "../escape.py"
    elif mutation == "typing":
        value["files"] = [entry for entry in value["files"] if not entry["source"].endswith("py.typed")]
    else:
        value["files"][0]["target"] = "src/owner/adapter.py"
    save_manifest(vendored, value)
    with pytest.raises(ValueError):
        vendor.project(vendored)


def test_wheel_sha_is_checked_before_archive_reads(vendored, monkeypatch):
    value = manifest(vendored)
    (vendored / "vendor-provenance" / value["upstream"]["wheel"]).write_bytes(b"tampered")
    monkeypatch.setattr(vendor.zipfile, "ZipFile", lambda *a, **kw: pytest.fail("unverified archive opened"))
    with pytest.raises(ValueError, match="SHA256"):
        vendor.project(vendored)


def test_import_only_projection_preserves_all_other_bytes_and_relative_imports():
    original = (
        b"# example_sdk must stay\nfrom example_sdk.api import greet\n"
        b'import example_sdk.api as api\nfrom .api import greet\ntext = "example_sdk.api"\n'
    )
    result = vendor.relocate(original, "example_sdk", "owner._vendor.example_sdk")
    assert result == original.replace(b"from example_sdk.api", b"from owner._vendor.example_sdk.api").replace(
        b"import example_sdk.api as", b"import owner._vendor.example_sdk.api as"
    )


@pytest.mark.parametrize(
    "source",
    [
        "import example_sdk\nexample_sdk.call()\n",
        "import example_sdk.api\n",
        "from importlib import import_module as load\nload('example_sdk')\n",
        "import importlib as loader\nloader.import_module('example_sdk')\n",
        "__import__('example_sdk')\n",
        "exec('import example_sdk')\n",
        "def example_sdk(): pass\n",
        "def call(example_sdk): pass\n",
        "example_sdk = 3\n",
    ],
)
def test_closed_transform_rejects_dynamic_imports_and_unexpected_identifier_rewrites(source):
    with pytest.raises(ValueError):
        vendor.relocate(source.encode(), "example_sdk", "owner._vendor.example_sdk")


def test_no_manifest_cannot_hide_vendor_tree_and_stale_inventory_cannot_exempt(vendored):
    inventory = vendor.project(vendored)
    (vendored / "src/owner/_vendor/example_sdk/api.py").write_text("changed = True\n")
    with pytest.raises(ValueError):
        with vendor.quality_command(vendored, ["ruff", "check", "src"], inventory):
            pytest.fail("stale inventory accepted")
    (vendored / vendor.MANIFEST).unlink()
    with pytest.raises(ValueError, match="manifest"):
        vendor.project(vendored)


def test_derived_exemptions_leave_strict_settings_and_coverage_floor_unchanged(vendored):
    inventory = vendor.project(vendored)
    original = (vendored / "pyproject.toml").read_bytes()
    for command in (
        ["ruff", "check", "src", "tests"],
        ["mypy", "--strict", "src"],
        ["pyright", "src"],
        ["coverage", "run", "-m", "pytest"],
        ["coverage", "report"],
    ):
        with vendor.quality_command(vendored, command, inventory) as configured:
            assert configured[:2] == command[:2] or configured[:2] == ["coverage", "run"]
            assert "src/owner/_vendor/__init__.py" not in " ".join(configured)
            if command[0] == "mypy":
                temporary = Path(configured[configured.index("--config-file") + 1])
                assert "strict=true" in temporary.read_text() and "follow_imports" not in temporary.read_text()
            if command[0] == "pyright":
                config = json.loads(Path(configured[-1]).read_text())
                assert config["typeCheckingMode"] == "strict"
                assert set(config["ignore"]) == set(inventory.python_files)
    assert original == (vendored / "pyproject.toml").read_bytes()
    assert not list(vendored.glob(".vendor-*"))


@pytest.mark.parametrize("checker", ["mypy", "pyright"])
def test_real_type_checkers_reject_invalid_consumer_calls_without_any_degradation(vendored, checker):
    executable = shutil.which(checker)
    assert executable, f"install toolkit checks extra to run {checker}"
    consumer = vendored / "src/owner/consumer.py"
    inventory = vendor.project(vendored)
    for argument, expected in [("'valid'", 0), ("123", 1)]:
        consumer.write_text(f"from owner._vendor.example_sdk import greet\nvalue: str = greet({argument})\n")
        command = [checker, *(["--strict", "--no-incremental"] if checker == "mypy" else []), "src/owner/consumer.py"]
        with vendor.quality_command(vendored, command, inventory) as configured:
            configured[0] = executable
            result = subprocess.run(configured, cwd=vendored, text=True, capture_output=True, check=False, timeout=60)  # noqa: S603 - installed checkers and isolated source fixture
        assert result.returncode == expected, result.stdout + result.stderr
        if expected:
            assert ("int" in result.stdout or "Literal[123]" in result.stdout) and "str" in result.stdout


def test_actual_built_wheel_and_tampered_artifacts(vendored):
    subprocess.run(
        [sys.executable, "-m", "hatchling", "build", "-t", "wheel"],
        cwd=vendored,
        check=True,
        capture_output=True,
        timeout=60,
    )  # noqa: S603 - local fixture build
    wheel = next((vendored / "dist").glob("*.whl"))
    vendor.verify_wheel(vendored, wheel)
    with zipfile.ZipFile(wheel) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    for mutation in ["changed", "extra", "missing", "native", "symlink", "other-namespace"]:
        altered = dict(files)
        key = "owner/_vendor/example_sdk/api.py"
        if mutation == "missing":
            del altered[key]
        elif mutation == "changed":
            altered[key] = b"modified = True\n"
        elif mutation == "other-namespace":
            altered["other/_vendor/unknown/api.py"] = b"extra"
        else:
            altered[
                "owner/_vendor/example_sdk/extra.so" if mutation == "native" else "owner/_vendor/example_sdk/extra.py"
            ] = b"extra"
        candidate = vendored / f"{mutation}.whl"
        with zipfile.ZipFile(candidate, "w") as archive:
            for name, data in altered.items():
                if mutation == "symlink" and name == key:
                    info = zipfile.ZipInfo(name)
                    info.external_attr = 0o120777 << 16
                    archive.writestr(info, data)
                else:
                    archive.writestr(name, data)
        with pytest.raises(ValueError, match="wheel"):
            vendor.verify_wheel(vendored, candidate)


@pytest.mark.parametrize("action", ["fix", "check", "build"])
def test_commands_verify_before_any_environment_format_or_build(vendored, monkeypatch, action):
    selected = cli.projects(vendored)[0]
    (vendored / "src/owner/_vendor/example_sdk/api.py").write_text("tampered=True\n")
    monkeypatch.setattr(cli, "prepare_environment", lambda *a: pytest.fail("environment before vendor verification"))
    monkeypatch.setattr(cli, "validate_lock", lambda *a: pytest.fail("lock before vendor verification"))
    monkeypatch.setattr(cli, "run", lambda *a, **kw: pytest.fail("command before vendor verification"))
    with pytest.raises(ValueError):
        getattr(cli, action)(selected, *([] if action == "build" else [None]))


@pytest.mark.parametrize("mutation", ["none", "wrong-version", "wrong-hash", "missing"])
def test_retained_dependency_must_match_exact_upstream_lock(vendored, mutation):
    value = manifest(vendored)
    project_file = vendored / "pyproject.toml"
    project_file.write_text(
        project_file.read_text().replace('version="1.0.0"', 'version="1.0.0"\ndependencies=["example-sdk>=1"]')
    )
    pin = f"example-sdk==1.2.3 --hash=sha256:{value['upstream']['sha256']}\n"
    if mutation == "wrong-version":
        pin = pin.replace("1.2.3", "1.2.4")
    elif mutation == "wrong-hash":
        pin = pin.replace(value["upstream"]["sha256"], "0" * 64)
    elif mutation == "missing":
        pin = ""
    (vendored / "requirements.lock").write_text(pin)
    if mutation == "none":
        assert vendor.project(vendored).version == "1.2.3"
    else:
        with pytest.raises(ValueError, match="lock"):
            vendor.project(vendored)


def test_vendor_stays_in_vulnerability_and_license_audit_without_external_install(vendored, monkeypatch, capsys):
    from heinzel_plugin_tools import audit

    monkeypatch.chdir(vendored)
    monkeypatch.setattr(sys, "argv", ["audit", sys.executable, "owner-package"])
    records = []

    def run(command, **options):
        if "-c" in command:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"owner-package": "1.0.0"}))
        if "pip_audit" in command:
            records.append(Path(command[command.index("-r") + 1]).read_text())
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(audit.subprocess, "run", run)
    audit.main()
    assert records == ["example_sdk==1.2.3\n"]
    report = json.loads(capsys.readouterr().out)
    assert report["license"] == "MIT" and set(report["files"]) == set(vendor.project(vendored).files)
    (vendored / ".license-allowlist").write_text("Apache\n")
    with pytest.raises(ValueError, match="license"):
        audit.main()
    (vendored / ".license-allowlist").write_text("")
    with pytest.raises(ValueError, match="license"):
        audit.main()


def test_build_automatically_rejects_unverified_wheel_contents(vendored, monkeypatch):
    selected = cli.projects(vendored)[0]
    monkeypatch.setattr(cli, "validate_lock", lambda *args: {})

    def build(*args, **kwargs):
        (vendored / "dist").mkdir()
        with zipfile.ZipFile(vendored / "dist/owner_package-1.0.0-py3-none-any.whl", "w") as archive:
            archive.writestr("owner/_vendor/example_sdk/extra.py", b"extra")

    monkeypatch.setattr(cli, "run", build)
    with pytest.raises(ValueError, match="wheel"):
        cli.build(selected)


def test_regeneration_rejects_links_before_overwriting_other_files(vendored):
    path = vendored / "src/owner/_vendor/example_sdk/api.py"
    outside = vendored / "outside.py"
    outside.write_text("must_stay = True\n")
    path.unlink()
    os.link(outside, path)
    with pytest.raises(ValueError):
        vendor.regenerate(vendored)
    assert outside.read_text() == "must_stay = True\n"


def test_real_coverage_keeps_first_party_ninety_percent_floor(vendored):
    executable = shutil.which("coverage")
    assert executable
    (vendored / "src/owner/behavior.py").write_text(
        "def choose(value: bool) -> str:\n    if value:\n        return 'yes'\n    return 'no'\n"
    )
    (vendored / "exercise.py").write_text(
        "from owner.behavior import choose\nfrom owner._vendor.example_sdk import greet\nchoose(True)\ngreet('value')\n"
    )
    inventory = vendor.project(vendored)
    environment = {**os.environ, "PYTHONPATH": str(vendored / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    for command, expected in [(["coverage", "run", "exercise.py"], 0), (["coverage", "report"], 2)]:
        with vendor.quality_command(vendored, command, inventory) as configured:
            configured[0] = executable
            result = subprocess.run(  # noqa: S603 - isolated local coverage fixture
                configured, cwd=vendored, env=environment, check=False, text=True, capture_output=True, timeout=60
            )
        assert result.returncode == expected, result.stdout + result.stderr
    assert "fail-under=90" in result.stdout
    assert "example_sdk" not in result.stdout and "behavior.py" in result.stdout


@pytest.mark.parametrize(
    "mutation",
    [
        "format",
        "bad-source",
        "bad-target",
        "renamed-package",
        "outside-owner",
        "wheel-path",
        "native-wheel",
        "bad-sha",
        "bad-distribution",
        "bad-version",
        "empty-license-paths",
        "wrong-license-paths",
        "empty-files",
        "wrong-files",
        "empty-source-path",
        "duplicate-source",
        "duplicate-target",
        "missing-initializer",
        "missing-license",
        "unsupported-source",
        "bad-module-path",
        "source-traversal",
        "bad-original-hash",
        "bad-projected-hash",
        "wrong-license-file",
    ],
)
def test_manifest_schema_and_closed_subset_rules_fail_closed(vendored, mutation):
    value = manifest(vendored)
    if mutation == "format":
        value["format"] = 2
    elif mutation in {"bad-source", "bad-target", "renamed-package", "outside-owner"}:
        key = "source" if mutation == "bad-source" else "target"
        value["package"][key] = {
            "bad-source": "bad/path",
            "bad-target": "owner.vendor.example_sdk",
            "renamed-package": "owner._vendor.other",
            "outside-owner": "other._vendor.example_sdk",
        }[mutation]
    elif mutation in {
        "wheel-path",
        "native-wheel",
        "bad-sha",
        "bad-distribution",
        "bad-version",
        "empty-license-paths",
        "wrong-license-paths",
        "wrong-license-file",
    }:
        key, new = {
            "wheel-path": ("wheel", "dir/name-none-any.whl"),
            "native-wheel": ("wheel", "example_sdk-native.whl"),
            "bad-sha": ("sha256", "bad"),
            "bad-distribution": ("distribution", "bad\nname"),
            "bad-version": ("version", "bad\nversion"),
            "empty-license-paths": ("license_paths", []),
            "wrong-license-paths": ("license_paths", "LICENSE"),
            "wrong-license-file": ("license_paths", ["example_sdk/py.typed"]),
        }[mutation]
        value["upstream"][key] = new
    elif mutation in {"empty-files", "wrong-files"}:
        value["files"] = [] if mutation == "empty-files" else {}
    elif mutation == "duplicate-source":
        value["files"].append(value["files"][0])
    elif mutation == "duplicate-target":
        value["files"][1]["target"] = value["files"][0]["target"]
    elif mutation in {"missing-initializer", "missing-license"}:
        suffix = "__init__.py" if mutation == "missing-initializer" else "LICENSE"
        value["files"] = [entry for entry in value["files"] if not entry["source"].endswith(suffix)]
    elif mutation in {"bad-original-hash", "bad-projected-hash"}:
        value["files"][0]["original_sha256" if mutation == "bad-original-hash" else "projected_sha256"] = "bad"
    else:
        value["files"][1]["source"] = {
            "empty-source-path": "",
            "unsupported-source": "other/module.so",
            "bad-module-path": "example_sdk/bad-name.py",
            "source-traversal": "../escape.py",
        }[mutation]
    save_manifest(vendored, value)
    with pytest.raises(ValueError):
        vendor.project(vendored)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "symlink",
        "traversal",
        "no-metadata",
        "two-metadata",
        "no-license-metadata",
        "missing-license-file",
        "ambiguous-license-file",
        "case-alias",
        "metadata-alias",
        "unicode-alias",
        "directory-alias",
    ],
)
def test_even_pinned_malformed_upstream_archives_are_rejected(vendored, mutation):
    value = manifest(vendored)
    wheel = vendored / "vendor-provenance" / value["upstream"]["wheel"]
    with zipfile.ZipFile(wheel) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    metadata = "example_sdk-1.2.3.dist-info/METADATA"
    if mutation == "no-metadata":
        del files[metadata]
    elif mutation == "two-metadata":
        files["other-1.0.dist-info/METADATA"] = files[metadata]
    elif mutation == "no-license-metadata":
        files[metadata] = files[metadata].replace(b"License-File: LICENSE\n", b"")
    elif mutation == "missing-license-file":
        del files["example_sdk-1.2.3.dist-info/LICENSE"]
    elif mutation == "ambiguous-license-file":
        files["example_sdk-1.2.3.dist-info/licenses/LICENSE"] = b"ambiguous"
    elif mutation == "case-alias":
        files["example_sdk/API.PY"] = b"different = True\n"
    elif mutation == "metadata-alias":
        files["example_sdk-1.2.3.dist-info/metadata"] = b"Name: foreign\nVersion: 9.9\n"
    elif mutation == "unicode-alias":
        files["example_sdk/caf\u00e9.py"] = b"one = True\n"
        files["example_sdk/cafe\u0301.py"] = b"two = True\n"
    elif mutation == "directory-alias":
        files["example_sdk/data"] = b"file"
        files["example_sdk/data/"] = b""
    elif mutation == "traversal":
        files["../escape"] = b"escape"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, data in files.items():
            if mutation == "symlink" and name.endswith("api.py"):
                info = zipfile.ZipInfo(name)
                info.external_attr = 0o120777 << 16
                archive.writestr(info, data)
            else:
                archive.writestr(name, data)
        if mutation == "duplicate":
            with pytest.warns(UserWarning, match="Duplicate"):
                archive.writestr("example_sdk/api.py", b"duplicate")
    value["upstream"]["sha256"] = vendor.digest(wheel.read_bytes())
    save_manifest(vendored, value)
    with pytest.raises(ValueError):
        vendor.project(vendored)


@pytest.mark.parametrize("path", ["../escape", "/absolute", "a/./b", "a//b", "a\\b", "bad\x00file"])
def test_unsafe_inventory_paths_are_rejected(path):
    with pytest.raises(ValueError):
        vendor.relative(path)


def test_empty_inventory_never_adds_exemptions_and_spelling_is_exact(vendored, tmp_path):
    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    empty = vendor.project(empty_root)
    assert not empty.files
    with vendor.quality_command(empty_root, ["ruff", "check", "src"], empty) as command:
        assert command == ["ruff", "check", "src"]
    with vendor.quality_command(vendored, ["typos", "."], vendor.project(vendored)) as command:
        assert command[2::2] == ["--exclude"] * 4
        assert set(command[3::2]) == set(vendor.project(vendored).files)
    with pytest.raises(ValueError):
        with vendor.quality_command(empty_root, ["ruff", "check"], vendor.VerifiedInventory(("invented.py",))):
            pytest.fail("fabricated inventory accepted")


def test_alternate_type_config_fails_closed(vendored):
    (vendored / "pyrightconfig.json").write_text("{}")
    with pytest.raises(ValueError, match="Pyright"):
        with vendor.quality_command(vendored, ["pyright", "src"], vendor.project(vendored)):
            pytest.fail("alternate configuration accepted")


def test_generation_rechecks_explicit_sha_and_existing_pin(vendored):
    value = manifest(vendored)
    wheel = vendored / "vendor-provenance" / value["upstream"]["wheel"]
    arguments = dict(
        distribution="example_sdk",
        version="1.2.3",
        license_expression="MIT",
        license_paths=value["upstream"]["license_paths"],
        source="example_sdk",
        target="owner._vendor.example_sdk",
        paths=[
            entry["source"] for entry in value["files"] if entry["source"] not in value["upstream"]["license_paths"]
        ],
    )
    with pytest.raises(ValueError, match="SHA256"):
        vendor.generate_manifest(vendored, wheel, sha256="0" * 64, **arguments)
    vendor.generate_manifest(vendored, wheel, sha256=value["upstream"]["sha256"], **arguments)
    assert vendor.project(vendored).version == "1.2.3"


def test_repository_root_cli_audit_executes_scanner_in_the_owning_project(vendored, monkeypatch, tmp_path):
    from heinzel_plugin_tools import audit

    selected = cli.projects(vendored)[0]
    repository = tmp_path / "collection"
    repository.mkdir()
    scanners = tmp_path / "scanner-fixtures"
    scanners.mkdir()
    (scanners / "piplicenses.py").write_text("")
    (scanners / "pip_audit.py").write_text(
        "import os,sys\nfrom pathlib import Path\n"
        "Path(os.environ['AUDIT_RESULT']).write_text(Path(sys.argv[sys.argv.index('-r')+1]).read_text())\n"
    )
    interpreter = tmp_path / "owning-python"
    interpreter.write_text(f'#!{sys.executable}\nprint(\'{{"owner-package":"1.0.0"}}\')\n')
    interpreter.chmod(0o755)
    result_file = tmp_path / "audited-requirements.txt"
    environment = {**os.environ, "PYTHONPATH": str(scanners), "AUDIT_RESULT": str(result_file)}
    monkeypatch.chdir(repository)
    monkeypatch.setattr(cli, "ROOT", repository)
    monkeypatch.setattr(cli, "projects", lambda: [selected])
    monkeypatch.setattr(cli, "prepare_environment", lambda *args: interpreter)
    monkeypatch.setattr(cli, "repository_private", lambda: False)
    monkeypatch.setattr(sys, "argv", ["hz-plugin", "audit", selected.name])
    reports = []

    def dispatch(command, **options):
        assert str(Path(audit.__file__)) in command
        completed = subprocess.run(  # noqa: S603 - actual trusted audit script with isolated scanner fixtures
            [sys.executable, str(Path(audit.__file__)), str(interpreter), selected.name],
            cwd=options.get("cwd", repository),
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        reports.append(json.loads(completed.stdout))

    monkeypatch.setattr(cli, "run", dispatch)
    assert cli.main() == 0
    assert result_file.read_text() == "example_sdk==1.2.3\n"
    assert reports[0]["license"] == "MIT"
    assert set(reports[0]["files"]) == set(vendor.project(vendored).files)


@pytest.mark.parametrize("mode", [0o010644, 0o020644, 0o060644, 0o140644, 0o040755])
@pytest.mark.parametrize("artifact", ["upstream", "built"])
def test_all_declared_nonregular_archive_file_types_are_rejected(vendored, mode, artifact):
    value = manifest(vendored)
    if artifact == "upstream":
        path = vendored / "vendor-provenance" / value["upstream"]["wheel"]
        with zipfile.ZipFile(path) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        key = "example_sdk/api.py"
    else:
        path = vendored / "special-file.whl"
        files = {
            entry["target"].removeprefix("src/"): (vendored / entry["target"]).read_bytes() for entry in value["files"]
        }
        key = "owner/_vendor/example_sdk/api.py"
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            info = zipfile.ZipInfo(name)
            if name == key:
                info.create_system = 3
                info.external_attr = mode << 16
            archive.writestr(info, data)
    if artifact == "upstream":
        value["upstream"]["sha256"] = vendor.digest(path.read_bytes())
        save_manifest(vendored, value)
    with pytest.raises(ValueError, match="nonregular"):
        vendor.project(vendored) if artifact == "upstream" else vendor.verify_wheel(vendored, path)


@pytest.mark.parametrize("checker", ["mypy", "pyright"])
def test_companion_stubs_are_mandatory_and_retain_precise_consumer_types(vendored, checker):
    value = manifest(vendored)
    wheel = vendored / "vendor-provenance" / value["upstream"]["wheel"]
    with zipfile.ZipFile(wheel) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    files["example_sdk/api.py"] = b"def greet(value):\n    return value\n"
    files["example_sdk/api.pyi"] = b"from .types import Label\ndef greet(value: str) -> Label: ...\n"
    files["example_sdk/types.pyi"] = b"from typing import TypeAlias\nLabel: TypeAlias = str\n"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    value["upstream"]["sha256"] = vendor.digest(wheel.read_bytes())
    for entry in value["files"]:
        original = files[entry["source"]]
        entry["original_sha256"] = vendor.digest(original)
        entry["projected_sha256"] = vendor.digest(
            vendor.relocate(original, "example_sdk", "owner._vendor.example_sdk")
            if entry["source"].endswith(".py")
            else original
        )
    save_manifest(vendored, value)
    with pytest.raises(ValueError, match="companion"):
        vendor.project(vendored)
    for source in ["example_sdk/api.pyi", "example_sdk/types.pyi"]:
        original = files[source]
        value["files"].append(
            {
                "source": source,
                "target": "src/owner/_vendor/" + source,
                "original_sha256": vendor.digest(original),
                "projected_sha256": vendor.digest(
                    vendor.relocate(original, "example_sdk", "owner._vendor.example_sdk")
                ),
            }
        )
        save_manifest(vendored, value)
        if source.endswith("api.pyi"):
            with pytest.raises(ValueError, match="typing import"):
                vendor.projection(vendored)
    vendor.regenerate(vendored)
    consumer = vendored / "src/owner/typed_consumer.py"
    for argument, expected in [("'valid'", 0), ("123", 1)]:
        consumer.write_text(f"from owner._vendor.example_sdk import greet\nvalue: str = greet({argument})\n")
        command = [
            checker,
            *(["--strict", "--no-incremental"] if checker == "mypy" else []),
            "src/owner/typed_consumer.py",
        ]
        with vendor.quality_command(vendored, command, vendor.project(vendored)) as configured:
            result = subprocess.run(configured, cwd=vendored, check=False, capture_output=True, text=True, timeout=60)  # noqa: S603 - installed checkers with isolated typed fixtures
        assert result.returncode == expected, result.stdout + result.stderr


@pytest.mark.parametrize("vendored_output", [False, True])
def test_build_checks_for_injected_vendor_code_without_a_source_manifest(tmp_path, monkeypatch, vendored_output):
    (tmp_path / "pyproject.toml").write_text('[project]\nname="owner"\nversion="1.0.0"\n')
    selected = cli.Project(tmp_path, "owner", "1.0.0", {})
    monkeypatch.setattr(cli, "validate_lock", lambda *args: {})

    def build(*args, **kwargs):
        (tmp_path / "dist").mkdir()
        with zipfile.ZipFile(tmp_path / "dist/owner-1.0.0-py3-none-any.whl", "w") as archive:
            archive.writestr("owner/_vendor/unknown.py" if vendored_output else "owner/__init__.py", "")

    monkeypatch.setattr(cli, "run", build)
    if vendored_output:
        with pytest.raises(ValueError, match="manifest"):
            cli.build(selected)
    else:
        cli.build(selected)


def test_real_wheel_license_copies_require_own_metadata_declaration_and_exact_pinned_bytes(vendored):
    source = "src/owner/_vendor/example_sdk/LICENSE"
    pyproject = vendored / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text().replace('version="1.0.0"', f'version="1.0.0"\nlicense-files=["{source}"]')
    )
    subprocess.run(  # noqa: S603 - actual local fixture wheel build
        [sys.executable, "-m", "hatchling", "build", "-t", "wheel"],
        cwd=vendored,
        check=True,
        capture_output=True,
        timeout=60,
    )
    wheel = next((vendored / "dist").glob("*.whl"))
    vendor.verify_wheel(vendored, wheel)
    with zipfile.ZipFile(wheel) as archive:
        original = {name: archive.read(name) for name in archive.namelist()}
    metadata = "owner_package-1.0.0.dist-info/METADATA"
    wheel_metadata = "owner_package-1.0.0.dist-info/WHEEL"
    copy = "owner_package-1.0.0.dist-info/licenses/" + source
    declaration = b"License-File: " + source.encode() + b"\n"
    assert original[copy] == (vendored / source).read_bytes()
    assert declaration in original[metadata]
    generator = next(
        line for line in original[wheel_metadata].splitlines(keepends=True) if line.startswith(b"Generator:")
    )
    metadata_version = next(
        line for line in original[metadata].splitlines(keepends=True) if line.startswith(b"Metadata-Version:")
    )
    tag_lines = [line for line in original[wheel_metadata].splitlines(keepends=True) if line.startswith(b"Tag:")]
    all_tags = b"".join(tag_lines)
    identities = {
        "duplicate-name": (metadata, b"Name: owner-package\n", b"Name: owner-package\nName: foreign-owner\n"),
        "repeated-name": (metadata, b"Name: owner-package\n", b"Name: owner-package\nName: owner-package\n"),
        "duplicate-version": (metadata, b"Version: 1.0.0\n", b"Version: 1.0.0\nVersion: 9.9\n"),
        "duplicate-metadata-version": (
            metadata,
            metadata_version,
            metadata_version + b"Metadata-Version: 1.0\n",
        ),
        "invalid-metadata-version": (metadata, metadata_version, b"Metadata-Version: invalid\n"),
        "duplicate-wheel-version": (
            wheel_metadata,
            b"Wheel-Version: 1.0\n",
            b"Wheel-Version: 1.0\nWheel-Version: 9.9\n",
        ),
        "invalid-wheel-version": (wheel_metadata, b"Wheel-Version: 1.0\n", b"Wheel-Version: 2.0\n"),
        "duplicate-generator": (wheel_metadata, generator, generator + generator),
        "missing-generator": (wheel_metadata, generator, b""),
        "invalid-purelib": (wheel_metadata, b"Root-Is-Purelib: true\n", b"Root-Is-Purelib: maybe\n"),
        "duplicate-purelib": (
            wheel_metadata,
            b"Root-Is-Purelib: true\n",
            b"Root-Is-Purelib: true\nRoot-Is-Purelib: false\n",
        ),
        "missing-tag": (wheel_metadata, all_tags, b""),
        "invalid-tag": (wheel_metadata, all_tags, b"Tag: garbage\n"),
        "duplicate-tag": (wheel_metadata, all_tags, all_tags + tag_lines[0]),
    }
    aliases = {
        "lowercase-metadata": metadata.removesuffix("METADATA") + "metadata",
        "mixedcase-metadata": metadata.removesuffix("METADATA") + "mEtAdAtA",
        "lowercase-wheel": wheel_metadata.removesuffix("WHEEL") + "wheel",
        "mixedcase-wheel": wheel_metadata.removesuffix("WHEEL") + "wHeEl",
    }
    for mutation in [
        "tampered",
        "missing-declaration",
        "missing-copy",
        "foreign-copy",
        "foreign-identity",
        "missing-metadata",
        "dangerous-path",
        "extra-vendor-metadata",
        "foreign-authority",
        "foreign-case-authority",
        "case-import-namespace",
        "nested-authority",
        "missing-wheel",
        "invalid-build",
        "duplicate-build",
        "first-party-case-alias",
        "unicode-canonical-alias",
        *aliases,
        *identities,
    ]:
        altered = dict(original)
        if mutation in identities:
            member, old, new = identities[mutation]
            assert old in altered[member]
            altered[member] = altered[member].replace(old, new)
        elif mutation in aliases:
            altered[aliases[mutation]] = (
                b"Metadata-Version: 2.5\nName: foreign-owner\nVersion: 9.9\n"
                if mutation.endswith("metadata")
                else b"Wheel-Version: 1.0\nGenerator: foreign\nRoot-Is-Purelib: false\nTag: py3-none-other\n"
            )
        elif mutation == "first-party-case-alias":
            altered["OWNER/__INIT__.PY"] = b"unverified = True\n"
        elif mutation == "unicode-canonical-alias":
            altered["owner/caf\u00e9.txt"] = b"one"
            altered["owner/cafe\u0301.txt"] = b"two"
        elif mutation == "foreign-authority":
            altered["foreign-9.9.dist-info/METADATA"] = b"Name: foreign\nVersion: 9.9\n"
            altered["foreign-9.9.dist-info/WHEEL"] = original[wheel_metadata]
        elif mutation == "foreign-case-authority":
            altered["FOREIGN-9.9.DIST-INFO/METADATA"] = b"Name: foreign\nVersion: 9.9\n"
            altered["FOREIGN-9.9.DIST-INFO/WHEEL"] = original[wheel_metadata]
        elif mutation == "case-import-namespace":
            altered["OWNER/_VENDOR/example_sdk/extra.py"] = b"unverified = True\n"
        elif mutation == "nested-authority":
            altered["owner_package-1.0.0.dist-info/owner_package-1.0.0.dist-info/WHEEL"] = original[wheel_metadata]
        elif mutation == "missing-wheel":
            del altered[wheel_metadata]
        elif mutation == "invalid-build":
            altered[wheel_metadata] = b"Build: invalid\n" + original[wheel_metadata]
        elif mutation == "duplicate-build":
            altered[wheel_metadata] = b"Build: 1\nBuild: 2\n" + original[wheel_metadata]
        elif mutation == "tampered":
            altered[copy] = b"different license bytes"
        elif mutation == "missing-declaration":
            altered[metadata] = altered[metadata].replace(declaration, b"")
        elif mutation == "missing-copy":
            del altered[copy]
        elif mutation == "foreign-copy":
            altered["foreign-9.9.dist-info/licenses/" + source] = altered[copy]
        elif mutation == "foreign-identity":
            altered[metadata] = altered[metadata].replace(b"Name: owner-package", b"Name: foreign")
        elif mutation == "missing-metadata":
            del altered[metadata]
        elif mutation == "dangerous-path":
            altered[copy + "/../escape"] = b"escape"
        else:
            altered[copy.removesuffix("LICENSE") + "extra.py"] = altered[copy]
            altered[metadata] = altered[metadata].replace(
                declaration, declaration + b"License-File: " + source.removesuffix("LICENSE").encode() + b"extra.py\n"
            )
        candidate = vendored / f"{mutation}-license.whl"
        with zipfile.ZipFile(candidate, "w") as archive:
            for name, data in altered.items():
                archive.writestr(name, data)
        try:
            vendor.verify_wheel(vendored, candidate)
        except ValueError:
            continue
        pytest.fail(f"Accepted invalid wheel mutation: {mutation}")
