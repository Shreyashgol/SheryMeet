"""Unit tests for summary/checklist services and mock providers (no DB, no network)."""

from __future__ import annotations

from app.core.exceptions import LLMOutputValidationError
from app.providers.llm.base import LLMProvider, LLMRequest, LLMResponse
from app.services.checklist_service import ChecklistService
from app.services.summary_service import SummaryService

TRANSCRIPT = "John will own the API migration by Friday. We decided to postpone mobile."


def test_summary_service_produces_valid_summary() -> None:
    from app.providers.llm.mock import MockLLMProvider

    service = SummaryService(MockLLMProvider(), max_tokens=1024, temperature=0.2)
    summary, provider, model = service.summarize(TRANSCRIPT)
    assert provider == "mock"
    assert summary.meeting_title
    assert isinstance(summary.key_decisions, list)


def test_checklist_service_extracts_items() -> None:
    from app.providers.llm.mock import MockLLMProvider

    service = ChecklistService(MockLLMProvider(), max_tokens=1024, temperature=0.2)
    items = service.extract("Extract the action items from this meeting.")
    assert len(items) >= 1
    assert all(item.task for item in items)
    assert all(item.owner for item in items)  # never empty (defaulted to Unknown)


class _BadThenGoodProvider(LLMProvider):
    """Returns invalid JSON first, valid JSON on the reprompt — exercises recovery."""

    name = "bad-then-good"
    model = "test"

    def __init__(self) -> None:
        self._calls = 0

    def complete(self, request: LLMRequest) -> LLMResponse:
        self._calls += 1
        if self._calls == 1:
            return LLMResponse(text="not json at all", provider=self.name, model=self.model)
        return LLMResponse(
            text='{"meeting_title":"T","summary":"s","action_items":[]}',
            provider=self.name,
            model=self.model,
        )


def test_summary_service_reprompts_on_invalid_json() -> None:
    service = SummaryService(_BadThenGoodProvider(), max_tokens=512, temperature=0.2)
    summary, _, _ = service.summarize(TRANSCRIPT)
    assert summary.meeting_title == "T"


class _AlwaysBadProvider(LLMProvider):
    name = "always-bad"
    model = "test"

    def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text="never json", provider=self.name, model=self.model)


def test_summary_service_fails_permanently_after_reprompt() -> None:
    service = SummaryService(_AlwaysBadProvider(), max_tokens=512, temperature=0.2)
    try:
        service.summarize(TRANSCRIPT)
        assert False, "expected LLMOutputValidationError"
    except LLMOutputValidationError:
        pass
