"""Generate further-learning recommendations and custom explanations."""

from chains.explanation_chain import SUPPORTED_LEVELS, get_explanation_chain
from prompts.further_learning_prompt import FURTHER_LEARNING_PROMPT
from schemas import FurtherLearning, QuizEvaluation, TopicExplanation
from services.llm_service import get_chat_model


def get_learning_chain():
    """Return the recommendation prompt-to-structured-output chain."""

    structured_llm = get_chat_model().with_structured_output(FurtherLearning)
    return FURTHER_LEARNING_PROMPT | structured_llm


def generate_learning_recommendations(
    topic: str,
    learning_level: str,
    quiz_evaluation: QuizEvaluation,
) -> FurtherLearning:
    """Generate recommendations from a quiz result."""

    topic = topic.strip()
    if not topic:
        raise ValueError("Topic cannot be empty.")
    if learning_level not in SUPPORTED_LEVELS:
        raise ValueError(
            f"Learning level must be one of: {', '.join(SUPPORTED_LEVELS)}."
        )

    try:
        result = get_learning_chain().invoke(
            {
                "topic": topic,
                "learning_level": learning_level,
                "score": quiz_evaluation.score_percentage,
                "weak_concepts": ", ".join(quiz_evaluation.weak_concepts),
                "improvement_suggestions": ", ".join(
                    quiz_evaluation.improvement_suggestions
                ),
            }
        )
    except Exception as error:
        raise RuntimeError(
            f"Could not generate learning recommendations: {error}"
        ) from error

    if not isinstance(result, FurtherLearning):
        raise TypeError("The learning chain returned an invalid result.")
    return result


def generate_custom_learning(
    custom_topic: str, learning_level: str
) -> TopicExplanation:
    """Explain a learner-selected topic using the existing explanation chain."""

    custom_topic = custom_topic.strip()
    if not custom_topic:
        raise ValueError("Custom topic cannot be empty.")
    if learning_level not in SUPPORTED_LEVELS:
        raise ValueError(
            f"Learning level must be one of: {', '.join(SUPPORTED_LEVELS)}."
        )

    try:
        result = get_explanation_chain().invoke(
            {"topic": custom_topic, "learning_level": learning_level}
        )
    except Exception as error:
        raise RuntimeError(
            f"Could not generate custom learning explanation: {error}"
        ) from error

    if not isinstance(result, TopicExplanation):
        raise TypeError("The explanation chain returned an invalid result.")
    return result
