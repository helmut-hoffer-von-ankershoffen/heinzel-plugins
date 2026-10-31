import pytest
from heinzel import HeinzelError

from heinzel_slack import check_draft, draft_digest

pytestmark = pytest.mark.unit


def test_digest_is_of_the_exact_bytes():
    assert draft_digest("a") == draft_digest("a")
    assert draft_digest("a") != draft_digest("a ")
    assert draft_digest("é") != draft_digest("é")  # no normalisation: bytes are bytes
    assert len(draft_digest("a")) == 64


@pytest.mark.parametrize(
    "draft",
    ["", "   \n", "x" * 4_001, "hi‮there", "zero​width", "nul\x00", "bell\x07", "carriage\rreturn"],
)
def test_drafts_a_person_could_not_review_are_refused(draft):
    with pytest.raises(HeinzelError):
        check_draft(draft)


def test_ordinary_drafts_pass():
    check_draft("Weekly report\n\n- shipped the thing\n\tindented ✓ äöü <b>&</b> <!channel>")
