"""Settings: the `[slack]` table of the `hz` config files, or `HZ_SLACK__<FIELD>`."""

from typing import ClassVar

from heinzel import ModuleSettings
from pydantic import Field


class SlackSettings(ModuleSettings):
    """Whose Slack this is, and how long a draft may wait for a yes.

    All of it is ignored in a project hz.toml: a repository must not choose whose direct message receives your drafts.
    """

    owner: str = Field(
        default="",
        pattern=r"^([UW][A-Z0-9]{6,20})?$",
        title="Your Slack member ID",
        description="Your member ID in the workspace (profile, three dots, Copy member ID), like U01ABCDEF. "
        "Drafts and notices go to your direct message with the app, and only your click approves.",
        examples=["U01ABCDEF"],
    )
    team: str = Field(
        default="",
        pattern=r"^(T[A-Z0-9]{6,20})?$",
        title="Workspace ID",
        description="Optional: the workspace ID the app must belong to (like T01ABCDEF); another's token is refused.",
    )
    approval_minutes: int = Field(
        default=240,
        ge=1,
        le=10_080,
        title="Time to answer",
        description="How long a shared draft can be approved or declined; after that it expires.",
        json_schema_extra={"x-unit": "minutes"},
    )
    timeout: float = Field(
        default=30.0,
        gt=0,
        le=120,
        title="Time limit",
        description="How long to wait for each Slack call.",
        json_schema_extra={"x-expert": True, "x-unit": "seconds"},
    )

    ignored_in_project: ClassVar[frozenset[str]] = frozenset({"owner", "team", "approval_minutes", "timeout"})
