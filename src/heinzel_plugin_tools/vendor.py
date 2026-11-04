"""Offline, exact-wheel provenance and a closed namespace-only vendor projection."""

import ast
import copy
import hashlib
import io
import json
import re
import stat
import tempfile
import tokenize
import tomllib
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from email.parser import BytesParser
from pathlib import Path, PurePosixPath

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

TRANSFORM_VERSION = "namespace-relocation-v1"
MANIFEST = "vendor-manifest.json"
SHA256 = re.compile(r"[0-9a-f]{64}")
MODULE = re.compile(r"[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*")


def digest(data: bytes) -> str:
    """Return the immutable byte identity, independent of wheel RECORD claims."""
    return hashlib.sha256(data).hexdigest()


def relative(value: str) -> str:
    """Require a canonical relative POSIX file path without traversal."""
    path = PurePosixPath(value)
    if not value or path.is_absolute() or path.as_posix() != value or any(p in {".", ".."} for p in path.parts):
        raise ValueError(f"Unsafe vendor path: {value!r}")
    if "\\" in value or "\x00" in value:
        raise ValueError("Unsafe vendor path")
    return value


def regular(root: Path, name: str) -> Path:
    """Refuse symlinks in every component, including the selected file."""
    path = root
    for part in PurePosixPath(relative(name)).parts:
        path /= part
        if path.is_symlink():
            raise ValueError(f"Vendor symlink: {name}")
    if not path.is_file() or path.stat().st_nlink != 1:
        raise ValueError(f"Missing vendor file: {name}")
    return path


def relocate(data: bytes, source: str, target: str) -> bytes:
    """Rewrite only static import prefixes, preserving all other bytes.

    Dynamic imports and namespace shadowing are outside this closed transform. An
    independently constructed AST must equal the projected AST after rewriting.
    """
    if not source.isidentifier() or not MODULE.fullmatch(target):
        raise ValueError("Unsupported namespace mapping")
    text = data.decode("utf-8")
    tree = ast.parse(text)
    edits: set[tuple[int, int]] = set()
    tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = ast.unparse(node.func)
            if name in {"__import__", "eval", "exec", "compile"} or name.endswith(
                (".import_module", ".find_spec", ".load_module", ".exec_module")
            ):
                raise ValueError("Dynamic imports/execution are outside the vendor transform")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == source:
            raise ValueError("Namespace shadowing is outside the vendor transform")
        if isinstance(node, ast.arg) and node.arg == source:
            raise ValueError("Namespace shadowing is outside the vendor transform")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in {"importlib", "builtins"}:
                    raise ValueError("Dynamic import facilities are outside the vendor transform")
                if alias.asname == source:
                    raise ValueError("Namespace alias shadowing is outside the vendor transform")
                if alias.name == source or alias.name.startswith(source + "."):
                    if alias.asname is None:
                        raise ValueError("Unaliased absolute imports are outside the vendor transform")
                    edits.add((alias.lineno, alias.col_offset))
        if isinstance(node, ast.ImportFrom) and not node.level:
            if (node.module or "").split(".")[0] in {"importlib", "builtins"}:
                raise ValueError("Dynamic import facilities are outside the vendor transform")
            if node.module == source or (node.module or "").startswith(source + "."):
                match = next(
                    token
                    for token in tokens
                    if token.type == tokenize.NAME
                    and token.string == source
                    and token.start[0] == node.lineno
                    and token.start[1] > node.col_offset
                )
                edits.add(match.start)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == source:
            raise ValueError("Namespace identifier references are outside the vendor transform")

    class Expected(ast.NodeTransformer):
        def visit_Import(self, node: ast.Import) -> ast.Import:
            for alias in node.names:
                if alias.name == source or alias.name.startswith(source + "."):
                    alias.name = target + alias.name[len(source) :]
            return node

        def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
            if not node.level and (node.module == source or (node.module or "").startswith(source + ".")):
                node.module = target + (node.module or "")[len(source) :]
            return node

    lines = text.splitlines(keepends=True)
    # AST columns are UTF-8 byte offsets; imports and references cannot silently
    # move when a preceding non-ASCII literal appears on the same line.
    for line, column in sorted(edits, reverse=True):
        raw = lines[line - 1].encode("utf-8")
        if raw[column : column + len(source)] != source.encode():
            raise ValueError("Namespace token position escaped the transform")
        lines[line - 1] = (raw[:column] + target.encode() + raw[column + len(source) :]).decode("utf-8")
    projected = "".join(lines).encode("utf-8")
    expected = Expected().visit(tree)
    if ast.dump(ast.parse(projected)) != ast.dump(expected):
        raise ValueError("Namespace projection changed program logic")
    return projected


