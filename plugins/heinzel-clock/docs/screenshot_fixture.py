"""Align fictional team time zones and their source clock for documentation captures."""

import os
import runpy
import sys
from datetime import UTC, datetime

import heinzel_clock

MOMENT = datetime(2026, 10, 26, 15, 30, tzinfo=UTC)


class DemoTime(datetime):
    """Use one explicit demonstration moment without changing the installed runtime."""

    @classmethod
    def now(cls, tz=None):
        """Read the fixed demonstration moment in the requested time zone."""
        return MOMENT.astimezone(tz) if tz is not None else MOMENT.replace(tzinfo=None)


heinzel_clock.datetime = DemoTime
os.environ["HZ_CLOCK__ZONES"] = (
    '[{"name":"Europe/Berlin","hours":[9,18]},{"name":"America/New_York","hours":[9,18]},{"name":"America/Los_Angeles","hours":[9,18]}]'
)
os.environ["HZ_SYSTEM_UI__CONTRIBUTIONS"] = (
    '{"clock:zones-ticker":{"sidebar":true},"clock:primary-zone":{"footer":true}}'
)
sys.argv = ["hz", *sys.argv[1:]]
runpy.run_module("heinzel", run_name="__main__")
