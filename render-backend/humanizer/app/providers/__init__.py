"""
Provider factory — naam do, provider object milega.
"""
from app.config import settings
from app.providers.base import LLMProvider, ProviderError
from app.providers import openai_compatible as oc
from app.providers.gemini_provider import GeminiProvider

_FACTORIES = {
    "groq": oc.groq,
    "openrouter": oc.openrouter,
    "openai": oc.openai,
    "ollama": oc.ollama,
    "gemini": GeminiProvider,
}

AVAILABLE = list(_FACTORIES.keys())


def get_provider(name: str | None = None) -> LLMProvider:
    key = (name or settings.llm_provider or "groq").lower().strip()
    if key not in _FACTORIES:
        raise ProviderError(
            f"'{key}' provider maujood nahi. Available: {', '.join(AVAILABLE)}"
        )
    return _FACTORIES[key]()


__all__ = ["get_provider", "AVAILABLE", "LLMProvider", "ProviderError"]