@dataclass(frozen=True)
class Entry:
    """One upstream file and its mechanically projected byte identity."""

    source: str
    target: str
    original_sha256: str
    projected_sha256: str


@dataclass(frozen=True)
class VerifiedInventory:
    """Ephemeral result created only after provenance and exact inventory verification."""

    files: tuple[str, ...] = ()
    distribution: str = ""
    version: str = ""
    license_expression: str = ""

    @property
    def python_files(self) -> tuple[str, ...]:
        return tuple(path for path in self.files if path.endswith((".py", ".pyi")))


def mapping(value: object, keys: set[str]) -> dict[str, object]:
    """Validate a schema object without trusting JSON's dynamic types."""
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"Vendor manifest requires exactly {sorted(keys)}")
    return dict(value)


def string(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("Vendor manifest needs a nonempty string")
    return value


def strings(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("Vendor manifest needs a nonempty list")
    return [string(item) for item in value]


def projection(root: Path) -> tuple[VerifiedInventory, dict[str, bytes]]:
    """Verify the pinned upstream archive before reading any member, then regenerate."""
    manifest = mapping(
        json.loads(regular(root, MANIFEST).read_bytes()),
        {"format", "transform_version", "upstream", "package", "files"},
    )
    if manifest["format"] != 1 or manifest["transform_version"] != TRANSFORM_VERSION:
        raise ValueError("Unsupported vendor manifest/transform version")
    upstream = mapping(
        manifest["upstream"], {"distribution", "version", "wheel", "sha256", "license_paths", "license_expression"}
    )
    source_package = mapping(manifest["package"], {"source", "target"})
    source, target = string(source_package["source"]), string(source_package["target"])
    if not source.isidentifier() or not MODULE.fullmatch(target) or target.split(".")[1:-1] != ["_vendor"]:
        raise ValueError("Vendor target must be an owning package's _vendor namespace")
    if target.split(".")[-1] != source:
        raise ValueError("Vendor namespace must preserve the upstream package name")
    target_root = "src/" + target.replace(".", "/")
    metadata = tomllib.loads(regular(root, "pyproject.toml").read_text())
    owners = metadata.get("project", {}).get("entry-points", {}).get("heinzel.modules", {})
    if target.split(".")[0] not in {value.split(":")[0].split(".")[0] for value in owners.values()}:
        raise ValueError("Vendor target is outside the owning entry-point namespace")
    wheel_name = relative(string(upstream["wheel"]))
    if "/" in wheel_name or not wheel_name.endswith("-none-any.whl"):
        raise ValueError("Vendor provenance needs a wheel basename")
    wheel = regular(root, "vendor-provenance/" + wheel_name).read_bytes()
    if not SHA256.fullmatch(string(upstream["sha256"])) or digest(wheel) != upstream["sha256"]:
        raise ValueError("Upstream wheel SHA256 mismatch")
    distribution, version = string(upstream["distribution"]), string(upstream["version"])
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", distribution) or not re.fullmatch(
        r"[a-zA-Z0-9][a-zA-Z0-9.!+_-]*", version
    ):
        raise ValueError("Invalid upstream audit identity")
    locked_upstream(
        root,
        [string(value) for value in metadata.get("project", {}).get("dependencies", [])],
        distribution,
        version,
        string(upstream["sha256"]),
    )
    license_expression = string(upstream["license_expression"])
    license_paths = {relative(path) for path in strings(upstream["license_paths"])}
    raw_entries = manifest["files"]
    if not isinstance(raw_entries, list) or not raw_entries:
        raise ValueError("Empty vendor inventory")
    entries = []
    for raw_entry in raw_entries:
        entry_fields = mapping(raw_entry, {"source", "target", "original_sha256", "projected_sha256"})
        entries.append(Entry(**{key: string(value) for key, value in entry_fields.items()}))
    if len({entry.source for entry in entries}) != len(entries) or len({entry.target for entry in entries}) != len(
        entries
    ):
        raise ValueError("Duplicate vendor inventory entry")
    expected: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(wheel)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate upstream archive member")
        for info in archive.infolist():
            relative(info.filename.rstrip("/"))
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("Upstream archive symlink")
        metadata_paths = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_paths) != 1:
            raise ValueError("Upstream wheel needs one distribution identity")
        upstream_metadata = BytesParser().parsebytes(archive.read(metadata_paths[0]))
        if upstream_metadata["Name"] != distribution or upstream_metadata["Version"] != version:
            raise ValueError("Upstream distribution/version mismatch")
        if license_expression not in {upstream_metadata["License-Expression"], upstream_metadata["License"]}:
            raise ValueError("Upstream license identity mismatch")
        declared_licenses = upstream_metadata.get_all("License-File", [])
        required_licenses = set()
        metadata_root = metadata_paths[0].removesuffix("METADATA")
        for declared_license in declared_licenses:
            name = relative(declared_license)
            candidates = {metadata_root + name, metadata_root + "licenses/" + name} & set(names)
            if len(candidates) != 1:
                raise ValueError("Upstream license metadata has missing/ambiguous files")
            required_licenses.update(candidates)
        if not required_licenses or license_paths != required_licenses:
            raise ValueError("Vendor licenses must exactly retain upstream License-File metadata")
        if not license_paths <= set(names) or not license_paths <= {entry.source for entry in entries}:
            raise ValueError("Upstream license missing from exact inventory")
        if source + "/__init__.py" not in {entry.source for entry in entries}:
            raise ValueError("Upstream package initializer missing")
        if source + "/py.typed" in names and source + "/py.typed" not in {entry.source for entry in entries}:
            raise ValueError("Upstream typing marker must be retained")
        for entry in entries:
            relative(entry.source)
            relative(entry.target)
            is_license = entry.source in license_paths
            if is_license:
                required_target = target_root + "/" + PurePosixPath(entry.source).name
            elif entry.source.startswith(source + "/") and entry.source.endswith((".py", ".pyi", "/py.typed")):
                parts = PurePosixPath(entry.source).parts
                if any(not part.isidentifier() for part in parts[:-1]) or (
                    parts[-1] != "py.typed" and not PurePosixPath(parts[-1]).stem.isidentifier()
                ):
                    raise ValueError("Unsupported upstream module path")
                required_target = target_root + entry.source[len(source) :]
            else:
                raise ValueError("Unsupported/native file outside upstream source subset")
            if entry.target != required_target:
                raise ValueError("Vendor target is not an exact namespace relocation")
            original = archive.read(entry.source)
            if not SHA256.fullmatch(entry.original_sha256) or digest(original) != entry.original_sha256:
                raise ValueError("Original vendor file hash mismatch")
            projected = relocate(original, source, target) if entry.source.endswith((".py", ".pyi")) else original
            if not SHA256.fullmatch(entry.projected_sha256) or digest(projected) != entry.projected_sha256:
                raise ValueError("Projected vendor file hash/transform mismatch")
            expected[entry.target] = projected
    return VerifiedInventory(tuple(sorted(expected)), distribution, version, license_expression), expected


