"""Manual experiment for personalized and custom learning."""

import sys

from chains.learning_chain import (
    generate_custom_learning,
    generate_learning_recommendations,
)
from schemas import QuizEvaluation, FurtherLearning, TopicExplanation


sys.stdout.reconfigure(encoding="utf-8")

evaluation = QuizEvaluation(
    total_questions=20,
    correct_answers=13,
    incorrect_answers=7,
    score_percentage=65,
    question_results=[
        {
            "question_id": question_id,
            "user_answer": "answer",
            "correct_answer": "answer",
            "is_correct": question_id <= 13,
            "explanation": "Review parallel execution."
            if question_id > 13
            else "Correct.",
            "concept_tested": (
                "RunnableParallel" if question_id % 2 else "RunnableBranch"
            ),
        }
        for question_id in range(1, 21)
    ],
    weak_concepts=["RunnableParallel", "RunnableBranch"],
    improvement_suggestions=["Practice concurrent and conditional workflows."],
)

recommendations = generate_learning_recommendations(
    "Runnables in LangChain", "Intermediate", evaluation
)
if not isinstance(recommendations, FurtherLearning):
    raise TypeError("The recommendation result is not FurtherLearning.")

print("Recommended topics:", recommendations.recommended_topics)
print("Advanced topics:", recommendations.advanced_topics)
print("Suggested learning order:", recommendations.suggested_learning_order)
print(
    "Custom learning suggestions:",
    recommendations.custom_learning_suggestions,
)

custom_explanation = generate_custom_learning(
    "RunnableBranch with practical examples", "Intermediate"
)
print("\nCustom result is TopicExplanation:", isinstance(custom_explanation, TopicExplanation))
print("Custom topic:", custom_explanation.topic)
print("Custom summary:", custom_explanation.summary)
