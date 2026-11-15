"""Unit tests for the Phase 3 explanation chain."""

from unittest.mock import Mock, patch

import pytest

from chains.explanation_chain import (
    SUPPORTED_LEVELS,
    generate_explanation,
)
from prompts.explanation_prompt import EXPLANATION_PROMPT
from schemas import TopicExplanation


def sample_explanation() -> TopicExplanation:
    return TopicExplanation(
        topic="Python",
        learning_level="Beginner",
        introduction="Python is a programming language.",
        definition="Python is a high-level language.",
        why_it_is_important="It is widely used.",
        how_it_works="An interpreter runs Python code.",
        key_concepts=["variables"],
        practical_examples=["A calculator"],
        advantages=["Readable"],
        disadvantages=["Can be slower"],
        real_world_applications=["Web applications"],
        common_mistakes=["Bad indentation"],
        summary="Python is versatile.",
    )


def test_prompt_accepts_a_valid_topic() -> None:
    messages = EXPLANATION_PROMPT.format_messages(
        topic="Python", learning_level="Beginner"
    )
    assert "Python" in messages[-1].content


@pytest.mark.parametrize("level", SUPPORTED_LEVELS)
def test_prompt_formats_for_each_learning_level(level: str) -> None:
    messages = EXPLANATION_PROMPT.format_messages(topic="LangChain", learning_level=level)
    assert level in messages[-1].content
    assert "LangChain" in messages[-1].content


def test_empty_topic_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        generate_explanation("   ", "Beginner")


def test_invalid_learning_level_is_rejected() -> None:
    with pytest.raises(ValueError, match="Learning level"):
        generate_explanation("Python", "Advanced")


def test_chain_returns_topic_explanation() -> None:
    explanation_chain = Mock()
    explanation_chain.invoke.return_value = sample_explanation()

    with patch("chains.explanation_chain.get_explanation_chain") as get_chain:
        get_chain.return_value = explanation_chain
        result = generate_explanation("Python", "Beginner")

    assert isinstance(result, TopicExplanation)
    assert result.topic == "Python"


def test_api_errors_are_wrapped_with_a_clear_message() -> None:
    explanation_chain = Mock()
    explanation_chain.invoke.side_effect = ConnectionError("service unavailable")

    with patch("chains.explanation_chain.get_explanation_chain") as get_chain:
        get_chain.return_value = explanation_chain
        with pytest.raises(RuntimeError, match="Could not generate explanation"):
            generate_explanation("Python", "Beginner")
