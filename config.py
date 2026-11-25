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


# ---------------------------------------------------------------------------
# Storage configuration (new for Adaptive AI Learning System)
# ---------------------------------------------------------------------------


def get_db_path() -> str:
    """Return the SQLite database file path (default: ./data/learning.db)."""
    return os.getenv("DB_PATH", "./data/learning.db").strip()


def get_chroma_path() -> str:
    """Return the ChromaDB persistence directory (default: ./data/chroma)."""
    return os.getenv("CHROMA_PATH", "./data/chroma").strip()


def get_embedding_model() -> str:
    """Return the HuggingFace sentence-transformers model name."""
    return os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip()


def get_huggingface_token() -> str:
    """Return the HuggingFace Hub API token (may be empty for public models)."""
    return os.getenv("HUGGINGFACEHUB_API_TOKEN", "").strip()
