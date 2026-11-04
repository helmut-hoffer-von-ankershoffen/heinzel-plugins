"""What a Jira helper hands a host for notices and approvals fits the core's channel ports; no ticket text."""

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest

from heinzel_atlassian import AtlassianSettings
from heinzel_atlassian._drafts import JiraDrafts, sha256_of
from heinzel_atlassian._work import attention, ticket_from
from tests.conftest import live
from tests.unit.untrusted_test import INJECTION, hostile_view

pytestmark = pytest.mark.unit

SITE = "https://acme.atlassian.net"
NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)


def overdue(view: dict):
    found = attention(ticket_from(SITE, view), NOW, NOW, "acct-wren", None)
    assert found
    return found


def test_a_notice_is_stable_short_and_made_of_structured_fields_only():
    view = hostile_view()
    view["fields"]["duedate"] = "2026-11-01"
    found = overdue(view)
    assert found.title == "KAN-8: overdue"
    assert found.notice_key == overdue(view).notice_key  # the same news is the same notice
    assert INJECTION not in found.title + found.body + found.notice_key
    assert "Due 2026-11-01" in found.body


def test_a_new_update_or_new_reason_is_new_news():
    view = live("view_task.json")
    view["fields"]["duedate"] = "2026-11-01"
    first = overdue(view).notice_key
    view["fields"]["updated"] = "2026-11-04T09:00:00.000+0100"
    assert overdue(view).notice_key != first


def test_a_draft_carries_what_an_approval_request_needs(fake_acli):
    fake_acli.handler = lambda args: (0, json.dumps(live("view_task.json")), "")
    draft = JiraDrafts(AtlassianSettings(site_url=SITE), fake_acli).draft_comment("KAN-8", "Dunmore is fixed.")
    assert draft.arguments_sha256 == sha256_of(draft.action, draft.arguments)
    assert (
        draft.arguments_sha256
        == hashlib.sha256(
            json.dumps([draft.action, draft.arguments], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    assert draft.digest == draft.arguments_sha256[:12]
    assert draft.link == f"{SITE}/browse/KAN-8"
    assert "Dunmore is fixed." in draft.approval_text
    assert len(draft.approval_text) <= 4000


def test_a_long_draft_is_cut_for_the_approval_text(fake_acli):
    fake_acli.handler = lambda args: (0, json.dumps(live("view_task.json")), "")
    draft = JiraDrafts(AtlassianSettings(site_url=SITE), fake_acli).draft_comment("KAN-8", "x" * 40_000)
    assert not draft.ready  # Jira's own bound refuses it
    assert len(draft.approval_text) <= 4000


def test_these_fields_fit_the_core_channel_messages_when_the_core_has_them(fake_acli):
    kernel = pytest.importorskip("heinzel.kernel")
    if not hasattr(kernel, "ChannelNotice"):
        pytest.skip("this core has no channel ports yet")
    view = live("view_task.json")
    view["fields"]["duedate"] = "2026-11-01"
    found = overdue(view)
    kernel.ChannelNotice(
        key=found.notice_key, helper="Mira", title=found.title, body=found.body, route="/heinzel?chat=hz-1"
    )
    fake_acli.handler = lambda args: (0, json.dumps(view), "")
    draft = JiraDrafts(AtlassianSettings(site_url=SITE), fake_acli).draft_comment("KAN-8", "Done.")
    kernel.ChannelApprovalRequest(
        request_id="r1",
        helper="Mira",
        action="Comment on KAN-8",
        preview=draft.approval_text,
        link=draft.link,
        arguments_sha256=draft.arguments_sha256,
        expires_at=NOW + timedelta(hours=1),
    )
