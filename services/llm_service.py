"""Create the Groq chat model used by the application."""

from langchain_groq import ChatGroq

from config import get_settings


def get_chat_model() -> ChatGroq:
    """Create the configured Groq chat model."""

    settings = get_settings()
    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key.get_secret_value(),
        temperature=0,
    )
