"""Approval storage refuses unsafe paths before SQLite or permission changes can touch them."""

import os
import shutil
import stat
from datetime import UTC, datetime

import pytest
from heinzel import HeinzelError

from heinzel_slack._store import Store

pytestmark = pytest.mark.integration


def test_storage_is_private_on_creation_and_reopens(tmp_path):
    folder = tmp_path / "state" / "slack"
    store = Store(folder)
    assert stat.S_IMODE(folder.stat().st_mode) == 0o700
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600
    assert Store(folder).pending() == []


@pytest.mark.parametrize("where", ["leaf", "ancestor"])
def test_directory_symlinks_are_rejected_without_changing_the_target(tmp_path, where):
    target = tmp_path / "foreign"
    target.mkdir(mode=0o755)
    linked = tmp_path / "link"
    linked.symlink_to(target, target_is_directory=True)
    folder = linked if where == "leaf" else linked / "slack"
    before = target.stat()
    with pytest.raises(HeinzelError, match="physical private"):
        Store(folder)
    assert target.stat().st_mode == before.st_mode
    assert list(target.iterdir()) == []


@pytest.mark.parametrize("mode", [0o755, 0o770])
def test_existing_nonprivate_directory_is_never_chmodded(tmp_path, mode):
    folder = tmp_path / "slack"
    folder.mkdir(mode=mode)
    folder.chmod(mode)
    with pytest.raises(HeinzelError, match="physical private"):
        Store(folder)
    assert stat.S_IMODE(folder.stat().st_mode) == mode
    assert list(folder.iterdir()) == []


def test_a_writable_ancestor_is_rejected_without_creating_children(tmp_path):
    ancestor = tmp_path / "shared"
    ancestor.mkdir(mode=0o700)
    ancestor.chmod(0o777)
    with pytest.raises(HeinzelError, match="physical private"):
        Store(ancestor / "slack")
    assert list(ancestor.iterdir()) == []


@pytest.mark.parametrize("suffix", ["", "-wal", "-shm", "-journal"])
def test_file_ownership_is_validated_before_sqlite_opens(tmp_path, monkeypatch, suffix):
    folder = tmp_path / "slack"
    folder.mkdir(mode=0o700)
    path = folder / ("approvals.sqlite3" + suffix)
    path.write_bytes(b"FOREIGN OWNER SENTINEL")
    path.chmod(0o600)
    original_stat = os.stat

    def foreign_stat(name, *args, **kwargs):
        found = original_stat(name, *args, **kwargs)
        if name == path.name and kwargs.get("dir_fd") is not None:
            fields = list(found)
            fields[4] = os.getuid() + 1
            return os.stat_result(fields)
        return found

    monkeypatch.setattr(os, "stat", foreign_stat)
    with pytest.raises(HeinzelError, match="single-link regular"):
        Store(folder)
    assert path.read_bytes() == b"FOREIGN OWNER SENTINEL"


@pytest.mark.parametrize("suffix", ["", "-wal", "-shm", "-journal"])
@pytest.mark.parametrize("kind", ["symlink", "hardlink", "fifo", "public", "directory"])
def test_unsafe_database_and_sidecars_are_refused_before_mutation(tmp_path, suffix, kind):
    folder = tmp_path / "slack"
    folder.mkdir(mode=0o700)
    target = tmp_path / "foreign"
    target.write_bytes(b"PRIVATE SENTINEL")
    target.chmod(0o600)
    path = folder / ("approvals.sqlite3" + suffix)
    if kind == "symlink":
        path.symlink_to(target)
    elif kind == "hardlink":
        os.link(target, path)
    elif kind == "fifo":
        os.mkfifo(path, mode=0o600)
    elif kind == "directory":
        path.mkdir(mode=0o700)
    else:
        path.write_bytes(b"PUBLIC SENTINEL")
        path.chmod(0o644)
    before = target.stat()
    path_before = path.lstat()
    with pytest.raises(HeinzelError, match="single-link regular"):
        Store(folder)
    assert target.read_bytes() == b"PRIVATE SENTINEL"
    assert target.stat().st_mode == before.st_mode
    assert path.lstat().st_mode == path_before.st_mode
    if suffix:
        assert not (folder / "approvals.sqlite3").exists()


@pytest.mark.parametrize("replacement", ["symlink", "copy", "directory"])
def test_reopen_detects_replaced_database_or_directory(tmp_path, replacement):
    folder = tmp_path / "slack"
    store = Store(folder)
    foreign = tmp_path / "foreign.sqlite3"
    shutil.copyfile(store.path, foreign)
    foreign.chmod(0o600)
    before = foreign.read_bytes()
    if replacement == "directory":
        folder.rename(tmp_path / "original")
        folder.mkdir(mode=0o700)
        shutil.copyfile(foreign, store.path)
        store.path.chmod(0o600)
    else:
        store.path.rename(folder / "original.sqlite3")
        if replacement == "symlink":
            store.path.symlink_to(foreign)
        else:
            shutil.copyfile(foreign, store.path)
            store.path.chmod(0o600)
    with pytest.raises(HeinzelError):
        store.pending()
    assert foreign.read_bytes() == before


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_reopen_validates_new_sidecars_before_sqlite_can_touch_them(tmp_path, suffix):
    store = Store(tmp_path / "slack")
    foreign = tmp_path / "foreign"
    foreign.write_bytes(b"PRIVATE SENTINEL")
    foreign.chmod(0o600)
    path = store.path.with_name(store.path.name + suffix)
    path.symlink_to(foreign)
    with pytest.raises(HeinzelError, match="single-link regular"):
        store.begin_delivery("new", datetime.now(UTC))
    assert foreign.read_bytes() == b"PRIVATE SENTINEL"


@pytest.mark.parametrize("suffix", ["", "-wal", "-shm", "-journal"])
def test_reopen_rejects_files_that_became_public_without_chmodding_them(tmp_path, suffix):
    store = Store(tmp_path / "slack")
    path = store.path.with_name(store.path.name + suffix)
    if suffix:
        path.write_bytes(b"PUBLIC SIDECAR")
    path.chmod(0o644)
    before = path.read_bytes()
    with pytest.raises(HeinzelError, match="single-link regular"):
        store.pending()
    assert stat.S_IMODE(path.stat().st_mode) == 0o644
    assert path.read_bytes() == before
