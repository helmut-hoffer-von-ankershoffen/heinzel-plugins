"""The worked example exercises public contributions without core test sources or sibling plugins."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from heinzel import NoticeKind, Notifications, ViewLet

from heinzel_example import module, notify, sample, status, today

pytestmark = pytest.mark.unit


def test_example_value_owns_its_status_and_today_widget():
    assert sample() == 42
    assert status(sample()).effect.path == "/?panel=example:inspector"
    assert today(sample()).value == "42"
    [view] = [let for let in module.lets if isinstance(let, ViewLet)]
    assert view.files
    assert view.source == "sample"


@pytest.mark.parametrize("enabled", [True, False])
def test_plugin_notice_uses_the_shared_notification_policy(enabled):
    notifications = Mock(spec=Notifications)
    notifications.emit.return_value = SimpleNamespace(title="Example is ready") if enabled else None
    assert notify(notifications) == ("Example is ready" if enabled else "Notifications are disabled")
    assert notifications.emit.call_args.args[0] is NoticeKind.PLUGIN
