"""Adaptive Quiz Context Builder.

Builds the context dictionary passed to the adaptive quiz prompt.
Retrieves weak concepts, mastered concepts, and recent incorrect questions
from the database so the quiz generator can personalise its output.
"""

from __future__ import annotations

from services.learning_history import (
    get_mastered_concepts_for_topic,
    get_recent_incorrect_questions,
    get_weak_concepts_for_topic,
)


def build_quiz_context(
    db_user_id: int,
    topic: str,
    question_count: int,
    learning_level: str = "Beginner",
) -> dict:
    """Build a context dict for the adaptive quiz prompt.

    Parameters
    ----------
    db_user_id:
        Integer PK of the user (from ``get_or_create_user()``).
    topic:
        Topic name being quizzed.
    question_count:
        Desired number of questions.
    learning_level:
        "Beginner" | "Intermediate" | "Industry Level"

    Returns
    -------
    dict suitable for the ``ADAPTIVE_QUIZ_PROMPT`` template.
    """
    weak = get_weak_concepts_for_topic(db_user_id, topic)
    mastered = get_mastered_concepts_for_topic(db_user_id, topic)
    incorrect_history = get_recent_incorrect_questions(db_user_id, topic, limit=5)

    incorrect_summary = ""
    if incorrect_history:
        lines = [
            f"- '{item['question_text']}' (concept: {item['concept_name']}, "
            f"user answered: '{item['user_answer']}')"
            for item in incorrect_history[:5]
        ]
        incorrect_summary = "Previously incorrect questions:\n" + "\n".join(lines)

    return {
        "topic": topic,
        "learning_level": learning_level,
        "question_count": question_count,
        "weak_concepts": ", ".join(weak) if weak else "none identified yet",
        "mastered_concepts": ", ".join(mastered) if mastered else "none yet",
        "incorrect_history": incorrect_summary or "No previous incorrect answers recorded.",
        "has_history": bool(weak or mastered),
    }
