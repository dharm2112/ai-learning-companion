"""Unit tests for further-learning recommendations."""

from unittest.mock import Mock, patch

import pytest

from chains.learning_chain import (
    generate_custom_learning,
    generate_learning_recommendations,
)
from schemas import (
    FurtherLearning,
    QuizEvaluation,
    QuestionResult,
    TopicExplanation,
)


def sample_evaluation() -> QuizEvaluation:
    return QuizEvaluation(
        total_questions=2,
        correct_answers=1,
        incorrect_answers=1,
        score_percentage=50,
        question_results=[
            QuestionResult(
                question_id=1,
                user_answer="wrong",
                correct_answer="right",
                is_correct=False,
                explanation="Review this concept.",
                concept_tested="RunnableParallel",
            ),
            QuestionResult(
                question_id=2,
                user_answer="right",
                correct_answer="right",
                is_correct=True,
                explanation="Correct.",
                concept_tested="RunnableSequence",
            ),
        ],
        weak_concepts=["RunnableParallel"],
        improvement_suggestions=["Review parallel execution."],
    )


def sample_recommendations() -> FurtherLearning:
    return FurtherLearning(
        recommended_topics=["RunnableLambda"],
        advanced_topics=["RunnableBranch"],
        suggested_learning_order=["RunnableLambda", "RunnableBranch"],
        custom_learning_suggestions=["Build a routing chain."],
    )


def sample_explanation() -> TopicExplanation:
    return TopicExplanation(
        topic="RunnableBranch with practical examples",
        learning_level="Intermediate",
        introduction="RunnableBranch chooses a path.",
        definition="It routes input to a matching runnable.",
        why_it_is_important="It supports conditional workflows.",
        how_it_works="Conditions are checked in order.",
        key_concepts=["conditions"],
        practical_examples=["Route by topic"],
        advantages=["Flexible"],
        disadvantages=["Can be harder to debug"],
        real_world_applications=["Support routing"],
        common_mistakes=["Overlapping conditions"],
        summary="RunnableBranch supports conditional routing.",
    )


def test_valid_recommendation_generation_and_output_type() -> None:
    chain = Mock()
    chain.invoke.return_value = sample_recommendations()

    with patch("chains.learning_chain.get_learning_chain") as get_chain:
        get_chain.return_value = chain
        result = generate_learning_recommendations(
            "Runnables in LangChain", "Intermediate", sample_evaluation()
        )

    assert isinstance(result, FurtherLearning)


def test_quiz_evaluation_data_reaches_chain() -> None:
    chain = Mock()
    chain.invoke.return_value = sample_recommendations()

    with patch("chains.learning_chain.get_learning_chain") as get_chain:
        get_chain.return_value = chain
        generate_learning_recommendations(
            "Runnables", "Intermediate", sample_evaluation()
        )

    data = chain.invoke.call_args.args[0]
    assert data["score"] == 50
    assert data["weak_concepts"] == "RunnableParallel"
    assert data["improvement_suggestions"] == "Review parallel execution."


def test_empty_topic_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        generate_learning_recommendations(" ", "Beginner", sample_evaluation())


def test_invalid_learning_level_is_rejected() -> None:
    with pytest.raises(ValueError, match="Learning level"):
        generate_learning_recommendations("Python", "Advanced", sample_evaluation())


def test_recommendation_api_error_is_handled() -> None:
    chain = Mock()
    chain.invoke.side_effect = ConnectionError("service unavailable")

    with patch("chains.learning_chain.get_learning_chain") as get_chain:
        get_chain.return_value = chain
        with pytest.raises(
            RuntimeError, match="Could not generate learning recommendations"
        ):
            generate_learning_recommendations("Python", "Beginner", sample_evaluation())


def test_custom_topic_uses_existing_explanation_chain() -> None:
    explanation_chain = Mock()
    explanation_chain.invoke.return_value = sample_explanation()

    with patch(
        "chains.learning_chain.get_explanation_chain"
    ) as get_chain:
        get_chain.return_value = explanation_chain
        result = generate_custom_learning(
            "RunnableBranch with practical examples", "Intermediate"
        )

    assert isinstance(result, TopicExplanation)
    explanation_chain.invoke.assert_called_once_with(
        {
            "topic": "RunnableBranch with practical examples",
            "learning_level": "Intermediate",
        }
    )


def test_custom_learning_returns_topic_explanation() -> None:
    explanation_chain = Mock()
    explanation_chain.invoke.return_value = sample_explanation()

    with patch("chains.learning_chain.get_explanation_chain") as get_chain:
        get_chain.return_value = explanation_chain
        result = generate_custom_learning("RunnableBranch", "Intermediate")

    assert isinstance(result, TopicExplanation)


def test_custom_topic_error_is_handled() -> None:
    with pytest.raises(ValueError, match="Custom topic cannot be empty"):
        generate_custom_learning(" ", "Intermediate")
