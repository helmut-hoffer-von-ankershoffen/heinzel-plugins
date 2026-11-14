"""The scheduled tick waits out the last seconds of a five-minute slot."""

import pytest

from tests.support.connected_schedule_support import _wait_for_slot_margin

pytestmark = pytest.mark.unit


def test_slot_margin_waits_across_a_boundary():
    clock = iter([299.0, 299.4, 300.0, 330.0])
    waits = []

    class Waiter:
        def wait(self, seconds):
            waits.append(seconds)

    _wait_for_slot_margin(Waiter(), lambda: next(clock))
    assert waits == [0.5, 0.5]
