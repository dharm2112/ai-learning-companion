"""LCEL chain for generating validated topic explanations."""

from schemas import TopicExplanation
from services.llm_service import get_chat_model
from prompts.explanation_prompt import EXPLANATION_PROMPT


SUPPORTED_LEVELS = ("Beginner", "Intermediate", "Industry Level")


def get_explanation_chain():
    """Return the prompt-to-structured-output LCEL chain."""

    structured_llm = get_chat_model().with_structured_output(TopicExplanation)
    return EXPLANATION_PROMPT | structured_llm


def generate_explanation(topic: str, learning_level: str) -> TopicExplanation:
    """Generate one validated explanation for a topic and learning level."""

    topic = topic.strip()
    if not topic:
        raise ValueError("Topic cannot be empty.")
    if learning_level not in SUPPORTED_LEVELS:
        raise ValueError(
            f"Learning level must be one of: {', '.join(SUPPORTED_LEVELS)}."
        )

    try:
        result = get_explanation_chain().invoke(
            {"topic": topic, "learning_level": learning_level}
        )
    except Exception as error:
        raise RuntimeError(f"Could not generate explanation: {error}") from error

    if not isinstance(result, TopicExplanation):
        raise TypeError("The explanation chain returned an invalid result.")
    return result
