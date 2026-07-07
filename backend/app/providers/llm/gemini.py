"""LLM provider backed by Google Gemini.

Alternative to the default Claude provider. The `google.generativeai` SDK is
imported lazily so this module is importable without the optional 'llm' extra.
"""

from __future__ import annotations

from app.core.enums import StageName
from app.core.exceptions import LLMServerError, LLMTimeoutError, PermanentError
from app.core.logging import get_logger
from app.providers.llm.base import LLMProvider, LLMRequest, LLMResponse

log = get_logger(__name__)


class GeminiProvider(LLMProvider):
    """Generate completions with Google Gemini models."""

    name = "gemini"

    def __init__(self, api_key: str, *, model: str, timeout: int) -> None:
        if not api_key:
            raise PermanentError(
                "GEMINI_API_KEY is required for the Gemini provider",
                stage=StageName.SUMMARIZATION,
            )
        self.model = model
        self._api_key = api_key
        self._timeout = timeout
        self._model_client = None

    def _ensure_client(self) -> None:
        if self._model_client is not None:
            return
        try:
            import google.generativeai as genai
        except ImportError as exc:  # pragma: no cover - optional dep
            raise PermanentError(
                "google-generativeai not installed; install the 'llm' extra",
                stage=StageName.SUMMARIZATION,
            ) from exc
        genai.configure(api_key=self._api_key)
        self._model_client = genai.GenerativeModel(self.model)

    def complete(self, request: LLMRequest) -> LLMResponse:
        self._ensure_client()
        assert self._model_client is not None
        prompt = f"{request.system}\n\n{request.user}"
        try:
            response = self._model_client.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "response_mime_type": "application/json",
                },
                request_options={"timeout": self._timeout},
            )
        except TimeoutError as exc:  # pragma: no cover - runtime dependent
            raise LLMTimeoutError("Gemini request timed out", stage=StageName.SUMMARIZATION) from exc
        except Exception as exc:  # noqa: BLE001 - SDK raises a broad set of errors
            raise LLMServerError(
                f"Gemini error: {str(exc)[:200]}", stage=StageName.SUMMARIZATION
            ) from exc

        text = (getattr(response, "text", "") or "").strip()
        if not text:
            raise PermanentError("Gemini returned no content", stage=StageName.SUMMARIZATION)
        return LLMResponse(text=text, provider=self.name, model=self.model)
