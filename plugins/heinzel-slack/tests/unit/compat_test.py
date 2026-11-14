"""The local stand-ins for Core's self-channel models keep Core's rules (used only with a Core before ADR 0160)."""

import pytest
from pydantic import ValidationError

from heinzel_slack._compat import LocalSelfAnswer, LocalSelfMessage

pytestmark = pytest.mark.unit


def test_an_answer_is_text_an_option_or_a_timeout():
    assert LocalSelfAnswer(text="Later").answered_by_option is False
    assert LocalSelfAnswer(text="Yes", option="Yes").answered_by_option is True
    assert LocalSelfAnswer(timed_out=True).text == ""
    assert LocalSelfMessage(id="1.2", thread="1.2").url is None


@pytest.mark.parametrize(
    "fields", [{}, {"text": "  "}, {"timed_out": True, "text": "x"}, {"timed_out": True, "option": "Yes"}]
)
def test_inconsistent_answers_are_refused(fields):
    with pytest.raises(ValidationError):
        LocalSelfAnswer(**fields)
