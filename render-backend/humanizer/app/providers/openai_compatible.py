"""
Groq, OpenRouter, OpenAI aur Ollama — chaaron ka API "OpenAI-compatible"
chat/completions format use karta hai, is liye ek hi class kaafi hai.
"""
import httpx

from app.config import settings
from app.providers.base import LLMProvider, ProviderError


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, name: str, base_url: str, api_key: str, model: str):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def complete(self, system: str, user: str, temperature: float = 0.9) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions", headers=headers, json=payload
                )
        except httpx.HTTPError as e:
            raise ProviderError(f"{self.name} tak pohanch nahi saka: {e}") from e

        if r.status_code >= 400:
            raise ProviderError(f"{self.name} error {r.status_code}: {r.text[:400]}")

        data = r.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as e:
            raise ProviderError(f"{self.name} ka jawab samajh nahi aaya: {data}") from e


def groq() -> OpenAICompatibleProvider:
    if not settings.groq_api_key:
        raise ProviderError("GROQ_API_KEY .env mein set nahi hai.")
    return OpenAICompatibleProvider(
        "groq", "https://api.groq.com/openai/v1", settings.groq_api_key, settings.groq_model
    )


def openrouter() -> OpenAICompatibleProvider:
    if not settings.openrouter_api_key:
        raise ProviderError("OPENROUTER_API_KEY .env mein set nahi hai.")
    return OpenAICompatibleProvider(
        "openrouter",
        "https://openrouter.ai/api/v1",
        settings.openrouter_api_key,
        settings.openrouter_model,
    )


def openai() -> OpenAICompatibleProvider:
    if not settings.openai_api_key:
        raise ProviderError("OPENAI_API_KEY .env mein set nahi hai.")
    return OpenAICompatibleProvider(
        "openai", "https://api.openai.com/v1", settings.openai_api_key, settings.openai_model
    )


def ollama() -> OpenAICompatibleProvider:
    # Local — koi API key nahi chahiye.
    return OpenAICompatibleProvider(
        "ollama", f"{settings.ollama_base_url}/v1", "", settings.ollama_model
    )
