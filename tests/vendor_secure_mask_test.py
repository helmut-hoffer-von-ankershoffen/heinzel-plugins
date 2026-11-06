"""Only three exact upstream members can receive the verifier-owned transport security repair."""

import ast
import copy
import json
import shutil
import zipfile
from pathlib import Path

import pytest

from heinzel_plugin_tools import vendor

pytestmark = pytest.mark.integration
MASK_PATH = "slack_sdk/socket_mode/builtin/internals.py"
PROXY_PATH = "slack_sdk/proxy_env_variable_loader.py"
SLACK = Path(__file__).resolve().parents[1] / "plugins/heinzel-slack"


@pytest.fixture
def secured(tmp_path):
    root = tmp_path / "plugin"
    root.mkdir()
    for name in ("pyproject.toml", "requirements.lock", vendor.MANIFEST):
        shutil.copyfile(SLACK / name, root / name)
    shutil.copytree(SLACK / "vendor-provenance", root / "vendor-provenance")
    shutil.copytree(SLACK / "src", root / "src", ignore=shutil.ignore_patterns("__pycache__"))
    return root


def manifest(root):
    return json.loads((root / vendor.MANIFEST).read_bytes())


def save(root, value):
    (root / vendor.MANIFEST).write_text(json.dumps(value))


def original(root, path=MASK_PATH):
    with zipfile.ZipFile(root / "vendor-provenance" / vendor.SLACK_SECURITY_WHEEL) as archive:
        return archive.read(path)


def test_exact_projection_preserves_upstream_and_scopes_mask_entropy_change(secured):
    value = manifest(secured)
    assert value["transform_version"] == vendor.SLACK_SECURITY_TRANSFORM
    raw = original(secured)
    patched = vendor.repair_security_member(MASK_PATH, raw)
    assert vendor.digest(raw) == vendor.SLACK_SECURITY_PATCHES[MASK_PATH][0]
    assert vendor.digest(patched) == vendor.SLACK_SECURITY_PATCHES[MASK_PATH][1]
    before, after = ast.parse(raw), ast.parse(patched)
    function = next(
        n for n in before.body if isinstance(n, ast.FunctionDef) and n.name == "_build_data_frame_for_sending"
    )
    # Mask entropy is the only change in this function; compare independently of the replacement.
    masks = [n for n in function.body if isinstance(n, ast.AnnAssign) and ast.unparse(n.target) == "mask_key"]
    assert len(masks) == 1
    assert ast.unparse(masks[0].value) == "random.choices(range(256), k=4)"
    masks[0].value = ast.parse("list(os.urandom(4))", mode="eval").body
    patched_function = next(n for n in after.body if isinstance(n, ast.FunctionDef) and n.name == function.name)
    assert ast.dump(function) == ast.dump(patched_function)
    inventory = vendor.project(secured)
    for entry in value["files"]:
        if entry["source"] in vendor.SLACK_SECURITY_PATCHES:
            hashes = vendor.SLACK_SECURITY_PATCHES[entry["source"]]
            assert entry["original_sha256"] == hashes[0]
            with zipfile.ZipFile(secured / "vendor-provenance" / vendor.SLACK_SECURITY_WHEEL) as archive:
                repaired = vendor.repair_security_member(entry["source"], archive.read(entry["source"]))
            assert vendor.digest(repaired) == hashes[1]
            assert entry["projected_sha256"] == vendor.digest(
                vendor.relocate(repaired, "slack_sdk", vendor.SLACK_SECURITY_OWNER)
            )
        else:
            with zipfile.ZipFile(secured / "vendor-provenance" / vendor.SLACK_SECURITY_WHEEL) as archive:
                member = archive.read(entry["source"])
            expected = (
                vendor.relocate(member, "slack_sdk", vendor.SLACK_SECURITY_OWNER)
                if entry["source"].endswith(".py")
                else member
            )
            assert (secured / entry["target"]).read_bytes() == expected
    before_files = {name: (secured / name).read_bytes() for name in inventory.files}
    vendor.regenerate(secured)
    assert before_files == {name: (secured / name).read_bytes() for name in inventory.files}


