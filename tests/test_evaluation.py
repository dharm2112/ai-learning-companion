"""Unit tests for quiz evaluation."""

from unittest.mock import Mock, patch

import pytest

from chains.evaluation_chain import evaluate_quiz
from schemas import (
    Quiz,
    QuizEvaluation,
    QuizQuestion,
    QuestionType,
    ShortAnswerEvaluation,
)


def sample_quiz() -> Quiz:
    questions = [
        QuizQuestion(
            question_id=1,
            question_text="What is LCEL?",
            question_type=QuestionType.MCQ,
            options=["A", "B", "C", "D"],
            correct_answer="A",
            explanation="A is correct.",
            concept_tested="LCEL",
            difficulty="Beginner",
        ),
        QuizQuestion(
            question_id=2,
            question_text="Runnables can be composed.",
            question_type=QuestionType.TRUE_FALSE,
            options=["True", "False"],
            correct_answer="True",
            explanation="Runnables are composable.",
            concept_tested="Composition",
            difficulty="Beginner",
        ),
        QuizQuestion(
            question_id=3,
            question_text="What does invoke do?",
            question_type=QuestionType.SHORT_ANSWER,
            correct_answer="It executes a runnable with an input.",
            explanation="invoke executes a runnable.",
            concept_tested="invoke",
            difficulty="Intermediate",
        ),
    ]
    return Quiz(topic="LangChain", learning_level="Intermediate", questions=questions)


def test_all_mcq_answers_correct() -> None:
    quiz = sample_quiz().model_copy(
        update={"questions": [sample_quiz().questions[0]]}
    )
    result = evaluate_quiz(quiz, {1: " a "})
    assert result.correct_answers == 1


def test_some_mcq_answers_incorrect() -> None:
    quiz = sample_quiz().model_copy(
        update={
            "questions": [
                sample_quiz().questions[0],
                sample_quiz().questions[0].model_copy(update={"question_id": 4}),
            ]
        }
    )
    result = evaluate_quiz(quiz, {1: "A", 4: "B"})
    assert result.correct_answers == 1
    assert result.incorrect_answers == 1


def test_true_false_evaluation() -> None:
    quiz = sample_quiz().model_copy(update={"questions": [sample_quiz().questions[1]]})
    result = evaluate_quiz(quiz, {2: " TRUE "})
    assert result.question_results[0].is_correct is True


def test_missing_answers_are_incorrect() -> None:
    quiz = sample_quiz().model_copy(update={"questions": [sample_quiz().questions[0]]})
    result = evaluate_quiz(quiz, {})
    assert result.correct_answers == 0
    assert result.incorrect_answers == 1


def test_short_answer_uses_mocked_groq_result() -> None:
    short_result = ShortAnswerEvaluation(
        is_correct=True,
        explanation="The answer has the essential idea.",
        concept_tested="invoke",
    )
    short_chain = Mock()
    short_chain.invoke.return_value = short_result
    quiz = sample_quiz().model_copy(update={"questions": [sample_quiz().questions[2]]})

    with patch("chains.evaluation_chain.get_short_answer_chain") as get_chain:
        get_chain.return_value = short_chain
        result = evaluate_quiz(quiz, {3: "It runs the runnable with input."})

    assert result.question_results[0].is_correct is True
    short_chain.invoke.assert_called_once()


def test_score_calculation_and_weak_concepts() -> None:
    quiz = sample_quiz().model_copy(
        update={"questions": [sample_quiz().questions[0], sample_quiz().questions[1]]}
    )
    result = evaluate_quiz(quiz, {1: "B", 2: "False"})
    assert result.score_percentage == 0
    assert result.weak_concepts == ["LCEL", "Composition"]


def test_unknown_question_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown question IDs"):
        evaluate_quiz(sample_quiz(), {99: "answer"})


def test_empty_user_answers_are_valid_but_incorrect() -> None:
    result = evaluate_quiz(sample_quiz(), {})
    assert isinstance(result, QuizEvaluation)
    assert result.correct_answers == 0


def test_api_error_is_handled() -> None:
    short_chain = Mock()
    short_chain.invoke.side_effect = ConnectionError("service unavailable")
    quiz = sample_quiz().model_copy(update={"questions": [sample_quiz().questions[2]]})

    with patch("chains.evaluation_chain.get_short_answer_chain") as get_chain:
        get_chain.return_value = short_chain
        with pytest.raises(RuntimeError, match="Could not evaluate short-answer"):
            evaluate_quiz(quiz, {3: "answer"})
