"""Only authenticated public bootstrap bytes cross into the disposable renderer."""

import hashlib
import io
import urllib.error
from pathlib import Path

import pytest

from heinzel_plugin_tools import capture_linux, privacy

pytestmark = pytest.mark.unit
PUBLIC = b"fictional public wheel"


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(capture_linux, "BOOTSTRAP_SHA256", hashlib.sha256(PUBLIC).hexdigest())
    return tmp_path / ".cache/heinzel-plugin-tools/bootstrap" / capture_linux.BOOTSTRAP_WHEEL


def response(monkeypatch, data=PUBLIC):
    def read(url, *, timeout):
        assert url == capture_linux.BOOTSTRAP_URL
        assert timeout == 60
        return io.BytesIO(data)

    monkeypatch.setattr(capture_linux.urllib.request, "urlopen", read)


def test_cache_downloads_exact_public_bytes_and_verifies_each_reuse(cache, monkeypatch):
    response(monkeypatch)
    assert capture_linux.bootstrap_wheel() == PUBLIC
    assert cache.read_bytes() == PUBLIC
    monkeypatch.setattr(capture_linux.urllib.request, "urlopen", lambda *_a, **_k: pytest.fail("cache hit fetched"))
    assert capture_linux.bootstrap_wheel() == PUBLIC
    cache.write_bytes(b"changed")
    with pytest.raises(privacy.CaptureError, match="hash differs"):
        capture_linux.bootstrap_wheel()


@pytest.mark.parametrize("data", [b"wrong", b"x" * (20 * 1024 * 1024 + 1)])
def test_bad_download_never_enters_cache(cache, monkeypatch, data):
    response(monkeypatch, data)
    with pytest.raises(privacy.CaptureError, match="hash differs"):
        capture_linux.bootstrap_wheel()
    assert not cache.exists()


def test_cache_symlink_is_not_followed(cache, monkeypatch, tmp_path):
    response(monkeypatch)
    cache.parent.mkdir(parents=True)
    target = tmp_path / "outside"
    target.write_bytes(PUBLIC)
    cache.symlink_to(target)
    with pytest.raises(privacy.CaptureError):
        capture_linux.bootstrap_wheel()
    assert target.read_bytes() == PUBLIC


def test_failed_transport_leaves_no_cache(cache, monkeypatch):
    def fail(*_args, **_kwargs):
        raise urllib.error.URLError("fictional outage")

    monkeypatch.setattr(capture_linux.urllib.request, "urlopen", fail)
    with pytest.raises(privacy.CaptureError, match="transport recovers"):
        capture_linux.bootstrap_wheel()
    assert not cache.exists()
