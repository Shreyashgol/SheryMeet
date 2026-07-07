"""LLM provider backed by OpenAI's Chat Completions API.

Alternative to the default Claude provider. The `openai` SDK is imported lazily so
this module is importable without the optional 'llm' extra. Vendor exceptions are
mapped onto the domain error hierarchy at the boundary.
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


class OpenAIProvider(LLMProvider):
    """Generate completions with OpenAI chat models."""

    name = "openai"

    def __init__(
        self,
        api_key: str,
        *,
        model: str,
        timeout: int,
        base_url: str | None = None,
    ) -> None:
        if not api_key:
            raise PermanentError(
                f"An API key is required for the {self.name} provider",
                stage=StageName.SUMMARIZATION,
            )
        self.model = model
        self._api_key = api_key
        self._timeout = timeout
        self._base_url = base_url
        self._client = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional dep
            raise PermanentError(
                "openai package not installed; install the 'llm' extra",
                stage=StageName.SUMMARIZATION,
            ) from exc
        # base_url lets OpenAI-compatible backends (e.g. Groq) reuse this client.
        self._client = OpenAI(api_key=self._api_key, timeout=self._timeout, base_url=self._base_url)

    def complete(self, request: LLMRequest) -> LLMResponse:
        self._ensure_client()
        assert self._client is not None
        import openai

        try:
            completion = self._client.chat.completions.create(
                model=self.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": request.system},
                    {"role": "user", "content": request.user},
                ],
            )
        except openai.APITimeoutError as exc:
            raise LLMTimeoutError("OpenAI request timed out", stage=StageName.SUMMARIZATION) from exc
        except openai.RateLimitError as exc:
            raise LLMRateLimitError("OpenAI rate limited", stage=StageName.SUMMARIZATION) from exc
        except openai.APIConnectionError as exc:
            raise LLMServerError("OpenAI connection error", stage=StageName.SUMMARIZATION) from exc
        except openai.APIStatusError as exc:
            if exc.status_code >= 500:
                raise LLMServerError(
                    f"OpenAI server error {exc.status_code}", stage=StageName.SUMMARIZATION
                ) from exc
            raise PermanentError(
                f"OpenAI request rejected ({exc.status_code})", stage=StageName.SUMMARIZATION
            ) from exc

        text = (completion.choices[0].message.content or "").strip()
        if not text:
            raise PermanentError("OpenAI returned no content", stage=StageName.SUMMARIZATION)
        return LLMResponse(text=text, provider=self.name, model=self.model)
