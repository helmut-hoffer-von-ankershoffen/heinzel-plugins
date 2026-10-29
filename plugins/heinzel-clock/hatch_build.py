"""Build this plugin's own frontend before producing its wheel or sdist."""

import subprocess
import sys
from pathlib import Path
from typing import cast

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class ViewBuildHook(BuildHookInterface):
    """Package only this plugin's freshly built view assets."""

    def initialize(self, version: str, build_data: dict[str, object]) -> None:
        """Build in this project's PEP 517 environment; editable Python installs stay fast."""
        if version == "editable":
            return
        subprocess.run([sys.executable, str(Path(self.root) / "web/build.py"), "run", "build"], check=True, timeout=600)  # noqa: S603 - own build hook, no shell
        assets = Path(self.root) / "src/heinzel_clock/views"
        included = cast("dict[str, str]", build_data.setdefault("force_include", {}))
        included[str(assets)] = "heinzel_clock/views"
