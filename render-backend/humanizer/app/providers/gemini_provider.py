"""
Google Gemini ka API format alag hai, is liye separate class.
Free key: https://aistudio.google.com/apikey
"""
import httpx

from app.config import settings
from app.providers.base import LLMProvider, ProviderError

BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self):
        if not settings.gemini_api_key:
            raise ProviderError("GEMINI_API_KEY .env mein set nahi hai.")
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model

    async def complete(self, system: str, user: str, temperature: float = 0.9) -> str:
        url = f"{BASE}/{self.model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": temperature},
        }
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                r = await client.post(
                    url, params={"key": self.api_key}, json=payload
                )
        except httpx.HTTPError as e:
            raise ProviderError(f"gemini tak pohanch nahi saka: {e}") from e

        if r.status_code >= 400:
            raise ProviderError(f"gemini error {r.status_code}: {r.text[:400]}")

        data = r.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts).strip()
        except (KeyError, IndexError) as e:
            raise ProviderError(f"gemini ka jawab samajh nahi aaya: {data}") from e
