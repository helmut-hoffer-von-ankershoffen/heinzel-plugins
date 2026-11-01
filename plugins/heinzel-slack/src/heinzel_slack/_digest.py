"""The exact bytes of a draft, their digest, and what a draft may contain."""

import hashlib

from heinzel import HeinzelError, clean_text

MAX_DRAFT = 4_000
"""Most characters of a draft Slack will show in full; a longer one is not approved here, because the person could
not read all of it."""
_DOMAIN = b"hz-slack-draft-v1\0"


def draft_digest(draft: str) -> str:
    """The sha256 of the draft's UTF-8 bytes under this plugin's domain prefix, as 64 lower-case hex digits."""
    return hashlib.sha256(_DOMAIN + draft.encode("utf-8")).hexdigest()


def check_draft(draft: str) -> None:
    """Refuse a draft a person could not review as it is.

    The text is approved byte for byte, so nothing may be hidden in it: control, zero-width and bidirectional
    characters are refused rather than cleaned (cleaning would change what is approved).

    Raises:
        HeinzelError: If the draft is empty, too long, or has characters that hide or reorder text.
    """
    if not draft.strip():
        msg = "The draft is empty; there is nothing to approve"
        raise HeinzelError(msg)
    if len(draft) > MAX_DRAFT:
        msg = f"The draft has {len(draft):,} characters; Slack shows {MAX_DRAFT:,} at most, so review it locally"
        raise HeinzelError(msg)
    if clean_text(draft) != draft:
        msg = "The draft has control, zero-width or bidirectional characters that hide text; remove them"
        raise HeinzelError(msg)
    try:
        draft.encode("utf-8")
    except UnicodeEncodeError:
        msg = "The draft is not valid Unicode text"
        raise HeinzelError(msg) from None
