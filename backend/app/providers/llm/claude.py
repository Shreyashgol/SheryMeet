"""LLM provider backed by Anthropic's Claude (the default provider).

Uses the official `anthropic` SDK. The SDK is imported lazily so this module is
importable without the optional 'llm' extra installed. Vendor exceptions are
mapped onto the application's transient/permanent error hierarchy at the boundary,
so business code never sees an `anthropic.*` exception type.
"""

from __future__ import annotations

from app.core.enums import StageName
from app.core.exceptions import (
    LLMRateLimitError,
    LLMServerError,
    LLMTimeoutError,
    PermanentError,
)
from app.core.logging import get_logger
from app.providers.llm.base import LLMProvider, LLMRequest, LLMResponse

log = get_logger(__name__)


class ClaudeProvider(LLMProvider):
    """Generate completions with Anthropic Claude via the Messages API."""

    name = "claude"

    def __init__(self, api_key: str, *, model: str, timeout: int) -> None:
        if not api_key:
            raise PermanentError(
                "ANTHROPIC_API_KEY is required for the Claude provider",
                stage=StageName.SUMMARIZATION,
            )
        self.model = model
        self._api_key = api_key
        self._timeout = timeout
        self._client = None  # lazy

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - optional dep
            raise PermanentError(
                "anthropic package not installed; install the 'llm' extra",
                stage=StageName.SUMMARIZATION,
            ) from exc
        self._client = anthropic.Anthropic(api_key=self._api_key, timeout=self._timeout)

    def complete(self, request: LLMRequest) -> LLMResponse:
        self._ensure_client()
        assert self._client is not None
        import anthropic

        try:
            message = self._client.messages.create(
                model=self.model,
                max_tokens=request.max_tokens,
                system=request.system,
                messages=[{"role": "user", "content": request.user}],
            )
        except anthropic.APITimeoutError as exc:
            raise LLMTimeoutError("Claude request timed out", stage=StageName.SUMMARIZATION) from exc
        except anthropic.RateLimitError as exc:
            raise LLMRateLimitError("Claude rate limited", stage=StageName.SUMMARIZATION) from exc
        except anthropic.APIConnectionError as exc:
            raise LLMServerError(
                "Claude connection error", stage=StageName.SUMMARIZATION
            ) from exc
        except anthropic.APIStatusError as exc:
            if exc.status_code >= 500:
                raise LLMServerError(
                    f"Claude server error {exc.status_code}", stage=StageName.SUMMARIZATION
                ) from exc
            raise PermanentError(
                f"Claude request rejected ({exc.status_code}): {exc.message}",
                stage=StageName.SUMMARIZATION,
            ) from exc

        text = "".join(block.text for block in message.content if block.type == "text").strip()
        if not text:
            raise PermanentError(
                "Claude returned no text content", stage=StageName.SUMMARIZATION
            )
        return LLMResponse(text=text, provider=self.name, model=self.model)
