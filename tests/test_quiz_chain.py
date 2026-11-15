"""Unit tests for the Phase 4 quiz chain."""

from unittest.mock import Mock, patch

import pytest

from chains.quiz_chain import generate_quiz
from schemas import Quiz, QuizQuestion, QuestionType


def sample_quiz(question_count: int = 6) -> Quiz:
    questions = []
    for question_id in range(1, question_count + 1):
        questions.append(
            QuizQuestion(
                question_id=question_id,
                question_text=f"Question {question_id}?",
                question_type=QuestionType.MCQ,
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation="A is correct.",
                concept_tested="Runnables",
                difficulty="Intermediate",
            )
        )
    return Quiz(
        topic="Runnables in LangChain",
        learning_level="Intermediate",
        questions=questions,
    )


def mocked_quiz_chain(quiz: Quiz) -> Mock:
    quiz_chain = Mock()
    quiz_chain.invoke.return_value = quiz
    return quiz_chain


def test_valid_topic_is_accepted() -> None:
    with patch("chains.quiz_chain.get_quiz_chain") as get_chain:
        get_chain.return_value = mocked_quiz_chain(sample_quiz())
        result = generate_quiz("Runnables", "Intermediate", 6)

    assert isinstance(result, Quiz)
    assert len(result.questions) == 6


def test_empty_topic_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        generate_quiz("   ", "Beginner")


def test_invalid_learning_level_is_rejected() -> None:
    with pytest.raises(ValueError, match="Learning level"):
        generate_quiz("Python", "Advanced")


@pytest.mark.parametrize("count", [0, 21])
def test_invalid_question_count_is_rejected(count: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 20"):
        generate_quiz("Python", "Beginner", count)


def test_incorrect_generated_question_count_is_handled() -> None:
    with patch("chains.quiz_chain.get_quiz_chain") as get_chain:
        get_chain.return_value = mocked_quiz_chain(sample_quiz(5))
        with pytest.raises(ValueError, match="returned 5 questions"):
            generate_quiz("Python", "Beginner", 6)


def test_api_errors_are_wrapped_with_a_clear_message() -> None:
    quiz_chain = Mock()
    quiz_chain.invoke.side_effect = ConnectionError("service unavailable")

    with patch("chains.quiz_chain.get_quiz_chain") as get_chain:
        get_chain.return_value = quiz_chain
        with pytest.raises(RuntimeError, match="Could not generate quiz"):
            generate_quiz("Python", "Beginner", 6)
