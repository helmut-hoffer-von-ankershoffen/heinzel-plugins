"""Seed only the example's own notice in an isolated, in-app-only demonstration profile."""

import os
import sys

from heinzel import Config, Kernel, Notifications, Settings
from heinzel.heads.cli import build
from heinzel.kernel import discover
from heinzel_example import notify

os.environ.update(
    HZ_SYSTEM_NOTIFY__NATIVE="false",
    HZ_SYSTEM_NOTIFY__DOCTOR="false",
    HZ_SYSTEM_NOTIFY__RELEASE="false",
    HZ_SYSTEM_NOTIFY__QUIET="true",
    HZ_SYSTEM_NOTIFY__WORKING_HOURS="false",
)
config = Config.load()
records, errors = discover()
kernel = Kernel(config.settings(Settings, "hz"), records, errors, config)
notify(kernel.resolve(Notifications))
sys.argv = ["hz", *sys.argv[1:]]
build(kernel)()
