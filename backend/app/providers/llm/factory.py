"""LLM provider factory — selects the summarization/extraction backend from config.

Callers depend on the `LLMProvider` interface and obtain a concrete instance here,
so switching between Claude, OpenAI, Gemini, or the test mock is a configuration
change (Dependency Injection / Open-Closed). Real providers are imported lazily.
"""

from __future__ import annotations

from functools import lru_cache

from app.config.settings import get_settings
from app.providers.llm.base import LLMProvider
from app.providers.llm.mock import MockLLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider singleton."""
    settings = get_settings()
    provider = settings.llm_provider

    if provider == "mock":
        return MockLLMProvider()

    if provider == "claude":
        from app.providers.llm.claude import ClaudeProvider

        return ClaudeProvider(
            settings.anthropic_api_key,
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
        )

    if provider == "openai":
        from app.providers.llm.openai import OpenAIProvider

        return OpenAIProvider(
            settings.openai_api_key,
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
        )

    if provider == "gemini":
        from app.providers.llm.gemini import GeminiProvider

        return GeminiProvider(
            settings.gemini_api_key,
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
        )

    if provider == "groq":
        from app.providers.llm.groq import GroqProvider

        return GroqProvider(
            settings.groq_api_key,
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
            base_url=settings.groq_base_url,
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")
