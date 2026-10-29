import pytest
from heinzel import Config, Kernel, ModuleRecord, Settings
from heinzel.kernel import Origin, discover


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
