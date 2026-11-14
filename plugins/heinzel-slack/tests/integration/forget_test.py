"""Forgetting a request leaves no byte of it on disk: not in the database, a free page, the WAL or the shm (ADR 0148).

The canary test is its own positive control: the same search first finds every canary in the files, so a search that
could not see them would fail before it could pass.
"""

import json
import sqlite3
from pathlib import Path

import pytest
from heinzel import HeinzelError

from heinzel_slack import slot

pytestmark = pytest.mark.integration

ASCII = "CANARY-ascii-5f0c9e2a71d4"
KEPT = "KEPT-other-request-8b31"


def _canaries(tag: str) -> dict[str, str]:
    """Unique canaries in plain ASCII, in UTF-8 beyond ASCII, and in their JSON-escaped form."""
    wide = f"Kanarienvögel-ÄÖÜß-猫の歌-{tag}"
    return {"ascii": f"CANARY-{tag}-ascii", "utf-8": wide, "json": json.dumps(wide)[1:-1]}


POSTED = _canaries("posted-5f0c9e2a71d4")
LOST = _canaries("lost-0b7d63e4a925")
NEEDLES = {
    f"{group}:{form}": text.encode() for group, c in (("posted", POSTED), ("lost", LOST)) for form, text in c.items()
}


def _draft(*lines: str) -> str:
    text = "\n".join(lines) + "\n"
    return text + "x" * (3_990 - len(text))  # near the 4000-character limit: the row spills into overflow pages


def _planted(canaries: dict[str, str]) -> str:
    return _draft(*canaries.values(), json.dumps({"note": canaries["utf-8"]}))


def _found(folder: Path) -> dict[str, set[str]]:
    hits: dict[str, set[str]] = {}
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        data = path.read_bytes()
        hits[path.name] = {name for name, needle in NEEDLES.items() if needle in data}
    return hits


def test_forget_leaves_no_canary_in_any_file_of_the_state_dir(rig, tmp_path):
    state = tmp_path / "state"
    db_path = state / "slack" / "approvals.sqlite3"
    kept = rig.channel.post(rig.request(_draft(KEPT), request_id="req-kept"))
    # A second connection stays open, as the listener's would: SQLite then keeps the -wal and -shm files around.
    holder = sqlite3.connect(db_path, isolation_level=None)
    try:
        holder.execute("SELECT count(*) FROM requests").fetchone()
        receipt = rig.channel.post(rig.request(_planted(POSTED), request_id="req-posted"))
        ref = receipt.reference
        assert receipt.status == "delivered"
        assert ref
        rig.slack.lose_post = True  # stored before posting, and Slack never answered: no reference, still content
        lost = rig.channel.post(rig.request(_planted(LOST), request_id="req-lost"))
        assert (lost.status, lost.reference) == ("unknown", None)
        rig.slack.lose_post = False
        holder.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()  # the canaries reach the main database
        rig.service.handle(rig.click(ref))  # an UPDATE writes the whole row again: a stale copy in the WAL
        rig.channel.settle(ref, "approved")
        rig.channel.settle(slot("req-lost"), "superseded")  # and the never-posted row too

        before = _found(state)
        assert set(before) >= {"approvals.sqlite3", "approvals.sqlite3-wal", "approvals.sqlite3-shm"}
        assert before["approvals.sqlite3"] == set(NEEDLES)  # positive control: the search sees every form
        assert before["approvals.sqlite3-wal"] == set(NEEDLES)

        rig.channel.forget("req-posted", ref)
        rig.channel.forget("req-lost", None)

        after = _found(state)
        assert after == {name: set() for name in after}, after
        assert holder.execute("PRAGMA freelist_count").fetchone() == (0,)  # VACUUM left no free page behind
        assert db_path.with_name("approvals.sqlite3-wal").stat().st_size == 0
        for gone in (ref, slot("req-lost")):
            assert rig.service.store.get(gone) is None
            assert rig.service.store.audit(gone) == []
        survivor = rig.service.store.get(kept.reference or "")
        assert survivor is not None
        assert KEPT in survivor.draft  # only the forgotten requests went
    finally:
        holder.close()


@pytest.mark.parametrize(("request_id", "reference"), [("req-1", None), ("req-1", "ref"), ("other", "ref")])
def test_either_key_finds_the_request(rig, request_id, reference):
    ref = rig.post().reference or ""
    rig.channel.forget(request_id, ref if reference == "ref" else reference)
    assert rig.service.store.get(ref) is None
    assert rig.service.store.by_external("req-1") is None


