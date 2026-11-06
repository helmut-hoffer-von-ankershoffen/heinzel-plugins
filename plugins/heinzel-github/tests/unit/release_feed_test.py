"""The supplied CHANGELOG and real release notes are one exact source-bound bounded feed."""

import base64
import json
from types import SimpleNamespace

import pytest
from heinzel import HeinzelError
from heinzel.kernel import ReleaseFeedIdentity

from heinzel_github import _release_feed as feeds

pytestmark = pytest.mark.unit
REFERENCE = "https://github.com/acme/widgets/blob/main/CHANGELOG.md"


def release(number, version, published):
    return {
        "id": number,
        "tag_name": version,
        "body": f"Real notes for {version}.",
        "published_at": published,
        "draft": False,
        "updated_at": published,
    }


@pytest.fixture
def rig():
    value = object.__new__(feeds._FeedLease)
    value.repository, value.ref, value.file, value.reference = "acme/widgets", "main", "CHANGELOG.md", REFERENCE
    value.service = SimpleNamespace(settings=SimpleNamespace(host="github.com"))
    value.identity = ReleaseFeedIdentity(
        account="github.com:lotte",
        source="source-digest",
        reference=REFERENCE,
        read_scope="repo:acme/widgets:releases+contents",
    )
    value._check = lambda: None
    page = [release(1, "v1.0.0", "2026-11-01T10:00:00Z")]
    value._releases = lambda: page
    markdown = "# CHANGELOG\n\n## 1.1.0\nLiteral new notes.\n\n## 1.0.0\nOlder notes.\n"
    content = {
        "path": "CHANGELOG.md",
        "encoding": "base64",
        "sha": "c" * 40,
        "content": base64.b64encode(markdown.encode()).decode(),
    }
    calls = []
    value.client = SimpleNamespace(get=lambda path: calls.append(path) or content)
    return value, page, content, calls


def test_baseline_is_no_historical_catchup_then_new_releases_have_literal_notes_and_changelog(rig):
    value, page, _content, calls = rig
    baseline = value.baseline()
    assert value.poll(baseline.cursor).releases == ()
    page.insert(0, release(2, "v1.1.0", "2026-11-02T10:00:00Z"))
    observed = value.poll(baseline.cursor)
    assert len(observed.releases) == 1
    assert observed.identity.reference == REFERENCE
    record = observed.releases[0]
    assert record.identity == "acme/widgets:release:2"
    assert json.loads(record.text.get_secret_value()) == {
        "tag": "v1.1.0",
        "release_notes": "Real notes for v1.1.0.",
        "changelog_markdown": "## 1.1.0\nLiteral new notes.\n\n",
    }
    assert calls == ["repos/acme/widgets/contents/CHANGELOG.md?ref=main"]
    assert value.poll(observed.cursor).releases == ()


def test_cursor_cannot_be_moved_to_another_account_or_source(rig):
    value, _page, _, _ = rig
    cursor = value.baseline().cursor
    value.identity = value.identity.model_copy(update={"account": "github.com:someone-else"})
    with pytest.raises(HeinzelError, match="exact captured source"):
        value.poll(cursor)


@pytest.mark.parametrize(("field", "value"), [("path", "OTHER.md"), ("encoding", "utf8")])
def test_exact_changelog_target_and_real_release_body_are_required(rig, field, value):
    lease, page, content, _ = rig
    baseline = lease.baseline()
    page.insert(0, release(2, "v1.1.0", "2026-11-02T10:00:00Z"))
    content[field] = value
    with pytest.raises(HeinzelError, match="exact supplied CHANGELOG"):
        lease.poll(baseline.cursor)


def test_missing_corresponding_version_refuses_instead_of_generating_from_unrelated_text(rig):
    lease, page, _, _ = rig
    baseline = lease.baseline()
    page.insert(0, release(2, "v9.0.0", "2026-11-02T10:00:00Z"))
    with pytest.raises(HeinzelError, match="section"):
        lease.poll(baseline.cursor)


@pytest.mark.parametrize(
    "reference",
    [
        "acme/widgets",
        REFERENCE.replace("github.com", "evil.invalid"),
        REFERENCE.replace("https:", "http:"),
        REFERENCE + "?ref=other",
    ],
)
def test_supplied_url_cannot_redirect_account_host_or_reference(reference):
    with pytest.raises(HeinzelError, match="exact HTTPS"):
        feeds._reference(reference, "github.com")


