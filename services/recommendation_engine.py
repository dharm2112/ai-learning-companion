"""Rule-based Personalized Recommendation Engine.

Generates three categories of recommendations:
- revision  : Concepts the user should re-read (status=weak, ≥2 attempts)
- practice  : Concepts to drill with a targeted quiz
- next_topic: Topics to study next based on mastery and history

Rule logic is deterministic and explainable. After rules produce
structured recommendations, the LLM is used only to narrate them in
natural language (via recommendation_chain).
"""

from __future__ import annotations

from schemas.memory import LearnerProfile, Recommendation, RecommendationSet

# Thresholds
REVISION_MIN_ATTEMPTS = 2       # Only recommend revision if seen ≥ N times
PRACTICE_ACCURACY_THRESHOLD = 0.5  # Recommend practice when accuracy < 50%
MASTERY_SCORE_FOR_NEXT = 0.80   # Topic must have ≥80% mastery to suggest next


# ---------------------------------------------------------------------------
# Rule-based recommendation generation
# ---------------------------------------------------------------------------


def generate_recommendations(
    profile: LearnerProfile,
    current_topic: str,
    score_percentage: float,
) -> RecommendationSet:
    """Generate a full RecommendationSet from the learner's profile.

    Parameters
    ----------
    profile:
        Current LearnerProfile from ``get_learner_profile()``.
    current_topic:
        The topic just studied.
    score_percentage:
        Score (0–100) from the most recent quiz.

    Returns
    -------
    RecommendationSet with revision, practice, and next_topic lists.
    """
    revision = _revision_recommendations(profile)
    practice = _practice_recommendations(profile)
    next_topic = _next_topic_recommendations(profile, current_topic, score_percentage)

    return RecommendationSet(
        revision=revision,
        practice=practice,
        next_topic=next_topic,
    )


def _revision_recommendations(profile: LearnerProfile) -> list[Recommendation]:
    """Recommend re-reading concepts that are still weak after multiple tries."""
    recommendations = []

    for concept in profile.weak_concepts:
        if concept.total_attempts < REVISION_MIN_ATTEMPTS:
            # Only one attempt — too early to recommend revision
            continue

        accuracy_pct = round(concept.raw_accuracy * 100)
        recommendations.append(
            Recommendation(
                rec_type="revision",
                title=f"Revise: {concept.concept_name}",
                reasoning=(
                    f"You answered {concept.correct_attempts}/{concept.total_attempts} "
                    f"questions correctly on '{concept.concept_name}' "
                    f"({accuracy_pct}% accuracy). Re-reading this concept before your "
                    f"next quiz will help you improve."
                ),
                action_label="Start Revision",
                target=concept.concept_name,
            )
        )

    # Cap at 3 revision recommendations to avoid overwhelming the learner.
    return recommendations[:3]


def _practice_recommendations(profile: LearnerProfile) -> list[Recommendation]:
    """Recommend a targeted quiz for weak concepts where accuracy is low."""
    recommendations = []

    for concept in profile.weak_concepts:
        if concept.raw_accuracy >= PRACTICE_ACCURACY_THRESHOLD:
            continue  # Improving — no targeted practice needed yet

        recommendations.append(
            Recommendation(
                rec_type="practice",
                title=f"Practice Quiz: {concept.concept_name}",
                reasoning=(
                    f"Your accuracy on '{concept.concept_name}' is "
                    f"{round(concept.raw_accuracy * 100)}%. A short targeted quiz "
                    f"will reinforce your understanding with focused questions."
                ),
                action_label="Start Practice Quiz",
                target=concept.concept_name,
            )
        )

    # Cap at 2 practice recommendations.
    return recommendations[:2]


def _next_topic_recommendations(
    profile: LearnerProfile,
    current_topic: str,
    score_percentage: float,
) -> list[Recommendation]:
    """Suggest moving to a next topic when the learner is ready."""
    recommendations = []

    # Only suggest next topic if the learner scored well on the current quiz.
    if score_percentage < 70:
        return []

    # Check if learner has mastered concepts in the current topic.
    mastered_in_topic = [
        c for c in profile.mastered_concepts
        if _is_related(c.concept_name, current_topic)
    ]

    if mastered_in_topic or score_percentage >= 80:
        mastered_names = ", ".join(
            c.concept_name for c in mastered_in_topic[:3]
        ) or "several concepts"

        recommendations.append(
            Recommendation(
                rec_type="next_topic",
                title=f"Explore Beyond: {current_topic}",
                reasoning=(
                    f"You scored {score_percentage:.0f}% and have mastered "
                    f"{mastered_names} in {current_topic}. You are ready to "
                    f"explore related advanced topics."
                ),
                action_label="Choose Next Topic",
                target=current_topic,
            )
        )

    return recommendations[:1]


def _is_related(concept_name: str, topic: str) -> bool:
    """Rough check: does the concept name contain the topic keyword?"""
    topic_lower = topic.strip().lower()
    concept_lower = concept_name.strip().lower()
    # Simple heuristic — good enough for rule-based filtering
    return topic_lower in concept_lower or any(
        word in concept_lower for word in topic_lower.split() if len(word) > 3
    )


# ---------------------------------------------------------------------------
# Format recommendations for display
# ---------------------------------------------------------------------------


def format_recommendations_as_text(rec_set: RecommendationSet) -> str:
    """Return a plain-text summary of the recommendation set."""
    if rec_set.is_empty:
        return "No specific recommendations at this time. Keep up the good work!"

    lines = []
    if rec_set.revision:
        lines.append("**📖 Concepts to Revise**")
        for rec in rec_set.revision:
            lines.append(f"- {rec.title}: {rec.reasoning}")
    if rec_set.practice:
        lines.append("\n**🎯 Practice Quizzes**")
        for rec in rec_set.practice:
            lines.append(f"- {rec.title}: {rec.reasoning}")
    if rec_set.next_topic:
        lines.append("\n**🚀 Ready for More?**")
        for rec in rec_set.next_topic:
            lines.append(f"- {rec.title}: {rec.reasoning}")

    return "\n".join(lines)
