"""Offline exact-wheel provenance, namespace relocation and one pinned security repair."""

import ast
import copy
import hashlib
import io
import json
import re
import stat
import tempfile
import textwrap
import tokenize
import tomllib
import unicodedata
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from email.parser import BytesParser
from pathlib import Path, PurePosixPath

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

TRANSFORM_VERSION = "namespace-relocation-v1"
SLACK_SECURITY_TRANSFORM = "namespace-relocation-v1+slack-sdk-3.46.0-security-v2"
SLACK_SECURITY_OWNER = "heinzel_slack._vendor.slack_sdk"
SLACK_SECURITY_WHEEL = "slack_sdk-3.46.0-py2.py3-none-any.whl"
SLACK_SECURITY_WHEEL_SHA256 = "6286d89da97ea193c853609131515e6f1b3edf86866d6e5aad0dba9dcf1cb72d"
SLACK_SECURITY_PATCHES = {
    "slack_sdk/socket_mode/builtin/internals.py": (
        "e98b873e92e58f5909229030441e78da4820f47c74ed4e5eea9717917a5ed861",
        "dce0a5f17a119ff01dbe9e5648ac5784b7ee8187153b9604600236d5a61bdab4",
        (
            (
                "_build_data_frame_for_sending",
                "    mask_key: List[int] = random.choices(range(256), k=4)",
                "    mask_key: List[int] = list(os.urandom(4))",
            ),
            (
                "_establish_new_socket_connection",
                '            logger.debug(f"Proxy connect request (session id: {session_id}):\\n{req}")',
                '            logger.debug(f"Proxy connect request sent (session id: {session_id})")',
            ),
            (
                "_establish_new_socket_connection",
                "        status, text = _parse_connect_response(sock)",
                "        try:\n"
                "            status, text = _parse_connect_response(sock)\n"
                "        except (ValueError, IndexError):\n"
                '            raise ConnectionError("Malformed proxy CONNECT response") from None',
            ),
            (
                "_establish_new_socket_connection",
                '            log_message = f"Proxy connect response (session id: {session_id}):\\n{text}"',
                '            log_message = f"Proxy connect response (session id: {session_id}, status: {status})"',
            ),
            (
                "_establish_new_socket_connection",
                '            raise Exception(f"Failed to connect to the proxy '
                '(proxy: {proxy}, connect status code: {status})")',
                '            raise Exception(f"Failed to connect to the proxy (connect status code: {status})")',
            ),
            (
                "_establish_new_socket_connection",
                "    if server_port != 443:\n"
                "        # only for library testing\n"
                '        logger.info(f"Using non-ssl socket to connect '
                '({server_hostname}:{server_port})")\n'
                "        sock = socket.create_connection((server_hostname, "
                "server_port), timeout=3)\n"
                "        return sock\n",
                "",
            ),
            (
                "_fetch_messages",
                "            if current_data is not None and len(current_data) >= 0:\n"
                "                _append_message(messages, current_header, current_data)",
                "            if current_data is not None:\n"
                "                _append_message(messages, current_header, current_data)",
            ),
        ),
    ),
    "slack_sdk/proxy_env_variable_loader.py": (
        "bf08e211ae42dff0d784f12e957e1ffd1b00db546c2e938fd7976f0faf48f4d3",
        "457ae15cab87ff86b02e0062e7a5a3d3551330c7c9f095ca60aa5fc53e790fa7",
        (
            (
                "load_http_proxy_from_env",
                '    logger.debug(f"HTTP proxy URL has been loaded from an env variable: {proxy_url}")',
                '    logger.debug("HTTP proxy URL has been loaded from an env variable")',
            ),
        ),
    ),
    "slack_sdk/web/base_client.py": (
        "fd7beafe11ec7a0661005c96617378ad4ff0873b5f095205ac993f1a762b88ae",
        "66bf86b8841a666edff4c0f22dbe74c8e0d76136815e83b082840e4f79fbffcd",
        (
            (
                "BaseClient._perform_urllib_http_request_internal",
                "                resp = urlopen(req, context=self.ssl, timeout=self.timeout)",
                "                opener = urllib.request.build_opener(ProxyHandler({}), "
                "HTTPSHandler(context=self.ssl))\n"
                "                resp = opener.open(req, timeout=self.timeout)",
            ),
        ),
    ),
    "slack_sdk/web/internal_utils.py": (
        "57079c812b5ad1b9a1ec287a05f1c33d4a43977ed06f3ce5c0f213e730f1cfad",
        "401b13f1e3fbddf7a1a397865be5783a68a01828d1b29301c767c8611c1ecd51",
        (("_build_req_args", "    token = token\n", ""),),
    ),
}
MANIFEST = "vendor-manifest.json"
SHA256 = re.compile(r"[0-9a-f]{64}")
MODULE = re.compile(r"[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*")


