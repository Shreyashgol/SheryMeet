"""LLM provider backed by Groq.

Groq serves an OpenAI-compatible Chat Completions API, so this provider reuses
`OpenAIProvider` and only overrides the identity (`name`) and the base URL. The
`openai` SDK is still imported lazily by the parent class.
"""

from __future__ import annotations

from app.providers.llm.openai import OpenAIProvider


class GroqProvider(OpenAIProvider):
    """Generate completions with Groq (OpenAI-compatible endpoint)."""

    name = "groq"

    def __init__(self, api_key: str, *, model: str, timeout: int, base_url: str) -> None:
        super().__init__(api_key, model=model, timeout=timeout, base_url=base_url)
