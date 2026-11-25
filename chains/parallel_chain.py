"""Generate an explanation and quiz concurrently."""

from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel

from chains.explanation_chain import (
    SUPPORTED_LEVELS,
    get_contextual_explanation_chain,
    get_explanation_chain,
)
from chains.quiz_chain import get_quiz_chain
from schemas import Quiz, TopicExplanation


def get_parallel_chain(memory_context: str = "") -> Runnable:
    """Return parallel explanation and quiz branches."""

    if memory_context:
        explanation_chain = get_contextual_explanation_chain()
        explanation_input = RunnableLambda(
            lambda data: {
                "topic": data["topic"],
                "learning_level": data["learning_level"],
                "memory_context": data["memory_context"],
            }
        )
    else:
        explanation_chain = get_explanation_chain()
        explanation_input = RunnableLambda(
            lambda data: {
                "topic": data["topic"],
                "learning_level": data["learning_level"],
            }
        )

    quiz_input = RunnableLambda(
        lambda data: {
            "topic": data["topic"],
            "learning_level": data["learning_level"],
            "question_count": data["question_count"],
            "distribution": data["distribution"],
        }
    )

    return RunnableParallel(
        explanation=explanation_input | explanation_chain,
        quiz=quiz_input | get_quiz_chain(),
    )


def generate_learning_material(
    topic: str,
    learning_level: str,
    question_count: int = 6,
    memory_context: str = "",
) -> dict[str, TopicExplanation | Quiz]:
    """Generate an explanation and quiz concurrently."""

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
        inputs = {
            "topic": topic,
            "learning_level": learning_level,
            "question_count": question_count,
            "distribution": distribution,
        }
        if memory_context:
            inputs["memory_context"] = memory_context
        result = get_parallel_chain(memory_context).invoke(inputs)
    except Exception as error:
        raise RuntimeError(f"Could not generate learning material: {error}") from error

    explanation = result.get("explanation")
    quiz = result.get("quiz")
    if not isinstance(explanation, TopicExplanation):
        raise TypeError("The parallel chain returned an invalid explanation.")
    if not isinstance(quiz, Quiz):
        raise TypeError("The parallel chain returned an invalid quiz.")
    if len(quiz.questions) != question_count:
        raise ValueError(
            f"The quiz returned {len(quiz.questions)} questions; "
            f"{question_count} were requested."
        )

    return {"explanation": explanation, "quiz": quiz}