def test_lost_frontier_refuses_instead_of_silently_skipping_more_than_one_page(rig):
    lease, page, _, _ = rig
    baseline = lease.baseline()
    page[:] = [release(number, "v1.1.0", "2026-11-02T10:00:00Z") for number in range(2, 102)]
    with pytest.raises(HeinzelError, match="skip history"):
        lease.poll(baseline.cursor)


def test_duplicate_version_sections_are_ambiguous():
    with pytest.raises(HeinzelError, match="unambiguous"):
        feeds._section("## 1.1.0\nFirst.\n## 1.1.0\nSecond.\n", "v1.1.0")


def test_native_gh_and_credentials_are_privately_pinned_and_selection_drift_refuses(tmp_path, monkeypatch):
    import shutil

    from heinzel_github._gh import Gh, GhResult
    from heinzel_github._models import GithubSettings

    selected = tmp_path / "selected-gh"
    shutil.copyfile(shutil.which("true"), selected)
    selected.chmod(0o700)
    hosts = tmp_path / "hosts.yml"
    hosts.write_text("github.com:\n    user: lotte\n")
    environment = {"HOME": str(tmp_path), "PATH": "/usr/bin:/bin", "GH_HOST": "github.com"}
    monkeypatch.setattr(Gh, "executable", lambda self: str(selected))
    monkeypatch.setattr(Gh, "run", lambda *args, **kwargs: GhResult(0, b"synthetic-fixture-gh-credential\n", ""))
    monkeypatch.setattr(feeds, "hosts_file", lambda: hosts)
    monkeypatch.setattr(feeds, "environment", lambda *args: dict(environment))
    captured = feeds._CapturedGh(GithubSettings())
    try:
        assert captured.path != selected
        assert captured.path.read_bytes() == selected.read_bytes()
        assert captured.execution_environment("github.com")["GH_TOKEN"] == "synthetic-fixture-gh-credential"
        assert captured.execution_environment("github.com")["GH_CONFIG_DIR"] != str(tmp_path)
        captured.check()
        hosts.write_text("github.com:\n    user: different\n")
        with pytest.raises(HeinzelError, match="changed"):
            captured.check()
    finally:
        path = captured.path
        captured.close()
        assert not path.exists()
        assert captured.execution_environment("github.com") == {}


@pytest.mark.parametrize("draft_count", [1, 100])
def test_full_raw_page_cannot_advance_cursor_past_unseen_published_releases(rig, draft_count):
    from types import MethodType

    lease, page, _, calls = rig
    baseline = lease.baseline()
    published = [release(number, "v1.1.0", "2026-11-03T10:00:00Z") for number in range(2, 102 - draft_count)]
    drafts = [{"id": number, "draft": True, "published_at": None} for number in range(200, 200 + draft_count)]
    first = published + drafts
    assert len(first) == 100
    hidden = release(500, "v1.1.0", "2026-11-02T10:00:00Z")
    provider_pages = []

    def pages(*args):
        provider_pages.append(first)
        yield first
        provider_pages.append([hidden])
        yield [hidden]

    lease.client.pages = pages
    lease._releases = MethodType(feeds._FeedLease._releases, lease)
    with pytest.raises(HeinzelError, match="incomplete"):
        lease.poll(baseline.cursor)
    assert calls == []  # No notes read and no page/cursor returned from an incomplete observation.
    assert provider_pages == [first]
    # A later complete observation still starts from the same supplied frontier.
    lease._releases = lambda: [page[0], hidden]
    assert [item.identity for item in lease.poll(baseline.cursor).releases] == ["acme/widgets:release:500"]


@pytest.mark.parametrize("draft_count", [0, 1, 100])
def test_full_raw_page_refuses_an_incomplete_baseline_including_all_drafts(rig, draft_count):
    lease, page, _, calls = rig
    page[:] = [release(number, "v1.1.0", "2026-11-03T10:00:00Z") for number in range(1, 101 - draft_count)]
    page.extend({"id": number, "draft": True, "published_at": None} for number in range(200, 200 + draft_count))
    assert len(page) == 100
    with pytest.raises(HeinzelError, match="incomplete"):
        lease.baseline()
    assert calls == []


def test_short_complete_raw_page_may_include_drafts_without_inventing_releases(rig):
    lease, page, _, calls = rig
    page.extend({"id": number, "draft": True, "published_at": None} for number in range(2, 100))
    assert len(page) == 99
    baseline = lease.baseline()
    assert lease.poll(baseline.cursor).releases == ()
    assert calls == []
