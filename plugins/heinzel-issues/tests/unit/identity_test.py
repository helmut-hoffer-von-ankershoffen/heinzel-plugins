"""Issue ownership comes from one authenticated host call, never client text."""

from datetime import UTC, datetime

import pytest
from heinzel import CallIdentity, CurrentUser, HeinzelError, Principal

from heinzel_issues._beads import BeadsSettings, BeadsTracker, _Row, reporter
from heinzel_issues._contract import TrackerError
from heinzel_issues._identity import access, authenticated

pytestmark = pytest.mark.unit


def row(creator, labels=None):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return _Row(
        id="demo-1",
        title="Example",
        status="open",
        created_at=now,
        updated_at=now,
        created_by=creator,
        labels=labels or ["heinzel-issues"],
    )


def identity(principal):
    return CallIdentity(principal, "web-session", "fixture", "hz-web", frozenset({"private:read", "private:write"}))


def test_caller_is_required_and_scoped(tmp_path):
    current = CurrentUser(tmp_path / "identity")
    tracker = BeadsTracker(BeadsSettings())
    with pytest.raises(TrackerError, match="authenticated caller"):
        tracker.mine(row("unknown"))
    with pytest.raises(HeinzelError):
        with authenticated(current):
            pass
    with current.local("cli"), authenticated(current):
        outer = access().actor
        with current.using(identity(Principal("u-" + "a" * 32))), authenticated(current):
            assert access().actor != outer
        assert access().actor == outer
    with pytest.raises(TrackerError):
        access()


def test_principal_separation_and_owner_only_legacy_history(tmp_path):
    current = CurrentUser(tmp_path / "identity")
    tracker = BeadsTracker(BeadsSettings())
    owner = current.owner()
    other = Principal("u-" + "a" * 32)
    with current.using(identity(owner)), authenticated(current):
        assert tracker.mine(row(owner.id))
        assert tracker.mine(row(reporter()))
        assert not tracker.mine(row(other.id))
        assert not tracker.mine(row(owner.id, ["other"]))
    with current.using(identity(other)), authenticated(current):
        assert tracker.mine(row(other.id))
        assert not tracker.mine(row(owner.id))
        assert not tracker.mine(row(reporter()))
