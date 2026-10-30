"""Optional host item-evidence declaration for bounded returned provider IDs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import heinzel

if TYPE_CHECKING:
    from heinzel import ConnectedReadReview

MAX_ITEMS = 100


def with_item_identity(review: ConnectedReadReview) -> ConnectedReadReview:
    """Declare only returned root-array IDs when the host supports the exact optional contract."""
    if getattr(heinzel, "ConnectedItemIdentity", None) is None or "item_identity" not in type(review).model_fields:
        return review
    return type(review).model_validate(
        {**review.model_dump(mode="json"), "item_identity": {"collection": [], "identity_field": "id"}}
    )
