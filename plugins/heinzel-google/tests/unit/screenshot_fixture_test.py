"""The gallery uses the public adapter clock seam with fixed fictional vendor metadata."""

import json
import os
import runpy
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from heinzel.modules import org

pytestmark = pytest.mark.unit


def test_gallery_clock_is_explicit_and_vendor_metadata_stays_inside_the_requested_window():
    fixture = runpy.run_path(str(Path(__file__).parents[2] / "docs/screenshot_fixture.py"))
    response = fixture["DemoGws"]().run("gws", ["drive", "files", "list", "--params", "{}"], 10)
    items = json.loads(response.stdout)["files"]
    expected = datetime(2026, 10, 25, 12, tzinfo=UTC)
    assert {item["modifiedTime"] for item in items} == {"2026-10-25T12:00:00Z"}
    queries = []

    class Session:
        def pages(self, label, command, params, context, key):
            queries.append(params["q"])
            yield items, None

    drive = fixture["DemoDrive"](Session())
    for days, date in [(3, "2026-10-23"), (7, "2026-10-19")]:
        files = drive.recent(days, "Launch")
        assert len(files) == 3
        assert all(item.modified_at == expected for item in files)
        assert datetime.fromisoformat(date).replace(tzinfo=UTC) < expected < fixture["DEMO_NOW"]
        assert f"modifiedTime > '{date}T00:00:00Z'" in queries[-1]
        assert "name contains 'Launch'" in queries[-1]
    drive.recent(3, now=datetime(2026, 10, 30, tzinfo=UTC))
    assert "modifiedTime > '2026-10-27T00:00:00Z'" in queries[-1]


@pytest.mark.parametrize(
    ("wall_time", "zone", "excluded"),
    [
        ("2027-03-28T23:59:59", "Europe/Berlin", []),
        ("2027-11-07T23:59:59", "America/Los_Angeles", ["family@example.com"]),
        ("2027-03-29T00:01:00", "Pacific/Kiritimati", []),
    ],
)
def test_calendar_picker_uses_one_fixed_week_across_host_week_boundaries(
    wall_time, zone, excluded, monkeypatch, capsys
):
    docs = Path(__file__).parents[2] / "docs"
    fixture = runpy.run_path(str(docs / "screenshot_fixture.py"))
    browser_time = datetime.fromisoformat(json.loads((docs / "screenshot-definition.json").read_text())["browser_time"])
    assert browser_time == fixture["CALENDAR_NOW"]
    host_now = datetime.fromisoformat(wall_time).replace(tzinfo=ZoneInfo(zone))
    monkeypatch.setattr(org, "local_now", lambda _timezone: host_now)
    selection = json.dumps({"adapter": "google", "excluded": excluded})
    monkeypatch.setattr(sys, "argv", ["fixture", "org", "calendar", "--selection", selection, "--json"])

    with patch.dict(os.environ), pytest.raises(SystemExit) as result:
        fixture["main"]()

    assert result.value.code == 0
    assert org.local_now(None) == host_now
    week = json.loads(capsys.readouterr().out)
    assert week["timezone"] == "Europe/Berlin"
    assert datetime.fromisoformat(week["since"]).isoformat() == "2026-10-19T00:00:00+02:00"
    assert datetime.fromisoformat(week["until"]).isoformat() == "2026-10-26T00:00:00+01:00"
    assert [source["title"] for source in week["calendars"]] == ["Work", "Family"]
    titles = [event["title"] for event in week["events"]]
    expected = ["Launch readiness review", "Mira Example / Priya Example — one-on-one", "Rollout checkpoint"]
    if not excluded:
        expected.append("Family dinner")
    assert titles == expected
