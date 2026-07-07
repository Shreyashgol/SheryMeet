"""Accountable checklist extraction service (Phase 9).

Wraps the injected `LLMProvider` to extract action items independently of
summarization. Validates each item against `ActionItemSchema` (which enforces the
owner/deadline/status defaulting rules), so no incomplete action item can be
produced. Performs one bounded reprompt on invalid JSON.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError

from app.core.enums import StageName
from app.core.exceptions import LLMOutputValidationError
from app.core.logging import get_logger
from app.prompts.checklist_prompt import build_checklist_prompt
from app.providers.llm.base import LLMProvider, LLMRequest
from app.schemas.llm_output import ActionItemSchema
from app.utils.json_repair import extract_json_object
from app.utils.retry import with_transient_retry

log = get_logger(__name__)


class _ChecklistEnvelope(BaseModel):
    """Validation envelope for the checklist LLM response."""

    action_items: list[ActionItemSchema] = Field(default_factory=list)


class ChecklistService:
    """Extract validated action items from a cleaned transcript."""

    def __init__(self, provider: LLMProvider, *, max_tokens: int, temperature: float) -> None:
        self._provider = provider
        self._max_tokens = max_tokens
        self._temperature = temperature

    def extract(self, transcript: str) -> list[ActionItemSchema]:
        """Return the list of validated action items for the transcript.

        Raises:
            LLMOutputValidationError: if valid items cannot be produced after a
                bounded reprompt.
        """
        system, user = build_checklist_prompt(transcript)
        request = LLMRequest(
            system=system,
            user=user,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
        )

        complete = with_transient_retry(self._provider.complete)
        response = complete(request)

        try:
            items = self._parse(response.text)
        except LLMOutputValidationError:
            log.warning("checklist_invalid_json_reprompting")
            retry_request = LLMRequest(
                system=system,
                user=user + "\n\nReturn ONLY the JSON object, with no other text.",
                max_tokens=self._max_tokens,
                temperature=0.0,
            )
            response = complete(retry_request)
            items = self._parse(response.text)

        log.info("checklist_extracted", count=len(items))
        return items

    @staticmethod
    def _parse(text: str) -> list[ActionItemSchema]:
        """Extract and validate the action-item list from raw LLM text."""
        try:
            payload = extract_json_object(text)
            return _ChecklistEnvelope.model_validate(payload).action_items
        except (ValueError, ValidationError) as exc:
            raise LLMOutputValidationError(
                f"Could not parse checklist JSON: {str(exc)[:200]}", stage=StageName.CHECKLIST
            ) from exc
