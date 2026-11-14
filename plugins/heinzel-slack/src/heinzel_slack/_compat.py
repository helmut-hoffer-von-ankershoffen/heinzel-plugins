"""Core's self-channel contract (ADR 0160), from Core when it has it.

A Core that ships it is used as is: these names are then Core's own classes, so what the adapter returns is exactly
what Core validates. An older Core gets local stand-ins with the same fields, rules and limits so the plugin loads
and its tests run; such a Core never calls the self-channel methods. Remove this module once the plugin requires a
Core with ADR 0160.
"""

from typing import TYPE_CHECKING, Self

import heinzel
from pydantic import BaseModel, ConfigDict, Field, model_validator

LOCAL_SELF_OPTIONS = 10
LOCAL_SELF_OPTION_LENGTH = 75
LOCAL_SELF_CONTEXT_LENGTH = 60


class LocalSelfMessage(BaseModel):
    """What `Chat.notify_self` posted (stand-in for Core's `SelfMessage`)."""

    id: str = Field(description="Identifier of the new message, in the adapter's notation.")
    thread: str = Field(description="Handle to pass back as `thread`; for a top-level message, the thread it starts.")
    url: str | None = Field(default=None, description="Where people open it; none if it has no web address.")


class LocalSelfAnswer(BaseModel):
    """The person's answer to `Chat.ask_self` (stand-in for Core's `SelfAnswer`)."""

    model_config = ConfigDict(frozen=True)

    thread: str | None = Field(default=None, description="Thread the question and its answer are in.")
    text: str = Field(default="", description="Typed reply, or the chosen button's label.")
    option: str | None = Field(default=None, description="Chosen option exactly as offered; none for a typed reply.")
    timed_out: bool = Field(default=False, description="No answer before the timeout, or the wait was cancelled.")

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.timed_out and (self.text or self.option is not None):
            msg = "A timed-out answer carries no text and no option"
            raise ValueError(msg)
        if not self.timed_out and not self.text.strip() and self.option is None:
            msg = "An answer carries text or an option"
            raise ValueError(msg)
        return self

    @property
    def answered_by_option(self) -> bool:
        """Whether a button, not a typed reply, answered."""
        return self.option is not None


if TYPE_CHECKING:
    SelfMessage = LocalSelfMessage
    SelfAnswer = LocalSelfAnswer
    SELF_OPTIONS = LOCAL_SELF_OPTIONS
    SELF_OPTION_LENGTH = LOCAL_SELF_OPTION_LENGTH
    SELF_CONTEXT_LENGTH = LOCAL_SELF_CONTEXT_LENGTH
else:
    SelfMessage = getattr(heinzel, "SelfMessage", LocalSelfMessage)
    SelfAnswer = getattr(heinzel, "SelfAnswer", LocalSelfAnswer)
    SELF_OPTIONS = getattr(heinzel, "SELF_OPTIONS", LOCAL_SELF_OPTIONS)
    SELF_OPTION_LENGTH = getattr(heinzel, "SELF_OPTION_LENGTH", LOCAL_SELF_OPTION_LENGTH)
    SELF_CONTEXT_LENGTH = getattr(heinzel, "SELF_CONTEXT_LENGTH", LOCAL_SELF_CONTEXT_LENGTH)

CORE_HAS_SELF_CHANNEL = hasattr(heinzel, "SelfAnswer")
"""Whether the running Core defines the self channel (ADR 0160); otherwise the local stand-ins are in use."""

__all__ = [
    "CORE_HAS_SELF_CHANNEL",
    "SELF_CONTEXT_LENGTH",
    "SELF_OPTIONS",
    "SELF_OPTION_LENGTH",
    "SelfAnswer",
    "SelfMessage",
]
