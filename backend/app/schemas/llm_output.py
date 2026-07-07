"""LLM structured-output contracts.

These Pydantic models are the single source of truth for the JSON the LLM must
produce. The same schema is:
  1. embedded into the prompt (as a JSON schema) to instruct the model, and
  2. used to validate/coerce the model's response before persistence.

Validators enforce the domain invariants required by the spec — an action item is
never incomplete: missing owner → "Unknown", missing deadline → "Not Specified".
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import ActionItemStatus, Priority

UNKNOWN_OWNER = "Unknown"
UNSPECIFIED_DEADLINE = "Not Specified"


class ActionItemSchema(BaseModel):
    """A single accountable action item produced by the LLM."""

    model_config = ConfigDict(extra="ignore")

    owner: str = Field(default=UNKNOWN_OWNER)
    task: str
    deadline: str = Field(default=UNSPECIFIED_DEADLINE)
    priority: Priority = Field(default=Priority.MEDIUM)
    status: ActionItemStatus = Field(default=ActionItemStatus.PENDING)

    @field_validator("owner", mode="before")
    @classmethod
    def _default_owner(cls, value: object) -> str:
        """Blank/None owner becomes the sentinel 'Unknown'."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return UNKNOWN_OWNER
        return str(value).strip()

    @field_validator("deadline", mode="before")
    @classmethod
    def _default_deadline(cls, value: object) -> str:
        """Blank/None deadline becomes the sentinel 'Not Specified'."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return UNSPECIFIED_DEADLINE
        return str(value).strip()

    @field_validator("task")
    @classmethod
    def _task_non_empty(cls, value: str) -> str:
        """Reject empty tasks — an incomplete action item is invalid."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("action item 'task' must not be empty")
        return cleaned

    @field_validator("priority", mode="before")
    @classmethod
    def _coerce_priority(cls, value: object) -> object:
        """Accept case-insensitive priority strings; fall back to Medium."""
        if isinstance(value, str):
            normalized = value.strip().capitalize()
            if normalized in {p.value for p in Priority}:
                return normalized
            return Priority.MEDIUM.value
        return value


class MeetingSummary(BaseModel):
    """The full structured meeting intelligence object.

    Mirrors the required JSON schema exactly. Absent list fields default to empty
    lists so downstream persistence never sees `None`.
    """

    model_config = ConfigDict(extra="ignore")

    meeting_title: str = Field(default="Untitled Meeting")
    summary: str = Field(default="")
    agenda: list[str] = Field(default_factory=list)
    key_decisions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    action_items: list[ActionItemSchema] = Field(default_factory=list)

    @field_validator(
        "agenda", "key_decisions", "risks", "blockers", "next_steps", mode="before"
    )
    @classmethod
    def _coerce_str_list(cls, value: object) -> object:
        """Coerce None → [] and drop empty/blank list entries defensively."""
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        return value

    @field_validator("meeting_title", mode="before")
    @classmethod
    def _default_title(cls, value: object) -> str:
        """Blank/None title becomes a safe placeholder."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return "Untitled Meeting"
        return str(value).strip()
