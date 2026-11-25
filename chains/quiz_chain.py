"""LCEL chain for generating validated quizzes.

Provides two public functions:
- generate_quiz()         — original, unchanged, topic + level only
- generate_adaptive_quiz() — personalised, uses weak/mastered concept context
"""

from schemas import Quiz
from services.llm_service import get_chat_model
from prompts.quiz_prompt import QUIZ_PROMPT
from prompts.adaptive_quiz_prompt import ADAPTIVE_QUIZ_PROMPT
from chains.explanation_chain import SUPPORTED_LEVELS


def get_quiz_chain():
    """Return the prompt-to-structured-output quiz chain."""

    # json_schema is supported by the installed ChatGroq version for Quiz.
    structured_llm = get_chat_model().with_structured_output(
        Quiz, method="json_schema"
    )
    return QUIZ_PROMPT | structured_llm


def get_adaptive_quiz_chain():
    """Return the adaptive quiz chain using the personalised prompt."""
    structured_llm = get_chat_model().with_structured_output(
        Quiz, method="json_schema"
    )
    return ADAPTIVE_QUIZ_PROMPT | structured_llm


def generate_quiz(
    topic: str, learning_level: str, question_count: int = 6
) -> Quiz:
    """Generate a quiz with exactly the requested number of questions."""

    topic = topic.strip()
    if not topic:
        raise ValueError("Topic cannot be empty.")
    if learning_level not in SUPPORTED_LEVELS:
        raise ValueError(
            f"Learning level must be one of: {', '.join(SUPPORTED_LEVELS)}."
        )
    if not 1 <= question_count <= 20:
        raise ValueError("Question count must be between 1 and 20.")

    mcq_count = max(1, question_count // 2)
    remaining = question_count - mcq_count
    true_false_count = (remaining + 1) // 2
    short_answer_count = remaining - true_false_count
    distribution = (
        f"{mcq_count} MCQ, {true_false_count} True/False, "
        f"{short_answer_count} Short Answer"
    )

    try:
        result = get_quiz_chain().invoke(
            {
                "topic": topic,
                "learning_level": learning_level,
                "question_count": question_count,
                "distribution": distribution,
            }
        )
    except Exception as error:
        raise RuntimeError(f"Could not generate quiz: {error}") from error

    if not isinstance(result, Quiz):
        raise TypeError("The quiz chain returned an invalid result.")
    if len(result.questions) != question_count:
        raise ValueError(
            f"The quiz returned {len(result.questions)} questions; "
            f"{question_count} were requested."
        )
    return result


def generate_adaptive_quiz(
    topic: str,
    learning_level: str,
    question_count: int = 6,
    weak_concepts: str = "none identified yet",
    mastered_concepts: str = "none yet",
    incorrect_history: str = "No previous incorrect answers recorded.",
    has_history: bool = False,
) -> Quiz:
    """Generate a personalised quiz based on the learner's concept history.

    Parameters
    ----------
    topic, learning_level, question_count:
        Same as generate_quiz().
    weak_concepts:
        Comma-separated string of weak concept names.
    mastered_concepts:
        Comma-separated string of mastered concept names.
    incorrect_history:
        Formatted summary of previously incorrect questions.
    has_history:
        True if the learner has any previous quiz history for this topic.
    """
    topic = topic.strip()
    if not topic:
        raise ValueError("Topic cannot be empty.")
    if learning_level not in SUPPORTED_LEVELS:
        raise ValueError(
            f"Learning level must be one of: {', '.join(SUPPORTED_LEVELS)}."
        )
    if not 1 <= question_count <= 20:
        raise ValueError("Question count must be between 1 and 20.")

    try:
        result = get_adaptive_quiz_chain().invoke(
            {
                "topic": topic,
                "learning_level": learning_level,
                "question_count": question_count,
                "weak_concepts": weak_concepts,
                "mastered_concepts": mastered_concepts,
                "incorrect_history": incorrect_history,
                "has_history": has_history,
            }
        )
    except Exception as error:
        raise RuntimeError(f"Could not generate adaptive quiz: {error}") from error

    if not isinstance(result, Quiz):
        raise TypeError("The adaptive quiz chain returned an invalid result.")
    if len(result.questions) != question_count:
        raise ValueError(
            f"The adaptive quiz returned {len(result.questions)} questions; "
            f"{question_count} were requested."
        )
    return result

