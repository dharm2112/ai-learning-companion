"""Evaluate quiz answers with Python and structured short-answer grading."""

from typing import Mapping

from prompts.evaluation_prompt import EVALUATION_PROMPT
from schemas import (
    Quiz,
    QuizEvaluation,
    QuestionResult,
    QuestionType,
    ShortAnswerEvaluation,
)
from services.llm_service import get_chat_model


def get_short_answer_chain():
    """Return the prompt-to-structured-output chain for short answers."""

    structured_llm = get_chat_model().with_structured_output(ShortAnswerEvaluation)
    return EVALUATION_PROMPT | structured_llm


def normalize_answer(answer: str) -> str:
    """Make submitted text safe to compare without changing its meaning."""

    return " ".join(answer.strip().lower().split())


def evaluate_quiz(
    quiz: Quiz, user_answers: Mapping[int, str]
) -> QuizEvaluation:
    """Evaluate every answer and return a validated evaluation report."""

    question_ids = {question.question_id for question in quiz.questions}
    unknown_ids = set(user_answers) - question_ids
    if unknown_ids:
        raise ValueError(f"Unknown question IDs: {sorted(unknown_ids)}.")

    question_results: list[QuestionResult] = []

    for question in quiz.questions:
        user_answer = str(user_answers.get(question.question_id, ""))
        normalized_user = normalize_answer(user_answer)
        normalized_correct = normalize_answer(question.correct_answer)

        if question.question_type is QuestionType.MCQ:
            is_correct = normalized_user == normalized_correct
            explanation = question.explanation
            concept_tested = question.concept_tested
        elif question.question_type is QuestionType.TRUE_FALSE:
            is_correct = (
                normalized_user in {"true", "false"}
                and normalized_user == normalized_correct
            )
            explanation = question.explanation
            concept_tested = question.concept_tested
        elif not normalized_user:
            is_correct = False
            explanation = "No answer was submitted."
            concept_tested = question.concept_tested
        else:
            try:
                short_result = get_short_answer_chain().invoke(
                    {
                        "question": question.question_text,
                        "expected_answer": question.correct_answer,
                        "user_answer": user_answer,
                        "concept_tested": question.concept_tested,
                    }
                )
            except Exception as error:
                raise RuntimeError(
                    f"Could not evaluate short-answer question "
                    f"{question.question_id}: {error}"
                ) from error

            if not isinstance(short_result, ShortAnswerEvaluation):
                raise TypeError("The short-answer chain returned an invalid result.")
            is_correct = short_result.is_correct
            explanation = short_result.explanation
            concept_tested = short_result.concept_tested

        question_results.append(
            QuestionResult(
                question_id=question.question_id,
                user_answer=user_answer,
                correct_answer=question.correct_answer,
                is_correct=is_correct,
                explanation=explanation,
                concept_tested=concept_tested,
            )
        )

    total_questions = len(question_results)
    correct_answers = sum(result.is_correct for result in question_results)
    incorrect_answers = total_questions - correct_answers
    weak_concepts = list(
        dict.fromkeys(
            result.concept_tested
            for result in question_results
            if not result.is_correct
        )
    )
    suggestions = [
        f"Review the concept: {concept}." for concept in weak_concepts
    ]

    return QuizEvaluation(
        total_questions=total_questions,
        correct_answers=correct_answers,
        incorrect_answers=incorrect_answers,
        score_percentage=(correct_answers / total_questions) * 100,
        question_results=question_results,
        weak_concepts=weak_concepts,
        improvement_suggestions=suggestions,
    )
