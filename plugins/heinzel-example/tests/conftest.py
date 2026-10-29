"""Shared fixtures.

heinzel.testing (a pytest plugin, loaded automatically) brings the rest: every test is exactly one of unit,
integration or e2e and gets its level's timeout (docs/CODING_STANDARDS.md#tests), and every test has its own
HZ_CONFIG_HOME, HZ_DATA_DIR and HZ_CACHE_DIR, without the developer's HZ_* variables.
"""

from collections.abc import Callable

import pytest
from heinzel import Config, Kernel, ModuleRecord, Settings
from heinzel.kernel import Origin, discover


@pytest.fixture
def boot() -> Callable[..., Kernel]:
    """Boot a kernel the way the `hz` command does: Heinzelmännchen's built-in modules plus every installed plugin."""

    def make(**settings: object) -> Kernel:
        records, errors = discover()
        return Kernel(Settings(**settings), records, errors)

    return make


@pytest.fixture
def make_kernel():
    def make(*, builtins=False, settings_=None, config=None, **modules):
        config = config or Config.empty()
        records = discover(plugins=False)[0] if builtins else []
        records += [
            ModuleRecord(
                qualname=name.replace("__", "."),
                module=module,
                origin=Origin("heinzel-contract-fixture", "1.0.0", builtin=False),
            )
            for name, module in modules.items()
        ]
        return Kernel(settings_ or config.settings(Settings, "hz"), records, config=config)

    return make