@pytest.mark.parametrize(
    "change",
    [
        "mode",
        "unknown-mode",
        "wheel-name",
        "wheel-hash",
        "version",
        "distribution",
        "owner",
        "source",
        "member-missing",
        "proxy-member-missing",
        "member-target",
        "original-hash",
        "projected-hash",
        "parameters",
    ],
)
def test_manifest_cannot_redirect_disable_or_reconfigure_the_security_repair(secured, change):
    value = manifest(secured)
    member = next(e for e in value["files"] if e["source"] == MASK_PATH)
    if change == "mode":
        value["transform_version"] = vendor.TRANSFORM_VERSION
        member["projected_sha256"] = vendor.SLACK_SECURITY_PATCHES[MASK_PATH][0]
        (secured / member["target"]).write_bytes(original(secured))
    elif change == "unknown-mode":
        value["transform_version"] += "+other"
    elif change == "wheel-name":
        value["upstream"]["wheel"] = "other.whl"
    elif change == "wheel-hash":
        value["upstream"]["sha256"] = "0" * 64
    elif change in {"version", "distribution"}:
        value["upstream"][change] = "other"
    elif change in {"owner", "source"}:
        value["package"]["target" if change == "owner" else "source"] = (
            "other._vendor.slack_sdk" if change == "owner" else "other"
        )
    elif change == "member-missing":
        value["files"].remove(member)
    elif change == "proxy-member-missing":
        value["files"] = [entry for entry in value["files"] if entry["source"] != PROXY_PATH]
    elif change == "member-target":
        member["target"] = "src/heinzel_slack/adapter.py"
    elif change in {"original-hash", "projected-hash"}:
        member[change.replace("-hash", "_sha256")] = "0" * 64
    else:
        value["patch"] = {"replace": "anything"}
    save(secured, value)
    with pytest.raises(ValueError):
        vendor.project(secured)


@pytest.mark.parametrize(
    "replacement",
    [
        b"",
        b"random.randbytes(4)",
        b"list(os.urandom(3))",
        b"[0, 0, 0, 0]",
        b"list(os.urandom(4))",
        b"random.choices(range(256), k=4) # changed",
    ],
)
def test_changed_upstream_member_cannot_acquire_security_patch_authority(secured, replacement):
    raw = original(secured).replace(b"random.choices(range(256), k=4)", replacement)
    with pytest.raises(ValueError, match="preimage"):
        vendor.repair_security_member(MASK_PATH, raw)


@pytest.mark.parametrize("change", ["original", "other-statement", "duplicate-statement", "symlink", "extra"])
def test_source_inventory_stays_exact_after_the_security_patch(secured, change):
    path = secured / "src/heinzel_slack/_vendor" / MASK_PATH
    if change == "original":
        path.write_bytes(original(secured))
    elif change == "other-statement":
        path.write_bytes(path.read_bytes().replace(b"import errno", b"import errno # changed"))
    elif change == "duplicate-statement":
        path.write_bytes(path.read_bytes() + b"\nmask_key = [0, 0, 0, 0]\n")
    elif change == "symlink":
        path.unlink()
        path.symlink_to(secured / "pyproject.toml")
    else:
        path.with_name("extra.py").write_text("value = 1\n")
    with pytest.raises(ValueError):
        vendor.project(secured)


def test_security_transform_cannot_be_selected_for_an_unaffected_project(secured):
    value = manifest(secured)
    upstream = copy.deepcopy(value["upstream"])
    assert (
        vendor.required_transform(upstream, "slack_sdk", "other._vendor.slack_sdk", "other") == vendor.TRANSFORM_VERSION
    )
    with pytest.raises(ValueError, match="Unsupported"):
        vendor.projected_member(
            b"value = 1\n", "example_sdk/api.py", "example_sdk", "owner._vendor.example_sdk", "custom"
        )


def test_original_wheel_must_remain_the_pinned_upstream_archive(secured):
    wheel = secured / "vendor-provenance" / vendor.SLACK_SECURITY_WHEEL
    wheel.write_bytes(wheel.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="SHA256"):
        vendor.project(secured)