def locked_upstream(root: Path, dependencies: list[str], distribution: str, version: str, sha256: str) -> None:
    """Bind a retained external dependency to the same wheel and upstream version."""
    name = canonicalize_name(distribution)
    declared = any(canonicalize_name(Requirement(value).name) == name for value in dependencies)
    lock = root / "requirements.lock"
    found = False
    if lock.exists():
        text = regular(root, "requirements.lock").read_text().replace("\\\n", " ")
        for line in text.splitlines():
            if not re.match(r"[a-zA-Z0-9]", line):
                continue
            requirement_text = line.split("--hash=", 1)[0].strip()
            requirement = Requirement(requirement_text)
            if canonicalize_name(requirement.name) == name:
                found = True
                if str(requirement.specifier) != f"=={version}" or f"--hash=sha256:{sha256}" not in line:
                    raise ValueError("Vendor upstream differs from owning hashed dependency lock")
    if declared and not found:
        raise ValueError("Retained vendor dependency requires an exact owning hashed lock")


def project(root: Path) -> VerifiedInventory:
    """Return exact exemptions only after every on-disk vendor byte is verified."""
    if not (root / MANIFEST).exists() and not (root / MANIFEST).is_symlink():
        if any((root / "src").glob("*/_vendor")):
            raise ValueError("Vendor tree requires a verified manifest")
        return VerifiedInventory()
    inventory, expected = projection(root)
    target_root = PurePosixPath(next(iter(expected))).parts[:4]
    # All targets have the identical src/owner/_vendor/upstream root.
    tree = root.joinpath(*target_root)
    for namespace in (root / "src").glob("*/_vendor"):
        if namespace != tree.parent:
            raise ValueError("Unverified additional vendor namespace")
    for path in tree.parent.iterdir():
        if path != tree and path != tree.parent / "__init__.py":
            raise ValueError("Unverified additional vendor file")
    if (tree.parent / "__init__.py").exists() or (tree.parent / "__init__.py").is_symlink():
        regular(root, (tree.parent / "__init__.py").relative_to(root).as_posix())
    actual = set()
    directories = {parent for name in expected for parent in (root / name).parents if parent.is_relative_to(tree)}
    for path in tree.rglob("*"):
        if path.is_symlink():
            raise ValueError("Vendor inventory contains a symlink")
        if not path.is_dir() and (not path.is_file() or path.stat().st_nlink != 1):
            raise ValueError("Vendor inventory contains a linked/nonregular file")
        if path.is_dir() and path not in directories:
            raise ValueError("Vendor inventory contains an extra directory")
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != set(expected):
        raise ValueError("Vendor exact inventory has missing/extra files")
    for name, data in expected.items():
        if regular(root, name).read_bytes() != data:
            raise ValueError("Vendor byte mismatch")
    return inventory


