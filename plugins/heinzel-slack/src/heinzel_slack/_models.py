"""What the plugin's own operations return. The channel messages themselves are core's (ADR 0112)."""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field

from heinzel_slack._digest import draft_digest

State = Literal["posting", "pending", "approved", "declined", "expired", "superseded", "failed"]
DECIDED: frozenset[str] = frozenset({"approved", "declined"})


class SharedDraft(BaseModel):
    """A draft shared for approval with the `ask` operation."""

    request_id: str = Field(description="Identifier of this request.")
    digest: str = Field(description="sha256 of the exact draft bytes (domain-separated); an approval is for this.")
    state: State = Field(description="Where the request stands.")
    expires_at: AwareDatetime = Field(description="After this an answer is refused.")


class DraftStanding(BaseModel):
    """Where a shared draft stands. A decision is data about a click; it is not a bearer of authority."""

    request_id: str = Field(description="Identifier of the request.")
    state: State = Field(description="`approved` and `declined` are decisions; everything else is not an approval.")
    digest: str = Field(description="The digest the request is bound to.")
    approver: str | None = Field(default=None, description="Who decided: `slack:<team>:<user>`.")
    decided_at: AwareDatetime | None = Field(default=None, description="When the decision was recorded.")
    detail: str = Field(default="", description="A plain sentence on the state; never Slack text.")

    def approves(self, draft: str) -> bool:
        """Whether this is an approval of exactly `draft`: approved, and the same bytes."""
        return self.state == "approved" and self.digest == draft_digest(draft)
