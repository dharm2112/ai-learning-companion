"""LCEL chain for generating validated quizzes."""

from schemas import Quiz
from services.llm_service import get_chat_model
from prompts.quiz_prompt import QUIZ_PROMPT
from chains.explanation_chain import SUPPORTED_LEVELS


def get_quiz_chain():
    """Return the prompt-to-structured-output quiz chain."""

    # json_schema is supported by the installed ChatGroq version for Quiz.
    structured_llm = get_chat_model().with_structured_output(
        Quiz, method="json_schema"
    )
    return QUIZ_PROMPT | structured_llm


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
