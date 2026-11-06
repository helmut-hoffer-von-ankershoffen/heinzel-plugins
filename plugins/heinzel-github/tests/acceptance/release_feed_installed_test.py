"""The installed wheel must supply Core's source-bound release-feed service without opening a provider lease."""

import json
import os
import subprocess
import sys
from importlib.metadata import distribution
from pathlib import Path
from zipfile import ZipFile

import pytest

pytestmark = pytest.mark.e2e


def _refuse_external_effects(event, _args):
    if event.startswith(
        ("socket.connect", "socket.gethost", "socket.getaddr", "socket.sendto", "socket.sendmsg")
    ) or event in {
        "os.exec",
        "os.fork",
        "os.posix_spawn",
        "os.system",
        "subprocess.Popen",
    }:
        msg = "An installed source-binding check must not contact or start a provider"
        raise PermissionError(msg)


def _probe(wheel: Path, *, preload: bool) -> None:
    from heinzel import CurrentUser, HeinzelError
    from heinzel.kernel import ReleaseFeedService, boot
    from heinzel.modules.heinzel._draft_workflow_binding import DraftWorkflowBinding

    sys.addaudithook(_refuse_external_effects)
    installed = distribution("heinzel-github")
    direct = json.loads(installed.read_text("direct_url.json"))
    assert direct["url"] == wheel.as_uri()
    assert not direct.get("dir_info", {}).get("editable", False)
    assert "heinzel_github/_release_feed.py" in {str(path) for path in installed.files or ()}
    assert "heinzel_github" not in sys.modules

    if preload:
        import heinzel_github

        assert not hasattr(heinzel_github, "GithubReleaseFeeds")

    kernel = boot(cwd=Path.home())
    assert not kernel.errors, kernel.errors
    current = kernel.resolve(CurrentUser)
    with current.local("cli"):
        if preload:
            with pytest.raises(HeinzelError, match="The selected provider has no reviewed source capture"):
                DraftWorkflowBinding(kernel, "code-host", ReleaseFeedService, "release-feed")
            return

        binding = DraftWorkflowBinding(kernel, "code-host", ReleaseFeedService, "release-feed")
        service = binding.current()
        assert type(service).__name__ == "GithubReleaseFeeds"
        assert binding.record is kernel.module("github")
        capture = kernel.source_discovery.binding(kernel, "code-host", ReleaseFeedService).capture
        assert type(capture.finder).__name__ == "SourceOnlyFinder"
        assert sys.modules[type(service).__module__].__spec__.loader is capture.finder
        assert any(name == "_release_feed.py" for name, _ in capture.finder.snapshot.files)
        with ZipFile(wheel) as exact_wheel:
            for name, data in capture.finder.snapshot.files:
                assert exact_wheel.read(f"heinzel_github/{name}") == data


@pytest.mark.parametrize("mode", ["capture", "preload"])
def test_installed_release_feed_requires_exact_source_capture(tmp_path, mode):
    # The normal suite imports the editable adapter through conftest. Test installed boot in a fresh interpreter.
    wheel = Path(os.environ["PLUGIN_TEST_WHEEL"]).resolve(strict=True)
    home = tmp_path / "profile"
    home.mkdir(mode=0o700)
    environment = {
        "HOME": str(home),
        "PATH": "/usr/bin:/bin",
        "GH_CONFIG_DIR": str(home / "gh"),
        "HZ_CONFIG_HOME": str(home / "config"),
        "HZ_DATA_DIR": str(home / "data"),
        "HZ_CACHE_DIR": str(home / "cache"),
        "HZ_STATE_DIR": str(home / "state"),
        "HZ_LOG_DIR": str(home / "logs"),
        "HZ_PLUGINS_ENABLED": "true",
        "HZ_CAPABILITIES__CODE_HOST": "github",
        "HZ_GITHUB__GH": str(home / "no-provider-executable"),
        "HZ_SYSTEM_CREDENTIAL__BACKEND": "environment",
        "HZ_UPDATE_CHECK": "false",
    }
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(Path(__file__).resolve()), str(wheel), mode],
        cwd=home,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr


if __name__ == "__main__":
    _probe(Path(sys.argv[1]), preload=sys.argv[2] == "preload")
