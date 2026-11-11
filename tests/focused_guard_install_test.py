"""The companion installer never replaces a stock or unrelated legacy hook."""

import hashlib
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "focused_guard_install", Path(__file__).parents[1] / "scripts/focused_guard_install.py"
)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_install_requires_exact_review_pins_and_preserves_legacy(tmp_path):
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    shim = hooks / "pre-push"
    shim.write_bytes(b"stock")
    shim.chmod(0o700)
    source = tmp_path / "guard"
    source.write_bytes(b"reviewed")
    with pytest.raises(ValueError):
        installer.install(source, hooks, "0" * 64, sha(shim))
    assert not (hooks / "pre-push.legacy").exists()
    installer.install(source, hooks, sha(source), sha(shim))
    assert (hooks / "pre-push.legacy").read_bytes() == b"reviewed"
    assert shim.read_bytes() == b"stock"
    with pytest.raises(FileExistsError):
        installer.install(source, hooks, sha(source), sha(shim))
    assert (hooks / "pre-push.legacy").read_bytes() == b"reviewed"


def test_refuse_symlink_or_wrong_stock_shim(tmp_path):
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    source = tmp_path / "guard"
    source.write_bytes(b"guard")
    (hooks / "pre-push").symlink_to(source)
    with pytest.raises(ValueError):
        installer.install(source, hooks, sha(source), sha(source))
    assert not (hooks / "pre-push.legacy").exists()


def test_confined_refuses_traversal_and_symlink_escape(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    inside = root / "guard"
    inside.write_bytes(b"x")
    outside = tmp_path / "other"
    outside.write_bytes(b"x")
    (root / "link").symlink_to(outside)
    assert installer.confined(inside, root) == inside.resolve()
    for bad in (outside, root / ".." / "other", root / "link"):
        with pytest.raises(ValueError):
            installer.confined(bad, root)