@contextmanager
def quality_command(root: Path, command: list[str], inventory: VerifiedInventory) -> Iterator[list[str]]:
    """Suppress implementation diagnostics only for successfully verified exact files.

    Imported symbol analysis remains enabled in both type checkers. The owning
    strict settings, first-party paths and coverage floor are copied unchanged.
    """
    if project(root) != inventory:
        raise ValueError("Vendor inventory changed before quality command")
    files = inventory.python_files
    if not files:
        yield command
        return
    configured = list(command)
    temporary: Path | None = None
    try:
        if command[0] == "ruff":
            configured += ["--extend-exclude", ",".join(files)]
        elif command[0] == "mypy":
            modules = [
                path.removeprefix("src/")
                .removesuffix(".pyi")
                .removesuffix(".py")
                .replace("/", ".")
                .removesuffix(".__init__")
                for path in files
            ]
            content = (root / "pyproject.toml").read_text()
            content += "\n[[tool.mypy.overrides]]\nmodule = " + json.dumps(modules) + "\nignore_errors = true\n"
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".toml", prefix=".vendor-mypy-", dir=root, delete=False
            ) as stream:
                temporary = Path(stream.name)
                stream.write(content)
            configured += [
                "--config-file",
                str(temporary),
                "--exclude",
                "^(?:" + "|".join(re.escape(path) for path in files) + ")$",
            ]
        elif command[0] == "pyright":
            metadata = tomllib.loads((root / "pyproject.toml").read_text())
            config = copy.deepcopy(metadata.get("tool", {}).get("pyright", {}))
            # An alternate config could otherwise silently override the owning policy.
            if (root / "pyrightconfig.json").exists():
                raise ValueError("Vendor policy requires owning Pyright settings in pyproject.toml")
            config["ignore"] = [*config.get("ignore", []), *files]
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", prefix=".vendor-pyright-", dir=root, delete=False
            ) as stream:
                temporary = Path(stream.name)
                json.dump(config, stream)
            configured += ["--project", str(temporary)]
        elif command[:2] == ["coverage", "run"]:
            metadata = tomllib.loads((root / "pyproject.toml").read_text())
            existing = metadata.get("tool", {}).get("coverage", {}).get("run", {}).get("omit", [])
            configured.insert(2, "--omit=" + ",".join([*existing, *files]))
        elif command[:2] == ["coverage", "report"]:
            metadata = tomllib.loads((root / "pyproject.toml").read_text())
            existing = metadata.get("tool", {}).get("coverage", {}).get("report", {}).get("omit", [])
            configured += ["--omit=" + ",".join([*existing, *files])]
        elif command[0] == "typos":
            for path in inventory.files:
                configured += ["--exclude", path]
        yield configured
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def regenerate(root: Path) -> None:
    """Generate reviewed pinned projection; never delete unexpected existing files."""
    _, expected = projection(root)
    for name in expected:
        path = root / name
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError("Vendor generation cannot traverse symlinks")
        if path.exists():
            regular(root, name)
    for name, data in expected.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    project(root)


