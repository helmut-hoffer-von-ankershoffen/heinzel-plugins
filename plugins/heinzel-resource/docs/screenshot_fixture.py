"""Deterministic fictional machine data for documentation capture only."""

import runpy
import sys
from datetime import UTC, datetime

from heinzel_resource import ResourceService, Resources


def sample(self):
    return Resources(
        hostname="demo-workstation",
        sampled_at=datetime(2026, 10, 31, 10, tzinfo=UTC),
        cpu_percent=36,
        memory_percent=62,
        load_1m=0.65,
        logical_cores=8,
        problems=[],
    )


ResourceService.sample = sample
sys.argv = ["hz", *sys.argv[1:]]
runpy.run_module("heinzel", run_name="__main__")