def digest(data: bytes) -> str:
    """Return the immutable byte identity, independent of wheel RECORD claims."""
    return hashlib.sha256(data).hexdigest()


def required_transform(upstream: dict[str, object], source: str, target: str, owner: str) -> str:
    """Select verifier-owned policy; a manifest cannot supply security patch parameters."""
    # The owning namespace decides whether the repair is mandatory. Untrusted
    # upstream metadata must never turn that requirement off (including name aliases).
    if target != SLACK_SECURITY_OWNER and canonicalize_name(owner) != "heinzel-slack":
        return TRANSFORM_VERSION
    if (
        source,
        target,
        upstream["distribution"],
        upstream["version"],
        upstream["wheel"],
        upstream["sha256"],
    ) != (
        "slack_sdk",
        SLACK_SECURITY_OWNER,
        "slack_sdk",
        "3.46.0",
        SLACK_SECURITY_WHEEL,
        SLACK_SECURITY_WHEEL_SHA256,
    ):
        raise ValueError("The Slack security repair requires its exact approved upstream wheel")
    return SLACK_SECURITY_TRANSFORM


def replace_statement(function: ast.FunctionDef, before: str, after: str) -> None:
    """Construct the expected AST independently of byte replacement, in one fixed function scope."""
    pattern = ast.dump(ast.parse(textwrap.dedent(before)).body[0])
    replacement = ast.parse(textwrap.dedent(after)).body
    matches = 0

    class Expected(ast.NodeTransformer):
        def visit(self, node: ast.AST):
            nonlocal matches
            if isinstance(node, ast.stmt) and ast.dump(node) == pattern:
                matches += 1
                return copy.deepcopy(replacement)
            return super().visit(node)

    Expected().visit(function)
    if matches != 1:
        raise ValueError("Slack security statement identity differs")


def repair_security_member(path: str, original: bytes) -> bytes:
    """Apply only fixed source statements, verified by pre/post hashes and independent scoped AST edits."""
    before_hash, after_hash, changes = SLACK_SECURITY_PATCHES[path]
    if digest(original) != before_hash:
        raise ValueError("Slack security preimage differs from the reviewed member")
    patched = original
    expected = ast.parse(original)
    for function_name, before, after in changes:
        if patched.count(before.encode()) != 1:
            raise ValueError("Slack security statement must occur exactly once")
        patched = patched.replace(before.encode(), after.encode())
        scope = expected.body
        if "." in function_name:
            class_name, function_name = function_name.split(".", 1)
            classes = [node for node in scope if isinstance(node, ast.ClassDef) and node.name == class_name]
            if len(classes) != 1:
                raise ValueError("Slack security class identity differs")
            scope = classes[0].body
        functions = [node for node in scope if isinstance(node, ast.FunctionDef) and node.name == function_name]
        if len(functions) != 1:
            raise ValueError("Slack security function identity differs")
        replace_statement(functions[0], before, after)
    if ast.dump(expected) != ast.dump(ast.parse(patched)) or digest(patched) != after_hash:
        raise ValueError("Slack security semantic delta or postimage differs")
    return patched


def projected_member(original: bytes, path: str, source: str, target: str, transform: str) -> bytes:
    """Apply the selected closed policy before the unchanged namespace-only transform."""
    if transform not in {TRANSFORM_VERSION, SLACK_SECURITY_TRANSFORM}:
        raise ValueError("Unsupported vendor transform")
    if transform == SLACK_SECURITY_TRANSFORM and path in SLACK_SECURITY_PATCHES:
        original = repair_security_member(path, original)
    return relocate(original, source, target) if path.endswith((".py", ".pyi")) else original


def archive_regular(info: zipfile.ZipInfo) -> None:
    """Accept ordinary or unspecified ZIP modes, rejecting special file types."""
    mode = stat.S_IFMT(info.external_attr >> 16)
    allowed = {0, stat.S_IFDIR} if info.is_dir() else {0, stat.S_IFREG}
    if mode not in allowed:
        raise ValueError("Vendor wheel archive contains a nonregular file")


def unique_archive_paths(names: list[str]) -> None:
    """Reject aliases that collide across case-sensitive and canonicalizing filesystems."""
    canonical = [
        unicodedata.normalize("NFC", unicodedata.normalize("NFC", name.rstrip("/")).casefold()) for name in names
    ]
    if len(canonical) != len(set(canonical)):
        raise ValueError("Vendor wheel archive has colliding canonical paths")