def verify_wheel(root: Path, wheel: Path) -> VerifiedInventory:
    """Verify source first, then the exact projected inventory in the built wheel."""
    inventory = project(root)
    if not inventory.files:
        return inventory
    _, expected = projection(root)
    packed = {name.removeprefix("src/"): data for name, data in expected.items()}
    prefix = "/".join(next(iter(packed)).split("/")[:3]) + "/"
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Built wheel has duplicate files")
        actual = {name for name in names if name.startswith(prefix) and not name.endswith("/")}
        if actual != set(packed):
            raise ValueError("Built wheel vendor inventory mismatch")
        parent = prefix.rsplit("/", 2)[0] + "/"
        if any(
            "_vendor" in PurePosixPath(name).parts
            and not name.startswith(prefix)
            and name not in {parent, parent + "__init__.py"}
            for name in names
        ):
            raise ValueError("Built wheel has an unverified vendor namespace")
        directories = {str(parent) + "/" for name in packed for parent in PurePosixPath(name).parents}
        for info in archive.infolist():
            if info.filename.startswith(prefix):
                if stat.S_ISLNK(info.external_attr >> 16) or (
                    info.filename.endswith("/") and info.filename not in directories
                ):
                    raise ValueError("Built wheel vendor nonregular/extra directory")
        for name, data in packed.items():
            if stat.S_ISLNK(archive.getinfo(name).external_attr >> 16) or archive.read(name) != data:
                raise ValueError("Built wheel vendor byte/type mismatch")
    return inventory


def generate_manifest(
    root: Path,
    wheel: Path,
    *,
    distribution: str,
    version: str,
    sha256: str,
    license_expression: str,
    license_paths: list[str],
    source: str,
    target: str,
    paths: list[str],
) -> None:
    """Generate explicitly pinned inventory and projection from a local upstream wheel.

    The caller supplies a separately obtained upstream SHA256, never a RECORD hash.
    No network, dependency resolution, or upstream code execution occurs here.
    """
    data = regular(wheel.parent, wheel.name).read_bytes()
    if not SHA256.fullmatch(sha256) or digest(data) != sha256:
        raise ValueError("Explicit upstream wheel SHA256 mismatch")
    entries = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for path in sorted(paths + license_paths):
            relative(path)
            original = archive.read(path)
            projected = relocate(original, source, target) if path.endswith((".py", ".pyi")) else original
            suffix = "/" + PurePosixPath(path).name if path in license_paths else path[len(source) :]
            entries.append(
                {
                    "source": path,
                    "target": "src/" + target.replace(".", "/") + suffix,
                    "original_sha256": digest(original),
                    "projected_sha256": digest(projected),
                }
            )
    manifest = {
        "format": 1,
        "transform_version": TRANSFORM_VERSION,
        "upstream": {
            "distribution": distribution,
            "version": version,
            "wheel": wheel.name,
            "sha256": sha256,
            "license_paths": license_paths,
            "license_expression": license_expression,
        },
        "package": {"source": source, "target": target},
        "files": entries,
    }
    destination = root / "vendor-provenance" / wheel.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink() or destination.parent.is_symlink() or (root / MANIFEST).is_symlink():
        raise ValueError("Vendor provenance cannot traverse symlinks")
    if destination.exists():
        regular(root, "vendor-provenance/" + wheel.name)
    if (root / MANIFEST).exists():
        regular(root, MANIFEST)
    destination.write_bytes(data)
    (root / MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    regenerate(root)
