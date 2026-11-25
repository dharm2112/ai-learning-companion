"""Learning History Manager.

Provides CRUD operations for all persistence tables:
- Users / Topics
- LearningSession lifecycle (start → complete)
- QuizAttempt + QuizAnswer creation
- ConceptProgress upsert (most critical — feeds the Weak Concept Tracker)
- LearnerProfile retrieval (aggregated view for the memory system)

All functions accept a ``db_user_id`` (integer PK from ``users.id``), never
a UUID string, to keep joins fast and prevent cross-user data leakage.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.database import get_session
from db.models import (
    ConceptProgress,
    LearnerMemory,
    LearningSession,
    QuizAnswer,
    QuizAttempt,
    StoredRecommendation,
    Topic,
    User,
)
from schemas.memory import ConceptPerformanceSummary, LearnerProfile
from services.weak_concept_tracker import (
    ConceptPerformance,
    build_concept_performances,
)


# ---------------------------------------------------------------------------
# Topic helpers
# ---------------------------------------------------------------------------


def _normalize_topic(name: str) -> str:
    return name.strip().lower()


def get_or_create_topic(session: Session, topic_name: str) -> Topic:
    """Return existing topic row or create a new one."""
    norm = _normalize_topic(topic_name)
    topic = session.query(Topic).filter_by(normalized_name=norm).first()
    if topic is None:
        topic = Topic(name=topic_name.strip(), normalized_name=norm)
        session.add(topic)
        session.flush()
    return topic


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


def start_session(
    db_user_id: int,
    topic_name: str,
    learning_mode: str,
    learning_level: str,
) -> int:
    """Create and persist a new LearningSession. Returns the session id."""
    with get_session() as session:
        topic = get_or_create_topic(session, topic_name)
        ls = LearningSession(
            user_id=db_user_id,
            topic_id=topic.id,
            learning_mode=learning_mode,
            learning_level=learning_level,
        )
        session.add(ls)
        session.flush()
        return ls.id


def complete_session(session_id: int) -> None:
    """Mark a session as complete."""
    with get_session() as session:
        ls = session.get(LearningSession, session_id)
        if ls:
            ls.completed_at = datetime.now(timezone.utc)
            ls.is_complete = True


# ---------------------------------------------------------------------------
# Quiz attempt + answers
# ---------------------------------------------------------------------------


def save_quiz_attempt(
    session_id: int,
    attempt_type: str,
    question_results: Sequence[dict],
    score_percentage: float,
) -> int:
    """Persist a QuizAttempt and all its QuizAnswer rows.

    Parameters
    ----------
    session_id:
        FK to learning_sessions.id
    attempt_type:
        "initial" | "follow_up" | "practice"
    question_results:
        Each dict must have: concept_tested, question_text, question_type,
        user_answer, correct_answer, is_correct, explanation.
    score_percentage:
        Pre-computed float 0–100.

    Returns
    -------
    int  — the new QuizAttempt.id
    """
    total = len(question_results)
    correct = sum(1 for r in question_results if r.get("is_correct"))

    with get_session() as session:
        attempt = QuizAttempt(
            session_id=session_id,
            attempt_type=attempt_type,
            total_questions=total,
            correct_answers=correct,
            score_percentage=score_percentage,
        )
        session.add(attempt)
        session.flush()

        for i, result in enumerate(question_results, start=1):
            answer = QuizAnswer(
                attempt_id=attempt.id,
                question_number=i,
                concept_name=result.get("concept_tested", "").strip(),
                question_text=result.get("question_text", ""),
                question_type=result.get("question_type", ""),
                user_answer=str(result.get("user_answer", "")),
                correct_answer=str(result.get("correct_answer", "")),
                is_correct=bool(result.get("is_correct", False)),
                explanation=result.get("explanation", ""),
            )
            session.add(answer)

        return attempt.id


# ---------------------------------------------------------------------------
# Concept progress upsert
# ---------------------------------------------------------------------------


def update_concept_progress(
    db_user_id: int,
    topic_name: str,
    question_results: Sequence[dict],
    current_attempt_id: int | None = None,
) -> None:
    """Upsert concept_progress rows using the WeakConceptTracker's logic.

    This is called after every quiz submission.  It loads existing attempt
    history from the DB, appends the new results, and recalculates the
    weighted score and status.
    """
    with get_session() as session:
        topic = get_or_create_topic(session, topic_name)

        # Exclude the attempt being added below so its answers are not counted twice.
        historical: list[dict] = []
        history_query = (
            session.query(QuizAnswer)
            .join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id)
            .join(LearningSession, QuizAttempt.session_id == LearningSession.id)
            .filter(
                LearningSession.user_id == db_user_id,
                LearningSession.topic_id == topic.id,
            )
        )
        if current_attempt_id is not None:
            history_query = history_query.filter(
                QuizAttempt.id != current_attempt_id
            )
        existing_rows = history_query.order_by(QuizAnswer.id).all()
        for row in existing_rows:
            historical.append(
                {
                    "concept_tested": row.concept_name,
                    "is_correct": row.is_correct,
                    "question_text": row.question_text,
                    "user_answer": row.user_answer,
                    "correct_answer": row.correct_answer,
                }
            )

        # Build performances including the new results.
        all_results = historical + list(question_results)
        performances = build_concept_performances(all_results)

        now = datetime.now(timezone.utc)
        for key, perf in performances.items():
            row = (
                session.query(ConceptProgress)
                .filter_by(user_id=db_user_id, topic_id=topic.id, concept_name=perf.concept_name)
                .first()
            )
            if row is None:
                row = ConceptProgress(
                    user_id=db_user_id,
                    topic_id=topic.id,
                    concept_name=perf.concept_name,
                )
                session.add(row)

            row.total_attempts = perf.total_attempts
            row.correct_attempts = perf.correct_attempts
            row.weighted_score = round(perf.weighted_score, 4)
            row.status = perf.status
            row.last_attempted = now


# ---------------------------------------------------------------------------
# Learner profile retrieval
# ---------------------------------------------------------------------------


def get_learner_profile(db_user_id: int) -> LearnerProfile:
    """Build a LearnerProfile from the database for the given user."""
    with get_session() as session:
        user = session.get(User, db_user_id)
        if user is None:
            return LearnerProfile(user_id=str(db_user_id))

        # Topics studied
        topic_rows = (
            session.query(Topic.name)
            .join(LearningSession, LearningSession.topic_id == Topic.id)
            .filter(LearningSession.user_id == db_user_id)
            .distinct()
            .all()
        )
        topics_studied = [row.name for row in topic_rows]

        # Concept progress
        progress_rows = (
            session.query(ConceptProgress)
            .filter_by(user_id=db_user_id)
            .order_by(ConceptProgress.weighted_score)
            .all()
        )

        weak_concepts = []
        mastered_concepts = []
        learning_concepts = []

        for row in progress_rows:
            summary = ConceptPerformanceSummary(
                concept_name=row.concept_name,
                total_attempts=row.total_attempts,
                correct_attempts=row.correct_attempts,
                weighted_score=row.weighted_score,
                status=row.status,  # type: ignore[arg-type]
                last_attempted=row.last_attempted,
            )
            if row.status == "weak":
                weak_concepts.append(summary)
            elif row.status == "mastered":
                mastered_concepts.append(summary)
            else:
                learning_concepts.append(summary)

        # Session and attempt counts
        total_sessions = (
            session.query(func.count(LearningSession.id))
            .filter_by(user_id=db_user_id)
            .scalar()
            or 0
        )
        total_attempts = (
            session.query(func.count(QuizAttempt.id))
            .join(LearningSession, QuizAttempt.session_id == LearningSession.id)
            .filter(LearningSession.user_id == db_user_id)
            .scalar()
            or 0
        )

        return LearnerProfile(
            user_id=user.user_uuid,
            topics_studied=topics_studied,
            weak_concepts=weak_concepts,
            mastered_concepts=mastered_concepts,
            learning_concepts=learning_concepts,
            total_sessions=total_sessions,
            total_quiz_attempts=total_attempts,
            last_active=user.last_active,
        )


def get_weak_concepts_for_topic(db_user_id: int, topic_name: str) -> list[str]:
    """Return concept names marked 'weak' for a user × topic combination."""
    norm = _normalize_topic(topic_name)
    with get_session() as session:
        topic = session.query(Topic).filter_by(normalized_name=norm).first()
        if topic is None:
            return []
        rows = (
            session.query(ConceptProgress.concept_name)
            .filter_by(user_id=db_user_id, topic_id=topic.id, status="weak")
            .order_by(ConceptProgress.weighted_score)
            .all()
        )
        return [row.concept_name for row in rows]


def get_mastered_concepts_for_topic(db_user_id: int, topic_name: str) -> list[str]:
    """Return concept names marked 'mastered' for a user × topic combination."""
    norm = _normalize_topic(topic_name)
    with get_session() as session:
        topic = session.query(Topic).filter_by(normalized_name=norm).first()
        if topic is None:
            return []
        rows = (
            session.query(ConceptProgress.concept_name)
            .filter_by(user_id=db_user_id, topic_id=topic.id, status="mastered")
            .order_by(ConceptProgress.weighted_score.desc())
            .all()
        )
        return [row.concept_name for row in rows]


def get_recent_incorrect_questions(
    db_user_id: int,
    topic_name: str,
    limit: int = 10,
) -> list[dict]:
    """Return recent incorrect quiz answers for a user × topic (newest first)."""
    norm = _normalize_topic(topic_name)
    with get_session() as session:
        topic = session.query(Topic).filter_by(normalized_name=norm).first()
        if topic is None:
            return []
        rows = (
            session.query(QuizAnswer)
            .join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id)
            .join(LearningSession, QuizAttempt.session_id == LearningSession.id)
            .filter(
                LearningSession.user_id == db_user_id,
                LearningSession.topic_id == topic.id,
                QuizAnswer.is_correct == False,  # noqa: E712
            )
            .order_by(QuizAnswer.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "question_text": row.question_text,
                "concept_name": row.concept_name,
                "user_answer": row.user_answer,
                "correct_answer": row.correct_answer,
            }
            for row in rows
        ]


# ---------------------------------------------------------------------------
# Recommendation persistence
# ---------------------------------------------------------------------------


def save_recommendations(
    db_user_id: int,
    session_id: int,
    recommendations: list[dict],
) -> None:
    """Persist a list of recommendation dicts to the recommendations table."""
    with get_session() as session:
        for rec in recommendations:
            row = StoredRecommendation(
                user_id=db_user_id,
                session_id=session_id,
                rec_type=rec.get("rec_type", "revision"),
                title=rec.get("title", ""),
                content=rec.get("content", ""),
                reasoning=rec.get("reasoning", ""),
                target=rec.get("target", ""),
            )
            session.add(row)


def save_learner_memory(
    db_user_id: int,
    topic_name: str,
    content: str,
    memory_type: str = "topic_summary",
) -> None:
    """Persist a learner's topic summary in SQLite."""
    if not content.strip():
        return

    with get_session() as session:
        memory = LearnerMemory(
            user_id=db_user_id,
            memory_type=memory_type,
            topic_name=topic_name.strip(),
            content=content.strip(),
        )
        session.add(memory)


