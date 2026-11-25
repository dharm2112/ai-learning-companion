"""Unit tests for the Phase 5 parallel chain."""

from unittest.mock import patch

import pytest
from langchain_core.runnables import RunnableLambda

from chains.parallel_chain import generate_learning_material
from schemas import Quiz, QuizQuestion, QuestionType, TopicExplanation


def sample_explanation() -> TopicExplanation:
    return TopicExplanation(
        topic="Runnables",
        learning_level="Intermediate",
        introduction="Runnables are callable LangChain components.",
        definition="A Runnable accepts input and produces output.",
        why_it_is_important="They make chains composable.",
        how_it_works="Each runnable receives the previous result.",
        key_concepts=["invoke"],
        practical_examples=["Prompt followed by an LLM"],
        advantages=["Composable"],
        disadvantages=["Requires compatible inputs"],
        real_world_applications=["AI workflows"],
        common_mistakes=["Using the wrong input keys"],
        summary="Runnables are building blocks for LangChain workflows.",
    )


def sample_quiz(question_count: int = 6) -> Quiz:
    questions = [
        QuizQuestion(
            question_id=number,
            question_text=f"Question {number}?",
            question_type=QuestionType.MCQ,
            options=["A", "B", "C", "D"],
            correct_answer="A",
            explanation="A is correct.",
            concept_tested="Runnables",
            difficulty="Intermediate",
        )
        for number in range(1, question_count + 1)
    ]
    return Quiz(
        topic="Runnables",
        learning_level="Intermediate",
        questions=questions,
    )


def test_parallel_chain_returns_both_outputs_and_passes_inputs() -> None:
    explanation_inputs = []
    quiz_inputs = []

    explanation_chain = RunnableLambda(
        lambda data: explanation_inputs.append(data) or sample_explanation()
    )
    quiz_chain = RunnableLambda(
        lambda data: quiz_inputs.append(data) or sample_quiz()
    )

    with patch("chains.parallel_chain.get_explanation_chain") as get_explanation:
        with patch("chains.parallel_chain.get_quiz_chain") as get_quiz:
            get_explanation.return_value = explanation_chain
            get_quiz.return_value = quiz_chain
            result = generate_learning_material("Runnables", "Intermediate", 6)

    assert isinstance(result["explanation"], TopicExplanation)
    assert isinstance(result["quiz"], Quiz)
    assert explanation_inputs == [
        {"topic": "Runnables", "learning_level": "Intermediate"}
    ]
    assert quiz_inputs[0]["topic"] == "Runnables"
    assert quiz_inputs[0]["learning_level"] == "Intermediate"
    assert quiz_inputs[0]["question_count"] == 6
    assert quiz_inputs[0]["distribution"] == "3 MCQ, 2 True/False, 1 Short Answer"


def test_memory_context_uses_contextual_explanation_chain() -> None:
    explanation_inputs = []
    contextual_chain = RunnableLambda(
        lambda data: explanation_inputs.append(data) or sample_explanation()
    )
    quiz_chain = RunnableLambda(lambda data: sample_quiz())

    with patch(
        "chains.parallel_chain.get_contextual_explanation_chain"
    ) as get_contextual:
        with patch("chains.parallel_chain.get_quiz_chain") as get_quiz:
            get_contextual.return_value = contextual_chain
            get_quiz.return_value = quiz_chain
            result = generate_learning_material(
                "Runnables",
                "Intermediate",
                6,
                "Previously studied LCEL.",
            )

    assert isinstance(result["explanation"], TopicExplanation)
    assert explanation_inputs == [
        {
            "topic": "Runnables",
            "learning_level": "Intermediate",
            "memory_context": "Previously studied LCEL.",
        }
    ]


def test_invalid_topic_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        generate_learning_material(" ", "Beginner")


def test_invalid_learning_level_is_rejected() -> None:
    with pytest.raises(ValueError, match="Learning level"):
        generate_learning_material("Python", "Advanced")


@pytest.mark.parametrize("count", [0, 21])
def test_invalid_question_count_is_rejected(count: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 20"):
        generate_learning_material("Python", "Beginner", count)


def test_error_from_a_parallel_branch_is_handled() -> None:
    failing_chain = RunnableLambda(
        lambda data: (_ for _ in ()).throw(ConnectionError("service unavailable"))
    )
    working_chain = RunnableLambda(lambda data: sample_quiz())

    with patch("chains.parallel_chain.get_explanation_chain") as get_explanation:
        with patch("chains.parallel_chain.get_quiz_chain") as get_quiz:
            get_explanation.return_value = failing_chain
            get_quiz.return_value = working_chain
            with pytest.raises(RuntimeError, match="Could not generate learning material"):
                generate_learning_material("Python", "Beginner")
