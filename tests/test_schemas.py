"""Unit tests for Phase 2 Pydantic schemas."""

import pytest
from pydantic import ValidationError

from schemas import FurtherLearning, Quiz, QuizEvaluation, QuizQuestion, QuestionType, TopicExplanation


def explanation_data() -> dict:
    return {
        "topic": "Python",
        "learning_level": "Beginner",
        "introduction": "A programming language.",
        "definition": "Python is a high-level language.",
        "why_it_is_important": "It is widely used.",
        "how_it_works": "The interpreter executes Python code.",
        "key_concepts": ["variables"],
        "practical_examples": ["A calculator"],
        "advantages": ["Readable"],
        "disadvantages": ["Slower than compiled languages in some cases"],
        "real_world_applications": ["Web development"],
        "common_mistakes": ["Incorrect indentation"],
        "summary": "Python is versatile.",
    }


def question_data(question_type: QuestionType, **overrides: object) -> dict:
    data = {
        "question_id": 1,
        "question_text": "What is Python?",
        "question_type": question_type,
        "options": [],
        "correct_answer": "A programming language",
        "explanation": "Python is a programming language.",
        "concept_tested": "Definitions",
        "difficulty": "Beginner",
    }
    data.update(overrides)
    return data


def test_valid_topic_explanation() -> None:
    assert TopicExplanation.model_validate(explanation_data()).topic == "Python"


def test_valid_mcq_question() -> None:
    question = QuizQuestion.model_validate(
        question_data(QuestionType.MCQ, options=["A", "B"], correct_answer="A")
    )
    assert question.question_type is QuestionType.MCQ


def test_valid_true_false_question() -> None:
    question = QuizQuestion.model_validate(
        question_data(
            QuestionType.TRUE_FALSE,
            options=["True", "False"],
            correct_answer="True",
        )
    )
    assert question.options == ["True", "False"]


def test_valid_short_answer_question() -> None:
    question = QuizQuestion.model_validate(question_data(QuestionType.SHORT_ANSWER))
    assert question.options == []


def test_invalid_mcq_without_options() -> None:
    with pytest.raises(ValidationError, match="at least two options"):
        QuizQuestion.model_validate(question_data(QuestionType.MCQ))


def test_invalid_question_without_correct_answer() -> None:
    with pytest.raises(ValidationError):
        QuizQuestion.model_validate(question_data(QuestionType.SHORT_ANSWER, correct_answer=""))


def test_duplicate_question_ids() -> None:
    first = question_data(QuestionType.SHORT_ANSWER)
    second = question_data(QuestionType.SHORT_ANSWER, question_id=1)
    with pytest.raises(ValidationError, match="unique"):
        Quiz.model_validate({"topic": "Python", "learning_level": "Beginner", "questions": [first, second]})


def test_empty_quiz() -> None:
    with pytest.raises(ValidationError):
        Quiz.model_validate({"topic": "Python", "learning_level": "Beginner", "questions": []})


def test_invalid_evaluation_score() -> None:
    with pytest.raises(ValidationError):
        QuizEvaluation.model_validate(
            {
                "total_questions": 1,
                "correct_answers": 1,
                "incorrect_answers": 0,
                "score_percentage": 50,
                "question_results": [
                    {
                        "question_id": 1,
                        "user_answer": "A",
                        "correct_answer": "A",
                        "is_correct": True,
                        "explanation": "Correct.",
                        "concept_tested": "Python",
                    }
                ],
            }
        )


def test_valid_further_learning() -> None:
    learning = FurtherLearning(recommended_topics=["Functions"])
    assert learning.recommended_topics == ["Functions"]
