"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic import BaseModel, SecretStr

load_dotenv()


class Settings(BaseModel):
    """Validated settings required to connect to Groq."""

    groq_api_key: SecretStr
    groq_model: str = "openai/gpt-oss-20b"


def get_settings() -> Settings:
    """Load settings from environment variables."""

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()

    if not api_key or api_key == "your_groq_api_key_here":
        raise ValueError(
            "GROQ_API_KEY is not configured. Copy .env.example to .env and add "
            "your Groq API key, or set GROQ_API_KEY in the environment."
        )
    if not model:
        raise ValueError("GROQ_MODEL must not be empty.")

    return Settings(groq_api_key=api_key, groq_model=model)
