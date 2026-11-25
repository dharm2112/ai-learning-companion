"""SQLAlchemy ORM models for the Adaptive AI Learning System.

Design rules
------------
- Every table has an integer primary key named ``id``.
- Foreign keys are enforced at the SQLite level (PRAGMA foreign_keys=ON in database.py).
- ``user_id`` refers to ``users.id`` (integer FK), not the UUID string — joins are fast.
- Timestamps stored as UTC strings (SQLite has no native datetime type).
- No business logic lives here — only column definitions and relationships.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_uuid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False, default="Learner")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    last_active: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    sessions: Mapped[list["LearningSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    concept_progress: Mapped[list["ConceptProgress"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    memories: Mapped[list["LearnerMemory"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    recommendations: Mapped[list["StoredRecommendation"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    sessions: Mapped[list["LearningSession"]] = relationship(back_populates="topic")
    concept_progress: Mapped[list["ConceptProgress"]] = relationship(back_populates="topic")


# ---------------------------------------------------------------------------
# Learning Sessions
# ---------------------------------------------------------------------------


class LearningSession(Base):
    __tablename__ = "learning_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic_id: Mapped[int] = mapped_column(Integer, ForeignKey("topics.id"), nullable=False)
    learning_mode: Mapped[str] = mapped_column(String(32), nullable=False)   # "learn_first" | "test_first"
    learning_level: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="sessions")
    topic: Mapped["Topic"] = relationship(back_populates="sessions")
    quiz_attempts: Mapped[list["QuizAttempt"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    recommendations: Mapped[list["StoredRecommendation"]] = relationship(back_populates="session", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Quiz Attempts
# ---------------------------------------------------------------------------


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("learning_sessions.id"), nullable=False, index=True)
    attempt_type: Mapped[str] = mapped_column(String(32), nullable=False)  # "initial" | "follow_up" | "practice"
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_answers: Mapped[int] = mapped_column(Integer, nullable=False)
    score_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    session: Mapped["LearningSession"] = relationship(back_populates="quiz_attempts")
    answers: Mapped[list["QuizAnswer"]] = relationship(back_populates="attempt", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Quiz Answers (individual question results)
# ---------------------------------------------------------------------------


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(Integer, ForeignKey("quiz_attempts.id"), nullable=False, index=True)
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    concept_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(32), nullable=False)
    user_answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")

    attempt: Mapped["QuizAttempt"] = relationship(back_populates="answers")


# ---------------------------------------------------------------------------
# Concept Progress  (one row per user × topic × concept)
# ---------------------------------------------------------------------------


class ConceptProgress(Base):
    __tablename__ = "concept_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", "concept_name", name="uq_user_topic_concept"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic_id: Mapped[int] = mapped_column(Integer, ForeignKey("topics.id"), nullable=False)
    concept_name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    weighted_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="weak")  # weak|learning|mastered
    last_attempted: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    user: Mapped["User"] = relationship(back_populates="concept_progress")
    topic: Mapped["Topic"] = relationship(back_populates="concept_progress")


# ---------------------------------------------------------------------------
# Learner Memories  (text summaries for semantic retrieval)
# ---------------------------------------------------------------------------


class LearnerMemory(Base):
    __tablename__ = "learner_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)  # "topic_summary" | "cross_topic"
    topic_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    user: Mapped["User"] = relationship(back_populates="memories")


# ---------------------------------------------------------------------------
# Stored Recommendations
# ---------------------------------------------------------------------------


class StoredRecommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("learning_sessions.id"), nullable=False)
    rec_type: Mapped[str] = mapped_column(String(32), nullable=False)  # revision|practice|next_topic
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_acted_on: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    user: Mapped["User"] = relationship(back_populates="recommendations")
    session: Mapped["LearningSession"] = relationship(back_populates="recommendations")