def test_rebuilt_wheel_cannot_restore_the_original_weak_mask(secured):
    inventory, expected = vendor.projection(secured)
    wheel = secured / "artifact.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "heinzel_slack-0.1.0.dist-info/METADATA", "Metadata-Version: 2.4\nName: heinzel-slack\nVersion: 0.1.0\n"
        )
        archive.writestr(
            "heinzel_slack-0.1.0.dist-info/WHEEL",
            "Wheel-Version: 1.0\nGenerator: fixture\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        for path, data in expected.items():
            archive.writestr(path.removeprefix("src/"), data)
    assert vendor.verify_wheel(secured, wheel) == inventory
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "heinzel_slack-0.1.0.dist-info/METADATA", "Metadata-Version: 2.4\nName: heinzel-slack\nVersion: 0.1.0\n"
        )
        archive.writestr(
            "heinzel_slack-0.1.0.dist-info/WHEEL",
            "Wheel-Version: 1.0\nGenerator: fixture\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        for path, data in expected.items():
            archive.writestr(path.removeprefix("src/"), original(secured) if path.endswith(MASK_PATH) else data)
    with pytest.raises(ValueError, match="byte/type mismatch"):
        vendor.verify_wheel(secured, wheel)


@pytest.mark.parametrize("path", list(vendor.SLACK_SECURITY_PATCHES))
def test_wrong_postimage_is_rejected_even_if_manifest_claims_it(secured, path):
    value = manifest(secured)
    member = next(e for e in value["files"] if e["source"] == path)
    member["projected_sha256"] = vendor.digest(original(secured, path))
    (secured / member["target"]).write_bytes(original(secured, path))
    save(secured, value)
    with pytest.raises(ValueError, match="Projected vendor file"):
        vendor.project(secured)


def test_generator_deterministically_selects_mandatory_security_policy(secured):
    value = manifest(secured)
    upstream = value["upstream"]
    vendor.generate_manifest(
        secured,
        secured / "vendor-provenance" / upstream["wheel"],
        distribution=upstream["distribution"],
        version=upstream["version"],
        sha256=upstream["sha256"],
        license_expression=upstream["license_expression"],
        license_paths=upstream["license_paths"],
        source=value["package"]["source"],
        target=value["package"]["target"],
        paths=[entry["source"] for entry in value["files"] if entry["source"] not in upstream["license_paths"]],
    )
    assert manifest(secured) == value
    vendor.project(secured)


@pytest.mark.parametrize("change", ["distribution-alias", "version", "wheel-hash"])
def test_coherent_repacked_upstream_cannot_disable_mandatory_namespace_repair(secured, monkeypatch, change):
    value = manifest(secured)
    wheel = secured / "vendor-provenance" / value["upstream"]["wheel"]
    with zipfile.ZipFile(wheel) as archive:
        members = {entry.filename: archive.read(entry) for entry in archive.infolist()}
    metadata = next(path for path in members if path.endswith(".dist-info/METADATA"))
    if change == "distribution-alias":
        value["upstream"]["distribution"] = "slack-sdk"
        members[metadata] = members[metadata].replace(b"Name: slack_sdk", b"Name: slack-sdk")
    elif change == "version":
        value["upstream"]["version"] = "3.46.1"
        members[metadata] = members[metadata].replace(b"Version: 3.46.0", b"Version: 3.46.1")
        for name in ("pyproject.toml", "requirements.lock"):
            path = secured / name
            path.write_text(path.read_text().replace("slack-sdk==3.46.0", "slack-sdk==3.46.1"))
    else:
        members[metadata] += b"\nRepacked fixture\n"
    with zipfile.ZipFile(wheel, "w") as archive:
        for path, content in members.items():
            archive.writestr(path, content)
    new_hash = vendor.digest(wheel.read_bytes())
    lock = secured / "requirements.lock"
    lock.write_text(
        lock.read_text().replace(
            value["upstream"]["sha256"], value["upstream"]["sha256"] + " --hash=sha256:" + new_hash
        )
    )
    value["upstream"]["sha256"] = new_hash
    value["transform_version"] = vendor.TRANSFORM_VERSION
    for entry in value["files"]:
        raw = members[entry["source"]]
        projected = (
            vendor.relocate(raw, "slack_sdk", vendor.SLACK_SECURITY_OWNER) if entry["source"].endswith(".py") else raw
        )
        entry["original_sha256"] = vendor.digest(raw)
        entry["projected_sha256"] = vendor.digest(projected)
        (secured / entry["target"]).write_bytes(projected)
    save(secured, value)
    # Prove this is a coherent namespace-only fixture, not rejection by an unrelated
    # archive, dependency, inventory or byte mismatch later in verification.
    with monkeypatch.context() as baseline:
        baseline.setattr(vendor, "required_transform", lambda *_args: vendor.TRANSFORM_VERSION)
        vendor.project(secured)
    with pytest.raises(ValueError, match="exact approved upstream wheel"):
        vendor.project(secured)
    upstream = value["upstream"]
    with pytest.raises(ValueError, match="exact approved upstream wheel"):
        vendor.generate_manifest(
            secured,
            wheel,
            distribution=upstream["distribution"],
            version=upstream["version"],
            sha256=upstream["sha256"],
            license_expression=upstream["license_expression"],
            license_paths=upstream["license_paths"],
            source="slack_sdk",
            target=vendor.SLACK_SECURITY_OWNER,
            paths=[entry["source"] for entry in value["files"] if entry["source"] not in upstream["license_paths"]],
        )


@pytest.mark.parametrize("owner", ["heinzel-slack", "heinzel_slack", "Heinzel.Slack"])
def test_owning_slack_project_cannot_move_namespace_to_disable_security_policy(secured, owner):
    upstream = manifest(secured)["upstream"]
    with pytest.raises(ValueError, match="exact approved upstream wheel"):
        vendor.required_transform(upstream, "slack_sdk", "other._vendor.slack_sdk", owner)


@pytest.mark.parametrize("path", list(vendor.SLACK_SECURITY_PATCHES))
def test_every_security_member_is_mandatory_and_rejects_preimage_drift(secured, path):
    value = manifest(secured)
    value["files"] = [entry for entry in value["files"] if entry["source"] != path]
    save(secured, value)
    with pytest.raises(ValueError, match="member is missing"):
        vendor.project(secured)
    with pytest.raises(ValueError, match="preimage"):
        vendor.repair_security_member(path, original(secured, path) + b"\n")
