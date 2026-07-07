"""Unit tests for the LLM output schemas and their defaulting rules."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.enums import ActionItemStatus, Priority
from app.schemas.llm_output import ActionItemSchema, MeetingSummary


def test_action_item_defaults_unknown_owner_and_deadline() -> None:
    item = ActionItemSchema(task="Ship the release")
    assert item.owner == "Unknown"
    assert item.deadline == "Not Specified"
    assert item.status == ActionItemStatus.PENDING
    assert item.priority == Priority.MEDIUM


def test_action_item_blank_owner_becomes_unknown() -> None:
    item = ActionItemSchema(owner="   ", task="Do it", deadline="")
    assert item.owner == "Unknown"
    assert item.deadline == "Not Specified"


def test_action_item_rejects_empty_task() -> None:
    with pytest.raises(ValidationError):
        ActionItemSchema(task="   ")


def test_action_item_coerces_unknown_priority_to_medium() -> None:
    item = ActionItemSchema(task="x", priority="urgent")
    assert item.priority == Priority.MEDIUM


def test_meeting_summary_coerces_none_lists_to_empty() -> None:
    summary = MeetingSummary.model_validate(
        {"meeting_title": "", "summary": "s", "agenda": None, "risks": ["", "  ", "real"]}
    )
    assert summary.meeting_title == "Untitled Meeting"
    assert summary.agenda == []
    assert summary.risks == ["real"]
