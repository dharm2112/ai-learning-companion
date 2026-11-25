"""LCEL chain for generating validated topic explanations.

Provides two public functions:
- generate_explanation()            — original, unchanged
- generate_contextual_explanation() — enhanced with learner memory context
"""

from schemas import TopicExplanation
from services.llm_service import get_chat_model
from prompts.explanation_prompt import EXPLANATION_PROMPT
from prompts.contextual_explanation_prompt import CONTEXTUAL_EXPLANATION_PROMPT


SUPPORTED_LEVELS = ("Beginner", "Intermediate", "Industry Level")


def get_explanation_chain():
    """Return the prompt-to-structured-output LCEL chain."""

    structured_llm = get_chat_model().with_structured_output(TopicExplanation)
    return EXPLANATION_PROMPT | structured_llm


def get_contextual_explanation_chain():
    """Return the memory-aware explanation chain."""
    structured_llm = get_chat_model().with_structured_output(TopicExplanation)
    return CONTEXTUAL_EXPLANATION_PROMPT | structured_llm


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


def generate_contextual_explanation(
    topic: str,
    learning_level: str,
    memory_context: str = "",
) -> TopicExplanation:
    """Generate an explanation enriched with the learner's previous knowledge.

    Parameters
    ----------
    topic:
        Topic to explain.
    learning_level:
        "Beginner" | "Intermediate" | "Industry Level"
    memory_context:
        Pre-formatted string of past topic summaries from ``learner_memory.build_memory_context()``.
        Pass an empty string to fall back to standard explanation behaviour.
    """
    topic = topic.strip()
    if not topic:
        raise ValueError("Topic cannot be empty.")
    if learning_level not in SUPPORTED_LEVELS:
        raise ValueError(
            f"Learning level must be one of: {', '.join(SUPPORTED_LEVELS)}."
        )

    try:
        result = get_contextual_explanation_chain().invoke(
            {
                "topic": topic,
                "learning_level": learning_level,
                "memory_context": memory_context or "",
            }
        )
    except Exception as error:
        raise RuntimeError(
            f"Could not generate contextual explanation: {error}"
        ) from error

    if not isinstance(result, TopicExplanation):
        raise TypeError("The contextual explanation chain returned an invalid result.")
    return result

