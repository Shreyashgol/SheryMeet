"""Structured summarization service (Phase 8).

Wraps the injected `LLMProvider`: builds the summary prompt, applies transient
retry to the LLM call, then parses and validates the response against the
`MeetingSummary` schema. On invalid JSON it performs one bounded reprompt before
failing permanently, so a single malformed response never sinks a job silently.
"""

from __future__ import annotations

from pydantic import ValidationError

from app.core.enums import StageName
from app.core.exceptions import LLMOutputValidationError
from app.core.logging import get_logger
from app.prompts.summary_prompt import build_summary_prompt
from app.providers.llm.base import LLMProvider, LLMRequest
from app.schemas.llm_output import MeetingSummary
from app.utils.json_repair import extract_json_object
from app.utils.retry import with_transient_retry

log = get_logger(__name__)


class SummaryService:
    """Generate a validated `MeetingSummary` from a cleaned transcript."""

    def __init__(self, provider: LLMProvider, *, max_tokens: int, temperature: float) -> None:
        self._provider = provider
        self._max_tokens = max_tokens
        self._temperature = temperature

    def summarize(self, transcript: str) -> tuple[MeetingSummary, str, str]:
        """Return (summary, provider_name, model) for the transcript.

        Raises:
            LLMOutputValidationError: if a valid object cannot be produced after a
                bounded reprompt.
        """
        system, user = build_summary_prompt(transcript)
        request = LLMRequest(
            system=system,
            user=user,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
        )

        complete = with_transient_retry(self._provider.complete)
        response = complete(request)

        try:
            data = self._parse(response.text)
        except LLMOutputValidationError:
            log.warning("summary_invalid_json_reprompting")
            retry_request = LLMRequest(
                system=system,
                user=user + "\n\nReturn ONLY the JSON object, with no other text.",
                max_tokens=self._max_tokens,
                temperature=0.0,
            )
            response = complete(retry_request)
            data = self._parse(response.text)

        log.info("summary_generated", provider=response.provider, model=response.model)
        return data, response.provider, response.model

    @staticmethod
    def _parse(text: str) -> MeetingSummary:
        """Extract and validate a `MeetingSummary` from raw LLM text."""
        try:
            payload = extract_json_object(text)
            return MeetingSummary.model_validate(payload)
        except (ValueError, ValidationError) as exc:
            raise LLMOutputValidationError(
                f"Could not parse summary JSON: {str(exc)[:200]}", stage=StageName.SUMMARIZATION
            ) from exc
