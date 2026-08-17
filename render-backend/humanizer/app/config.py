"""
Saari settings ek jagah. .env file se automatically parh leta hai.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "groq"

    # free providers
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # paid (optional)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # app limits
    max_input_chars: int = 12000
    chunk_size: int = 2500
    request_timeout: int = 90


settings = Settings()