def retained_typing(source: str, available: set[str], originals: dict[str, bytes]) -> None:
    """Require companion stubs and every internal module referenced by a selected stub."""
    selected = set(originals)
    for path in selected:
        if path.endswith(".py") and path + "i" in available and path + "i" not in selected:
            raise ValueError("Upstream companion typing stub must be retained")
    for path, data in originals.items():
        if not path.endswith(".pyi"):
            continue
        package = list(PurePosixPath(path).parts[:-1])
        requested: set[str] = set()
        for node in ast.walk(ast.parse(data)):
            if isinstance(node, ast.Import):
                requested.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    if node.level > len(package):
                        raise ValueError("Typing import escapes the upstream namespace")
                    base = package[: len(package) - node.level + 1]
                    module = ".".join([*base, *node.module.split(".")]) if node.module else ".".join(base)
                else:
                    module = node.module or ""
                requested.add(module)
                requested.update(module + "." + alias.name for alias in node.names if alias.name != "*")
        for module in requested:
            if module == source or module.startswith(source + "."):
                parts = module.split(".")
                for length in range(1, len(parts) + 1):
                    prefix = "/".join(parts[:length])
                    candidates = {
                        prefix + suffix for suffix in (".py", ".pyi", "/__init__.py", "/__init__.pyi")
                    } & available
                    if not candidates <= selected:
                        raise ValueError("Upstream typing import requires omitted module files")


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
    license_files: tuple[str, ...] = ()

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
    if manifest["format"] != 1:
        raise ValueError("Unsupported vendor manifest/transform version")
    upstream = mapping(
        manifest["upstream"], {"distribution", "version", "wheel", "sha256", "license_paths", "license_expression"}
    )
    source_package = mapping(manifest["package"], {"source", "target"})
    source, target = string(source_package["source"]), string(source_package["target"])
    metadata = tomllib.loads(regular(root, "pyproject.toml").read_text())
    transform = required_transform(upstream, source, target, string(metadata["project"]["name"]))
    if manifest["transform_version"] != transform:
        raise ValueError("Unsupported vendor transform or missing mandatory security repair")
    if not source.isidentifier() or not MODULE.fullmatch(target) or target.split(".")[1:-1] != ["_vendor"]:
        raise ValueError("Vendor target must be an owning package's _vendor namespace")
    if target.split(".")[-1] != source:
        raise ValueError("Vendor namespace must preserve the upstream package name")
    target_root = "src/" + target.replace(".", "/")
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
    if transform == SLACK_SECURITY_TRANSFORM and not set(SLACK_SECURITY_PATCHES) <= {entry.source for entry in entries}:
        raise ValueError("Slack security repair member is missing from the inventory")
    if len({entry.source for entry in entries}) != len(entries) or len({entry.target for entry in entries}) != len(
        entries
    ):
        raise ValueError("Duplicate vendor inventory entry")
    expected: dict[str, bytes] = {}
    originals: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(wheel)) as archive:
        names = archive.namelist()
        unique_archive_paths(names)
        for info in archive.infolist():
            relative(info.filename.rstrip("/"))
            archive_regular(info)
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
            projected = projected_member(original, entry.source, source, target, transform)
            if not SHA256.fullmatch(entry.projected_sha256) or digest(projected) != entry.projected_sha256:
                raise ValueError("Projected vendor file hash/transform mismatch")
            expected[entry.target] = projected
            originals[entry.source] = original
        retained_typing(source, set(names), originals)
    licenses = tuple(sorted(entry.target for entry in entries if entry.source in license_paths))
    return VerifiedInventory(tuple(sorted(expected)), distribution, version, license_expression, licenses), expected


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
    expected = projection(root)[1] if inventory.files else {}
    packed = {name.removeprefix("src/"): data for name, data in expected.items()}
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        unique_archive_paths(names)
        for info in archive.infolist():
            relative(info.filename.rstrip("/"))
            archive_regular(info)
        if not inventory.files:
            if any("_vendor" in {part.casefold() for part in PurePosixPath(name).parts} for name in names):
                raise ValueError("Built wheel vendor namespace requires a verified manifest")
            return inventory
        prefix = "/".join(next(iter(packed)).split("/")[:3]) + "/"
        actual = {name for name in names if name.startswith(prefix) and not name.endswith("/")}
        if actual != set(packed):
            raise ValueError("Built wheel vendor inventory mismatch")
        license_copies = verified_license_copies(root, archive, inventory, expected)
        parent = prefix.rsplit("/", 2)[0] + "/"
        if any(
            "_vendor" in {part.casefold() for part in PurePosixPath(name).parts}
            and not name.startswith(prefix)
            and name not in {parent, parent + "__init__.py"}
            and name not in license_copies
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


def singleton_header(values: list[str], name: str) -> str:
    """Require one nonempty, unfolded authority header; repeated values are ambiguous."""
    if len(values) != 1 or not values[0].strip() or any(char in values[0] for char in "\r\n"):
        raise ValueError(f"Built wheel requires one unambiguous {name} header")
    return values[0]


def verified_license_copies(
    root: Path, archive: zipfile.ZipFile, inventory: VerifiedInventory, expected: dict[str, bytes]
) -> set[str]:
    """Permit only declared owning metadata copies of exact manifest-approved licenses."""
    project_metadata = tomllib.loads(regular(root, "pyproject.toml").read_text())["project"]
    name, version = str(project_metadata["name"]), str(Version(project_metadata["version"]))
    prefix = f"{canonicalize_name(name).replace('-', '_')}-{version}.dist-info/"
    names = set(archive.namelist())
    metadata_path = prefix + "METADATA"
    wheel_path = prefix + "WHEEL"
    authorities = {
        part for path in names for part in PurePosixPath(path).parts if part.casefold().endswith(".dist-info")
    }
    if authorities != {prefix.rstrip("/")} or not {metadata_path, wheel_path} <= names:
        raise ValueError("Built wheel license copy requires one canonical METADATA/WHEEL authority")
    if any(part.casefold().endswith(".dist-info") for path in names for part in PurePosixPath(path).parts[1:]):
        raise ValueError("Built wheel contains a nested dist-info authority")
    metadata = BytesParser().parsebytes(archive.read(metadata_path))
    metadata_version = singleton_header(metadata.get_all("Metadata-Version", []), "Metadata-Version")
    actual_name = singleton_header(metadata.get_all("Name", []), "Name")
    actual_version = singleton_header(metadata.get_all("Version", []), "Version")
    if (
        not re.fullmatch(r"[12]\.[0-9]+", metadata_version)
        or canonicalize_name(actual_name) != canonicalize_name(name)
        or actual_version != version
    ):
        raise ValueError("Built wheel license metadata identity mismatch")
    wheel_metadata = BytesParser().parsebytes(archive.read(wheel_path))
    wheel_version = singleton_header(wheel_metadata.get_all("Wheel-Version", []), "Wheel-Version")
    singleton_header(wheel_metadata.get_all("Generator", []), "Generator")
    pure = singleton_header(wheel_metadata.get_all("Root-Is-Purelib", []), "Root-Is-Purelib")
    tags = wheel_metadata.get_all("Tag", [])
    tag_pattern = (
        r"[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*-"
        r"[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*-[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*"
    )
    if (
        wheel_version != "1.0"
        or pure not in {"true", "false"}
        or not tags
        or len(tags) != len(set(tags))
        or any(not re.fullmatch(tag_pattern, tag) for tag in tags)
    ):
        raise ValueError("Built wheel has invalid WHEEL authority fields")
    build = wheel_metadata.get_all("Build", [])
    if build and not re.fullmatch(r"[0-9][a-zA-Z0-9_.]*", singleton_header(build, "Build")):
        raise ValueError("Built wheel has an invalid Build header")
    declared = {relative(path) for path in metadata.get_all("License-File", [])}
    verified = set()
    for path in inventory.license_files:
        copy = prefix + "licenses/" + path
        if copy not in names and path not in declared:
            continue
        if copy not in names or path not in declared or archive.read(copy) != expected[path]:
            raise ValueError("Built wheel license copy declaration/bytes mismatch")
        verified.add(copy)
    return verified


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
    upstream: dict[str, object] = {
        "distribution": distribution,
        "version": version,
        "wheel": wheel.name,
        "sha256": sha256,
        "license_paths": license_paths,
        "license_expression": license_expression,
    }
    metadata = tomllib.loads(regular(root, "pyproject.toml").read_text())
    transform = required_transform(upstream, source, target, string(metadata["project"]["name"]))
    if transform == SLACK_SECURITY_TRANSFORM and not set(SLACK_SECURITY_PATCHES) <= set(paths):
        raise ValueError("Slack security repair member is missing from the inventory")
    entries = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for path in sorted(paths + license_paths):
            relative(path)
            original = archive.read(path)
            projected = projected_member(original, path, source, target, transform)
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
        "transform_version": transform,
        "upstream": upstream,
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