def get_user_history(db_user_id: int, limit: int = 20) -> list[dict]:
    """Return recent learning sessions and their latest quiz scores."""
    with get_session() as session:
        sessions = (
            session.query(LearningSession)
            .filter_by(user_id=db_user_id)
            .order_by(LearningSession.started_at.desc())
            .limit(limit)
            .all()
        )
        history = []
        for learning_session in sessions:
            attempts = sorted(
                learning_session.quiz_attempts,
                key=lambda attempt: attempt.attempted_at,
            )
            latest_score = (
                attempts[-1].score_percentage if attempts else None
            )
            history.append(
                {
                    "topic": learning_session.topic.name,
                    "learning_mode": learning_session.learning_mode,
                    "learning_level": learning_session.learning_level,
                    "started_at": learning_session.started_at,
                    "completed_at": learning_session.completed_at,
                    "is_complete": learning_session.is_complete,
                    "attempt_count": len(attempts),
                    "latest_score": latest_score,
                }
            )
        return history


def get_user_recommendations(db_user_id: int, limit: int = 10) -> list[dict]:
    """Return recent persisted recommendations for one user."""
    with get_session() as session:
        rows = (
            session.query(StoredRecommendation)
            .filter_by(user_id=db_user_id)
            .order_by(StoredRecommendation.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "rec_type": row.rec_type,
                "title": row.title,
                "reasoning": row.reasoning,
                "target": row.target,
                "created_at": row.created_at,
            }
            for row in rows
        ]