def test_forget_is_idempotent_and_quiet_about_unknown_references(rig):
    ref = rig.post().reference or ""
    rig.service.store.begin_delivery("req-1", rig.now[0])
    rig.channel.forget("req-1", ref)
    rig.channel.forget("req-1", ref)
    assert rig.service.store.delivery("req-1") is None
    rig.channel.forget("not-a-request", "not-a-reference")
    rig.channel.forget("", None)
    assert rig.service.store.get(ref) is None


def test_forget_without_any_store_creates_nothing(rig, tmp_path):
    rig.channel.forget("never-posted", None)
    assert not (tmp_path / "state" / "slack").exists()


def test_an_open_request_is_withdrawn_in_slack_without_its_draft(rig):
    ref = rig.post(preview=_draft(ASCII)).reference or ""
    rig.channel.forget("req-1", ref)
    for thread in rig.service.withdrawing:
        thread.join(5)
    update = rig.slack.updates[-1]
    assert update["text"] == "Withdrawn"
    assert ASCII not in json.dumps(update)
    assert not any(b["type"] == "actions" for b in update["blocks"])


def test_forget_never_waits_on_or_fails_because_of_the_network(rig, monkeypatch):
    ref = rig.post(preview=_draft(ASCII)).reference or ""

    def offline() -> None:
        raise HeinzelError("Slack is unreachable")

    monkeypatch.setattr(rig.slack, "identity", offline)
    rig.channel.forget("req-1", ref)
    for thread in rig.service.withdrawing:
        thread.join(5)
    assert rig.slack.updates == []
    assert rig.service.store.get(ref) is None


def _settled(rig) -> None:
    for thread in rig.service.withdrawing:
        thread.join(5)


@pytest.mark.parametrize("answer", [None, "hz_approve", "hz_decline"])
def test_cores_order_settle_superseded_then_forget_leaves_no_draft_in_slack(rig, answer):
    ref = rig.post(preview=_planted(POSTED), request_id="req-core").reference or ""
    if answer:
        rig.service.handle(rig.click(ref, action=answer))
    rig.channel.settle(ref, "superseded")  # Core settles first; Slack then shows the whole draft as replaced
    assert POSTED["ascii"] in json.dumps(rig.slack.updates[-1])
    rig.channel.forget("req-core", ref)
    _settled(rig)
    final = rig.slack.updates[-1]
    assert final["ts"] == rig.slack.updates[0]["ts"]
    assert final["text"] == "Withdrawn"
    assert not any(text in json.dumps(final, ensure_ascii=False) for text in POSTED.values())
    assert not any(b["type"] == "actions" for b in final["blocks"])
    assert rig.service.store.matching({"req-core", ref}) == []
    assert rig.service.store.audit(ref) == []


def test_a_retry_after_a_busy_store_has_already_withdrawn(rig, monkeypatch):
    ref = rig.post(preview=_draft(ASCII)).reference or ""
    store = rig.service.store
    real = store.forget

    def busy_once(keys):
        real(keys)
        monkeypatch.setattr(store, "forget", real)
        raise HeinzelError("Slack approval storage is in use")

    monkeypatch.setattr(store, "forget", busy_once)
    with pytest.raises(HeinzelError, match="in use"):
        rig.channel.forget("req-1", ref)
    rig.channel.forget("req-1", ref)  # the retry finishes the local job
    _settled(rig)
    assert [u["text"] for u in rig.slack.updates] == ["Withdrawn"]


def test_finished_withdrawals_are_not_kept(rig):
    for n in range(3):
        ref = rig.post(request_id=f"req-{n}").reference or ""
        rig.channel.forget(f"req-{n}", ref)
        _settled(rig)
    assert len(rig.service.withdrawing) == 1


def test_forget_works_offline_with_the_bot_off_and_sends_nothing(rig, monkeypatch):
    ref = rig.post().reference or ""
    monkeypatch.setattr(rig.service, "usable", lambda: False)
    rig.channel.forget("req-1", ref)
    assert rig.service.withdrawing == []
    assert rig.service.store.get(ref) is None


def test_a_withdrawal_never_goes_to_another_direct_message(rig):
    ref = rig.post().reference or ""
    rig.slack.dm = "D0ELSEWHERE"
    rig.channel.forget("req-1", ref)
    for thread in rig.service.withdrawing:
        thread.join(5)
    assert rig.slack.updates == []
