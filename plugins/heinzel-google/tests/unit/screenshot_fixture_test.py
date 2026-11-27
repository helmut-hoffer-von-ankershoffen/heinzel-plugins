"""The gallery uses the public adapter clock seam with fixed fictional vendor metadata."""

import json
import runpy
from datetime import UTC, datetime
from pathlib import Path

import pytest

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
